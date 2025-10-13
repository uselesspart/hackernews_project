from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_engine(db_url: str):
    return create_engine(db_url, pool_pre_ping=True, future=True)


@contextmanager
def session_scope(db_url: str):
    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()