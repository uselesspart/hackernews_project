from sqlalchemy import select

from analytics.embeddings.patterns import PATTERNS
from analytics.embeddings.scripts import classify_tech
from analytics.embeddings.scripts.classify_tech import classify_stories, ensure_techs
from db import session_scope
from db.models import Story, Tech


def _links(session):
    return {s.id: sorted(t.name for t in s.techs) for s in session.scalars(select(Story))}


def test_ensure_techs_is_idempotent(db_url):
    with session_scope(db_url) as session:
        first = ensure_techs(session, ["python", "rust"])
        second = ensure_techs(session, ["python", "rust", "go"])
        assert set(first) == {"python", "rust"}
        assert set(second) == {"python", "rust", "go"}
        assert session.query(Tech).count() == 3


def test_classify_stories_links_techs(ingested_db):
    with session_scope(ingested_db) as session:
        updated = classify_stories(session)
        assert updated == 3
        assert _links(session) == {1: ["cpp"], 2: ["go", "rust"], 3: ["postgresql"], 4: []}
        assert session.query(Tech).count() == len(PATTERNS)


def test_classify_stories_commits_between_batches(ingested_db):
    # Регрессия: при чтении потоковым курсором коммит пакета на большой БД давал
    # "database is locked". batch_size=1 заставляет коммитить после каждой истории.
    with session_scope(ingested_db) as session:
        assert classify_stories(session, batch_size=1) == 3
        assert _links(session)[2] == ["go", "rust"]


def test_classify_stories_rerun_adds_nothing(classified_db):
    with session_scope(classified_db) as session:
        assert classify_stories(session) == 0


def test_classify_stories_dry_run_writes_nothing(ingested_db):
    with session_scope(ingested_db) as session:
        assert classify_stories(session, dry_run=True) == 3
    with session_scope(ingested_db) as session:
        assert all(not techs for techs in _links(session).values())


def test_classify_cli(run_cli, ingested_db, capsys):
    assert run_cli(classify_tech.main, "-d", ingested_db) == 0
    assert "Обновлено историй: 3" in capsys.readouterr().out
