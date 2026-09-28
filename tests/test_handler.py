import gzip
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models import Comment, Story
from hackernews_handler import HNHandler, iter_items
from tests.conftest import HN_ITEMS, write_jsonl


@pytest.fixture
def engine(db_url):
    eng = create_engine(db_url)
    yield eng
    eng.dispose()


@pytest.fixture
def handler(engine):
    return HNHandler(engine, batch_size=3)


def test_story_row(handler):
    row = handler._story_row(HN_ITEMS[0])
    assert row == {
        "id": 1, "author": "a", "descendants": 4, "score": 10,
        "time": datetime.fromtimestamp(1700000000, tz=timezone.utc),
        "title": "Why C++ is great", "url": "https://example.com/1", "kids": [10, 12],
        "dead": False, "deleted": False,
    }


@pytest.mark.parametrize("item", [
    {"id": 1, "type": "comment", "text": "x"},
    {"id": 1, "type": "story"},
    {"id": 1, "type": "story", "title": ""},
])
def test_story_row_rejects(handler, item):
    assert handler._story_row(item) is None


def test_story_row_defaults(handler):
    row = handler._story_row({"id": 5, "type": "story", "title": "T", "kids": None, "dead": True})
    assert row["kids"] == []
    assert row["time"] is None
    assert row["dead"] is True and row["deleted"] is False


def test_comment_row_unescapes_html(handler):
    row = handler._comment_row({"id": 7, "type": "comment", "parent": 1, "text": "it&#x27;s &gt; 1"})
    assert row["text"] == "it's > 1"
    assert handler._comment_row({"id": 7, "type": "story"}) is None


def test_comment_row_deleted_has_no_text(handler):
    row = handler._comment_row(next(i for i in HN_ITEMS if i["id"] == 14))
    assert row["text"] is None and row["deleted"] is True


def test_iter_items_plain_and_gzip(tmp_path):
    lines = ['{"id": 1}', "", "not json", "[1, 2]", '{"id": 2}']
    plain = tmp_path / "a.jsonl"
    plain.write_text("\n".join(lines), encoding="utf-8")
    packed = tmp_path / "a.jsonl.gz"
    with gzip.open(packed, "wt", encoding="utf-8") as f:
        f.write("\n".join(lines))

    assert list(iter_items(plain)) == [{"id": 1}, {"id": 2}]
    assert list(iter_items(packed)) == [{"id": 1}, {"id": 2}]


def test_iter_items_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(iter_items(tmp_path / "nope.jsonl"))


def test_ingest_counts_and_rows(handler, engine, items_file):
    counts = handler.ingest_from_path(items_file)
    assert counts == {"stories": 4, "comments": 7}

    with Session(engine) as s:
        assert s.scalars(select(Story.id).order_by(Story.id)).all() == [1, 2, 3, 4]
        story = s.get(Story, 3)
        assert story.dead is True and story.deleted is False
        comment = s.get(Comment, 11)
        assert (comment.parent, comment.text, comment.author) == (10, "I agree", "f")


def test_ingest_is_idempotent_upsert(handler, engine, items_file, tmp_path):
    handler.ingest_from_path(items_file)
    updated = [dict(HN_ITEMS[0], score=99, title="Why C++ is still great"),
               dict(HN_ITEMS[4], text="Edited")]
    handler.ingest_from_path(write_jsonl(tmp_path / "upd.jsonl", updated))

    with Session(engine) as s:
        assert s.query(Story).count() == 4
        story = s.get(Story, 1)
        assert (story.score, story.title) == (99, "Why C++ is still great")
        assert s.get(Comment, 10).text == "Edited"


def test_ingest_dedups_within_batch(engine, tmp_path):
    handler = HNHandler(engine, batch_size=100)
    items = [dict(HN_ITEMS[0], score=1), dict(HN_ITEMS[0], score=2)]
    handler.ingest_from_path(write_jsonl(tmp_path / "dup.jsonl", items))
    with Session(engine) as s:
        assert s.get(Story, 1).score == 2


def test_ingest_large_batch_exceeds_sqlite_variable_limit(engine, tmp_path):
    # 5000 комментариев x 7 колонок = 35000 параметров > лимита SQLite (32766) для одного INSERT
    items = [{"id": i, "type": "comment", "parent": 1, "text": f"c{i}"} for i in range(1, 5001)]
    counts = HNHandler(engine, batch_size=5000).ingest_from_path(write_jsonl(tmp_path / "big.jsonl", items))
    assert counts == {"stories": 0, "comments": 5000}
    with Session(engine) as s:
        assert s.query(Comment).count() == 5000


def test_ingest_skips_unknown_types(handler, engine, tmp_path):
    items = [{"id": 100, "type": "job", "title": "Hiring"}, {"id": 101, "type": "poll", "title": "Poll"}]
    counts = handler.ingest_from_path(write_jsonl(tmp_path / "other.jsonl", items))
    assert counts == {"stories": 0, "comments": 0}


def test_select_helpers(handler, items_file):
    handler.ingest_from_path(items_file)
    assert len(list(handler.select_all_stories())) == 4
    assert len(list(handler.select_all_comments())) == 7
    assert {c.id for c in handler.select_comments_by_parent(1)} == {10, 12}


def test_ingest_cli(run_cli, db_url, items_file, tmp_path):
    from db.scripts import ingest
    assert run_cli(ingest.main, "-d", db_url, "-i", items_file, "-b", 2) == 0
    assert run_cli(ingest.main, "-d", db_url, "-i", tmp_path / "missing.jsonl") == 2
