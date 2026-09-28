import json
import os
import sys

# Неинтерактивный backend до первого импорта matplotlib в тестах
os.environ.setdefault("MPLBACKEND", "Agg")

import pytest
from sqlalchemy import create_engine

from hackernews_handler import HNHandler


def _spacy_available() -> bool:
    from utils import lemmatize
    return lemmatize._en_nlp is not None


def pytest_collection_modifyitems(config, items):
    if _spacy_available():
        return
    skip = pytest.mark.skip(reason="spaCy en_core_web_sm не установлена")
    for item in items:
        if "spacy" in item.keywords:
            item.add_marker(skip)


# Истории и комментарии для БД-тестов:
#   1 "Why C++ is great"  <- 10 <- 11;  1 <- 12 (dead) <- 13
#   2 "Rust vs Golang"    <- 14 (deleted), 15
#   3 "Postgres tips" (dead story) <- 16
#   4 "Random news" — без технологий
HN_ITEMS = [
    {"id": 1, "type": "story", "title": "Why C++ is great", "descendants": 4, "score": 10,
     "time": 1700000000, "by": "a", "url": "https://example.com/1", "kids": [10, 12]},
    {"id": 2, "type": "story", "title": "Rust vs Golang", "descendants": 2, "score": 5,
     "time": 1700000100, "by": "b"},
    {"id": 3, "type": "story", "title": "Postgres tips", "descendants": 1, "score": 1,
     "time": 1700000200, "by": "c", "dead": True},
    {"id": 4, "type": "story", "title": "Random news", "descendants": 0, "score": 1,
     "time": 1700000300, "by": "d"},
    {"id": 10, "type": "comment", "parent": 1, "text": "Great language", "time": 1700000001, "by": "e"},
    {"id": 11, "type": "comment", "parent": 10, "text": "I agree", "time": 1700000002, "by": "f"},
    {"id": 12, "type": "comment", "parent": 1, "text": "spam spam", "time": 1700000003, "by": "g", "dead": True},
    {"id": 13, "type": "comment", "parent": 12, "text": "reply to dead", "time": 1700000004, "by": "h"},
    {"id": 14, "type": "comment", "parent": 2, "time": 1700000101, "deleted": True},
    {"id": 15, "type": "comment", "parent": 2, "text": "Rust is nice", "time": 1700000102, "by": "i"},
    {"id": 16, "type": "comment", "parent": 3, "text": "pg comment", "time": 1700000201, "by": "j"},
]


def write_jsonl(path, items):
    path.write_text("\n".join(json.dumps(x) for x in items) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'hn.db').as_posix()}"


@pytest.fixture
def items_file(tmp_path):
    return write_jsonl(tmp_path / "items.jsonl", HN_ITEMS)


@pytest.fixture
def ingested_db(db_url, items_file):
    """БД с загруженными HN_ITEMS, без классификации технологий."""
    engine = create_engine(db_url)
    HNHandler(engine).ingest_from_path(items_file)
    engine.dispose()
    return db_url


@pytest.fixture
def classified_db(ingested_db):
    """БД с HN_ITEMS и связями story <-> tech."""
    from db import session_scope
    from analytics.embeddings.scripts.classify_tech import classify_stories
    with session_scope(ingested_db) as session:
        classify_stories(session)
    return ingested_db


@pytest.fixture
def run_cli(monkeypatch):
    """Запуск main() CLI-скрипта с заданными аргументами командной строки."""
    def _run(main, *args):
        monkeypatch.setattr(sys, "argv", ["prog", *map(str, args)])
        return main()
    return _run
