import sqlite3

from sqlalchemy import create_engine, inspect, select

from db import session_scope, upgrade_schema
from db.models import Story, Tech
from db.queries import is_alive, iter_story_titles, iter_tech_names


def _create_legacy_db(path):
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE story (id INTEGER PRIMARY KEY, author VARCHAR(50), descendants INTEGER,
                            score INTEGER, time DATETIME, title VARCHAR, url VARCHAR, kids JSON);
        CREATE TABLE comment (id INTEGER PRIMARY KEY, author VARCHAR(50), parent INTEGER,
                              time DATETIME, text VARCHAR);
        INSERT INTO story (id, title, kids) VALUES (1, 'Legacy', '[]');
    """)
    con.commit()
    con.close()


def test_upgrade_schema_adds_columns_to_legacy_db(tmp_path):
    path = tmp_path / "legacy.db"
    _create_legacy_db(path)
    engine = create_engine(f"sqlite:///{path.as_posix()}")

    upgrade_schema(engine)
    upgrade_schema(engine)  # повторный вызов ничего не ломает

    insp = inspect(engine)
    for table in ("story", "comment"):
        cols = {c["name"] for c in insp.get_columns(table)}
        assert {"dead", "deleted"} <= cols
    assert {"tech", "story_tech"} <= set(insp.get_table_names())

    with engine.connect() as conn:
        assert conn.execute(select(Story.id, Story.title, Story.dead)).all() == [(1, "Legacy", None)]
    engine.dispose()


def test_session_scope_creates_schema(db_url):
    with session_scope(db_url) as session:
        assert session.query(Story).count() == 0


def test_iter_story_titles_filters_dead_and_deleted(ingested_db):
    with session_scope(ingested_db) as session:
        alive = list(iter_story_titles(session))
        everything = list(iter_story_titles(session, keep_deleted=True))
        limited = list(iter_story_titles(session, limit=2))

    assert [i for i, _ in alive] == [1, 2, 4]
    assert [i for i, _ in everything] == [1, 2, 3, 4]
    assert len(limited) == 2


def test_is_alive_treats_null_as_alive(ingested_db):
    with session_scope(ingested_db) as session:
        session.add(Story(id=50, title="Legacy row", dead=None, deleted=None))
        session.commit()
        ids = session.scalars(select(Story.id).where(is_alive(Story)).order_by(Story.id)).all()
    assert ids == [1, 2, 4, 50]


def test_iter_tech_names(db_url):
    with session_scope(db_url) as session:
        session.add_all([Tech(name="python"), Tech(name="rust")])
        session.commit()
        assert sorted(name for _, name in iter_tech_names(session)) == ["python", "rust"]
        assert len(list(iter_tech_names(session, limit=1))) == 1
