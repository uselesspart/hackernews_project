from contextlib import contextmanager
from sqlalchemy import Boolean, create_engine, event, inspect
from sqlalchemy.orm import sessionmaker

from .models import Base

# Колонки, добавленные после появления первых БД: create_all не меняет
# существующие таблицы, поэтому досоздаём их сами (до перехода на Alembic).
_ADDED_COLUMNS = {
    "story": [("dead", Boolean()), ("deleted", Boolean())],
    "comment": [("dead", Boolean()), ("deleted", Boolean())],
}


def upgrade_schema(engine) -> None:
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    quote = engine.dialect.identifier_preparer.quote
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, col_type in columns:
                if name not in existing:
                    type_sql = col_type.compile(dialect=engine.dialect)
                    conn.exec_driver_sql(
                        f"ALTER TABLE {quote(table)} ADD COLUMN {quote(name)} {type_sql}"
                    )
        # create_all создаёт индексы только вместе с новой таблицей
        for tbl in Base.metadata.sorted_tables:
            for index in tbl.indexes:
                index.create(conn, checkfirst=True)


def _sqlite_pragmas(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    # WAL + NORMAL: коммит пакета не ждёт полного fsync, читатели не блокируют писателя
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


def get_engine(db_url: str, **kwargs):
    engine = create_engine(db_url, pool_pre_ping=True, future=True, **kwargs)
    if engine.dialect.name == "sqlite" and engine.url.database not in (None, "", ":memory:"):
        event.listen(engine, "connect", _sqlite_pragmas)
    return engine


@contextmanager
def session_scope(db_url: str):
    engine = get_engine(db_url)
    upgrade_schema(engine)
    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()
