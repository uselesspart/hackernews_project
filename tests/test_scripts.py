import gzip
import json
from random import Random

import pytest

from hackernews_retriever import HNRetriever
from scripts import combine, create_samples
from scripts.retrieve import download_items_streaming, iter_hn_ids


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.urls = []

    def get(self, url, timeout=None):
        self.urls.append(url)
        return FakeResponse(self.payload)


class FakeRetriever:
    def retrieve_item(self, item_id, session=None):
        if item_id == 3:
            raise RuntimeError("network error")
        if item_id == 4:
            return None  # несуществующий item в API
        return {"id": item_id, "type": "story"}


def _read_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


# --- retrieve ---------------------------------------------------------------

def test_iter_hn_ids_explicit_range():
    assert list(iter_hn_ids(1, 4)) == [1, 2, 3, 4]
    assert list(iter_hn_ids(4, 1)) == [4, 3, 2, 1]


def test_iter_hn_ids_uses_maxitem():
    session = FakeSession(3)
    assert list(iter_hn_ids(session=session)) == [3, 2, 1]
    assert session.urls[0].endswith("maxitem.json")


def test_retriever_builds_item_url():
    session = FakeSession({"id": 42})
    assert HNRetriever().retrieve_item(42, session=session) == {"id": 42}
    assert session.urls == ["https://hacker-news.firebaseio.com/v0/item/42.json"]


@pytest.mark.parametrize("compress", [True, False])
def test_download_items_streaming(tmp_path, compress):
    out = tmp_path / ("items.jsonl.gz" if compress else "items.jsonl")
    stats = download_items_streaming(iter_hn_ids(1, 6), FakeRetriever(), out_path=str(out),
                                     workers=2, compress=compress, progress_every=0)
    assert (stats["seen"], stats["saved"], stats["errors"]) == (6, 4, 1)

    if compress:
        items = _read_gz(out)
    else:
        items = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert sorted(i["id"] for i in items) == [1, 2, 5, 6]


# --- combine ----------------------------------------------------------------

def _write_gz(path, lines):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write("".join(line + "\n" for line in lines))


@pytest.mark.parametrize("dedup, expected_count", [("line", 3), ("json", 2)])
def test_merge_jsonl_gz(tmp_path, dedup, expected_count):
    src = tmp_path / "src"
    src.mkdir()
    _write_gz(src / "a.jsonl.gz", ['{"id": 1, "x": 2}', '{"id": 2}'])
    _write_gz(src / "b.jsonl.gz", ['{"id": 2}', '{"x": 2, "id": 1}'])  # тот же JSON, другой порядок ключей
    out = tmp_path / "out" / "merged.jsonl.gz"

    combine.merge_jsonl_gz(src, out, dedup=dedup)
    assert len(_read_gz(out)) == expected_count


def test_merge_jsonl_gz_no_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        combine.merge_jsonl_gz(tmp_path, tmp_path / "out.jsonl.gz")


# --- create_samples ---------------------------------------------------------

def test_parse_sets():
    assert create_samples.parse_sets(["a:1", " b :20"]) == [("a", 1), ("b", 20)]
    for bad in ["a", "a:x", "a:0", ":3"]:
        with pytest.raises(ValueError):
            create_samples.parse_sets([bad])


def test_reservoir_sample_is_deterministic_and_bounded():
    items = [{"id": i} for i in range(100)]
    s1 = create_samples.reservoir_sample(iter(items), 10, Random(1))
    s2 = create_samples.reservoir_sample(iter(items), 10, Random(1))
    assert s1 == s2 and len(s1) == 10
    assert create_samples.reservoir_sample(iter(items[:3]), 10, Random(1)) == items[:3]


def test_filter_stream():
    items = [
        {"id": 1, "type": "story"}, {"id": 1, "type": "story"}, {"id": 2, "type": "comment"},
        {"id": 3, "type": "story", "dead": True}, {"type": "story"},
    ]
    kept = list(create_samples.filter_stream(iter(items), types=["story"]))
    assert kept == [{"id": 1, "type": "story"}]
    kept_all = list(create_samples.filter_stream(iter(items), skip_deleted=False, unique_by_id=False))
    assert len(kept_all) == 5


@pytest.mark.parametrize("fmt", ["json", "jsonl"])
def test_write_sets_files(tmp_path, fmt):
    items = [{"id": i} for i in range(5)]
    create_samples.write_sets_files(tmp_path, [("first", 2), ("second", 3)], items, fmt=fmt)
    path = tmp_path / f"second.{fmt}"
    text = path.read_text(encoding="utf-8")
    loaded = json.loads(text) if fmt == "json" else [json.loads(line) for line in text.splitlines()]
    assert loaded == items[2:]


def test_write_sets_files_not_enough_items(tmp_path):
    with pytest.raises(RuntimeError):
        create_samples.write_sets_files(tmp_path, [("a", 5)], [{"id": 1}])


def test_create_samples_main(run_cli, tmp_path):
    src = tmp_path / "raw.jsonl"
    src.write_text("\n".join(json.dumps({"id": i, "type": "story" if i % 2 else "comment"})
                             for i in range(20)), encoding="utf-8")
    out = tmp_path / "samples"
    rc = run_cli(create_samples.main, "-i", src, "-o", out, "--sets", "s1:3", "s2:2",
                 "--filter-types", "story", "--mode", "head")
    assert rc == 0
    s1 = json.loads((out / "s1.json").read_text(encoding="utf-8"))
    assert [x["id"] for x in s1] == [1, 3, 5]
    assert run_cli(create_samples.main, "-i", src, "-o", out, "--sets", "big:100") == 1
