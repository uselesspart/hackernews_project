import csv
import json

import pytest

from db import session_scope
from db.models import Story, Tech
from db.scripts import (
    db_connect,
    export_comments_for_techs,
    export_context,
    export_stories_meta,
    export_tech_names,
    export_titles,
    trim,
)
from db.scripts.export_comments_for_techs import all_thread_comments_for_tech


def _read(path):
    return path.read_text(encoding="utf-8").splitlines()


# --- export_context ---------------------------------------------------------

def test_export_context_txt(run_cli, ingested_db, tmp_path):
    out = tmp_path / "ctx" / "context.txt"
    assert run_cli(export_context.main, "-d", ingested_db, "-o", out) == 0
    # Только прямые, живые комментарии к живым историям
    assert _read(out) == [
        "Why C++ is great Great language",
        "Rust vs Golang Rust is nice",
        "Random news",
    ]


def test_export_context_cleans_each_comment_separately(run_cli, db_url, tmp_path):
    # Регрессия: clean_text на склеенной строке вырезал "< ... >" через границу комментариев,
    # а порядок комментариев зависел от плана запроса. Теперь порядок — по id комментария.
    from sqlalchemy import create_engine

    from hackernews_handler import HNHandler
    from tests.conftest import write_jsonl
    items = [
        {"id": 1, "type": "story", "title": "Compare"},
        {"id": 3, "type": "comment", "parent": 1, "text": "then c &gt; d"},
        {"id": 2, "type": "comment", "parent": 1, "text": "if a &lt; b"},
    ]
    engine = create_engine(db_url)
    HNHandler(engine).ingest_from_path(write_jsonl(tmp_path / "items.jsonl", items))
    engine.dispose()

    out = tmp_path / "context.txt"
    assert run_cli(export_context.main, "-d", db_url, "-o", out) == 0
    assert _read(out) == ["Compare if a < b then c > d"]


def test_export_context_keep_deleted_and_limit(run_cli, ingested_db, tmp_path):
    out = tmp_path / "context.txt"
    assert run_cli(export_context.main, "-d", ingested_db, "-o", out, "--keep-deleted", "--limit", 3) == 0
    lines = _read(out)
    assert len(lines) == 3
    assert "spam spam" in lines[0]
    assert lines[2] == "Postgres tips pg comment"


def test_export_context_csv(run_cli, ingested_db, tmp_path):
    out = tmp_path / "context.csv"
    assert run_cli(export_context.main, "-d", ingested_db, "-o", out, "--format", "csv") == 0
    with out.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["id"] for r in rows] == ["1", "2", "4"]
    assert rows[0] == {"id": "1", "title": "Why C++ is great", "context": "Great language"}


def test_export_context_jsonl(run_cli, ingested_db, tmp_path):
    out = tmp_path / "context.jsonl"
    assert run_cli(export_context.main, "-d", ingested_db, "-o", out, "--format", "jsonl") == 0
    rows = [json.loads(line) for line in _read(out)]
    assert rows[1] == {"id": 2, "title": "Rust vs Golang", "context": "Rust is nice"}


# --- export_titles / export_tech_names --------------------------------------

@pytest.mark.parametrize("fmt, expected", [
    ("txt", ["Why C++ is great", "Rust vs Golang", "Random news"]),
    ("csv", ["id,title", "1,Why C++ is great", "2,Rust vs Golang", "4,Random news"]),
    ("jsonl", ['{"id": 1, "title": "Why C++ is great"}', '{"id": 2, "title": "Rust vs Golang"}',
               '{"id": 4, "title": "Random news"}']),
])
def test_export_titles(run_cli, ingested_db, tmp_path, fmt, expected):
    out = tmp_path / f"titles.{fmt}"
    assert run_cli(export_titles.main, "-d", ingested_db, "-o", out, "--format", fmt) == 0
    assert _read(out) == expected


def test_export_titles_with_techs_only(run_cli, classified_db, tmp_path):
    out = tmp_path / "titles.txt"
    assert run_cli(export_titles.main, "-d", classified_db, "-o", out, "--with-techs-only") == 0
    assert _read(out) == ["Why C++ is great", "Rust vs Golang"]  # "Random news" без технологий


def test_export_context_with_techs_only(run_cli, classified_db, tmp_path):
    out = tmp_path / "context.txt"
    assert run_cli(export_context.main, "-d", classified_db, "-o", out, "--with-techs-only") == 0
    assert _read(out) == ["Why C++ is great Great language", "Rust vs Golang Rust is nice"]


def test_export_titles_keep_deleted(run_cli, ingested_db, tmp_path):
    out = tmp_path / "titles.txt"
    assert run_cli(export_titles.main, "-d", ingested_db, "-o", out, "--keep-deleted") == 0
    assert "Postgres tips" in _read(out)


def test_export_tech_names(run_cli, classified_db, tmp_path):
    out = tmp_path / "techs.csv"
    assert run_cli(export_tech_names.main, "-d", classified_db, "-o", out, "--format", "csv", "--limit", 5) == 0
    lines = _read(out)
    assert lines[0] == "id,name"
    assert len(lines) == 6


# --- export_stories_meta ----------------------------------------------------

def test_export_stories_meta(run_cli, classified_db, tmp_path):
    out = tmp_path / "meta.csv"
    assert run_cli(export_stories_meta.main, "-d", classified_db, "-o", out) == 0
    with out.open(encoding="utf-8", newline="") as f:
        rows = {int(r["id"]): r for r in csv.DictReader(f)}

    assert rows[1]["techs_count"] == "1" and rows[1]["tech_names"] == "cpp"
    assert rows[2]["techs_count"] == "2" and sorted(rows[2]["tech_names"].split("|")) == ["go", "rust"]
    assert rows[4]["techs_count"] == "0" and rows[4]["tech_names"] == ""
    assert rows[1]["time"] == "2023-11-14T22:13:20"
    # Сортировка по числу комментариев по убыванию
    assert list(rows) == [1, 2, 3, 4]


# --- export_comments_for_techs ----------------------------------------------

def _tech_id(session, name):
    return session.query(Tech).filter_by(name=name).one().id


def test_thread_comments_are_recursive_and_skip_dead(classified_db):
    with session_scope(classified_db) as session:
        cpp = all_thread_comments_for_tech(session, _tech_id(session, "cpp"))
        rust = all_thread_comments_for_tech(session, _tech_id(session, "rust"))
        pg = all_thread_comments_for_tech(session, _tech_id(session, "postgresql"))

    # 11 — ответ на ответ; 12 (dead) исключён, но ответ на него (13) остаётся
    assert sorted(cpp) == ["Great language", "I agree", "reply to dead"]
    assert rust == ["Rust is nice"]  # 14 (deleted) исключён
    assert pg == []  # история dead


def test_export_comments_txt(run_cli, classified_db, tmp_path):
    out_dir = tmp_path / "comments"
    assert run_cli(export_comments_for_techs.main, "-d", classified_db, "-o", out_dir, "-m", 1) == 0
    files = {p.name.rsplit("_", 1)[0]: p for p in out_dir.glob("*.txt")}
    assert set(files) == {"cpp", "rust", "go"}
    assert sorted(_read(files["cpp"])) == ["Great language", "I agree", "reply to dead"]


def test_export_comments_json(run_cli, classified_db, tmp_path):
    out_dir = tmp_path / "comments"
    assert run_cli(export_comments_for_techs.main, "-d", classified_db, "-o", out_dir, "-m", 1, "-f", "json") == 0
    data = json.loads((out_dir / "comments.json").read_text(encoding="utf-8"))
    by_tech = {d["tech"]: d["comments"] for d in data}
    assert by_tech["rust"] == ["Rust is nice"]
    assert by_tech["postgresql"] == []


def test_export_comments_minimum(run_cli, classified_db, tmp_path):
    out_dir = tmp_path / "comments"
    assert run_cli(export_comments_for_techs.main, "-d", classified_db, "-o", out_dir, "-m", 2) == 0
    assert list(out_dir.glob("*.txt")) == []


# --- trim / db_connect ------------------------------------------------------

def test_trim_dry_run_and_delete(classified_db):
    with session_scope(classified_db) as session:
        assert trim.delete_stories_without_techs(session, dry_run=True) == 0
        assert session.query(Story).count() == 4
        assert trim.delete_stories_without_techs(session) == 1
        assert session.get(Story, 4) is None


def test_db_connect(run_cli, classified_db, capsys):
    assert run_cli(db_connect.main, "-d", classified_db) == 0
    out = capsys.readouterr().out
    assert "- story: 4" in out
    assert "- comment: 7" in out
    assert "- story_tech: 4" in out
