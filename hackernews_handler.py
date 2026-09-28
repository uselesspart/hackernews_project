from collections.abc import Iterable
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from db.models import Comment, Story
from db.session import upgrade_schema
from utils.io import iter_jsonl

STORY_UPDATE_COLS = ("author", "descendants", "score", "time", "title", "url", "kids", "dead", "deleted")
COMMENT_UPDATE_COLS = ("author", "parent", "time", "text", "dead", "deleted")


def _utc(ts) -> datetime | None:
    return datetime.fromtimestamp(ts, tz=UTC) if isinstance(ts, int | float) else None


def _flags(item: dict) -> dict:
    return {"dead": bool(item.get("dead", False)), "deleted": bool(item.get("deleted", False))}


class HNHandler:
    def __init__(self, engine, batch_size: int = 1000):
        self.engine = engine
        self.batch_size = batch_size
        self.SessionLocal = sessionmaker(bind=engine)
        self.create_schema()

    def create_schema(self) -> None:
        upgrade_schema(self.engine)

    def ingest_from_path(self, path: str | Path) -> dict[str, int]:
        # Пакеты — словари по id: повтор элемента внутри пакета не даёт конфликта при вставке,
        # побеждает последняя версия
        stories: dict[int, dict] = {}
        comments: dict[int, dict] = {}
        counts = {"stories": 0, "comments": 0}

        with self.SessionLocal() as session:
            def flush():
                if stories:
                    counts["stories"] += self._upsert(session, Story.__table__, list(stories.values()),
                                                      STORY_UPDATE_COLS)
                    stories.clear()
                if comments:
                    counts["comments"] += self._upsert(session, Comment.__table__, list(comments.values()),
                                                       COMMENT_UPDATE_COLS)
                    comments.clear()

            for item in iter_jsonl(path):
                if (row := self._story_row(item)) is not None:
                    stories[row["id"]] = row
                elif (row := self._comment_row(item)) is not None:
                    comments[row["id"]] = row
                if len(stories) + len(comments) >= self.batch_size:
                    flush()
            flush()

        return counts

    # Преобразование в dict для Core-вставки
    def _story_row(self, item: dict) -> dict | None:
        if item.get("type") != "story" or not item.get("title"):
            return None
        return {
            "id": item.get("id"),
            "author": item.get("by"),
            "descendants": item.get("descendants"),
            "score": item.get("score"),
            "time": _utc(item.get("time")),
            "title": item.get("title"),
            "url": item.get("url"),
            "kids": item.get("kids") or [],
            **_flags(item),
        }

    def _comment_row(self, item: dict) -> dict | None:
        if item.get("type") != "comment":
            return None
        text = item.get("text")
        return {
            "id": item.get("id"),
            "author": item.get("by"),
            "parent": item.get("parent"),
            "time": _utc(item.get("time")),
            "text": unescape(text) if isinstance(text, str) else None,
            **_flags(item),
        }

    def _upsert(self, session, tbl, rows: list[dict], update_cols: tuple[str, ...]) -> int:
        dialect = session.bind.dialect.name
        if dialect in ("sqlite", "postgresql"):
            if dialect == "sqlite":
                from sqlalchemy.dialects.sqlite import insert as dialect_insert
            else:
                from sqlalchemy.dialects.postgresql import insert as dialect_insert
            stmt = dialect_insert(tbl)
            stmt = stmt.on_conflict_do_update(
                index_elements=[tbl.c.id],
                set_={c: stmt.excluded[c] for c in update_cols},
            )
        elif dialect in ("mysql", "mariadb"):
            from sqlalchemy.dialects.mysql import insert as my_insert
            ins = my_insert(tbl)
            stmt = ins.on_duplicate_key_update({c: ins.inserted[c] for c in update_cols})
        else:
            stmt = tbl.insert()

        # executemany вместо одного INSERT ... VALUES (...), (...): драйвер сам пакетирует,
        # и не упираемся в лимит числа параметров SQLite (32766) при большом batch_size
        session.execute(stmt, rows)
        session.commit()
        return len(rows)

    def select_all_stories(self) -> Iterable[Story]:
        with self.SessionLocal() as session:
            yield from session.scalars(select(Story))

    def select_all_comments(self) -> Iterable[Comment]:
        with self.SessionLocal() as session:
            yield from session.scalars(select(Comment))

    def select_comments_by_parent(self, parent_id: int) -> Iterable[Comment]:
        with self.SessionLocal() as session:
            yield from session.scalars(select(Comment).where(Comment.parent == parent_id))
