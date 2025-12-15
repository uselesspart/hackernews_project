import json
import gzip
from pathlib import Path
from typing import Iterator, Optional, Iterable
from datetime import datetime, timezone
from html import unescape

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from db.models import Base, Story, Comment

class HNHandler:
    def __init__(self, engine, batch_size: int = 1000):
        self.engine = engine
        self.batch_size = batch_size
        self.SessionLocal = sessionmaker(bind=engine)
        self.create_schema()

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)


    def ingest_from_path(self, path: str | Path) -> dict[str, int]:
        story_batch: list[dict] = []
        comment_batch: list[dict] = []
        cnt_stories = 0
        cnt_comments = 0

        with self.SessionLocal() as session:
            def flush():
                nonlocal cnt_stories, cnt_comments
                # дедупликат внутри батча по id, чтобы не ловить конфликт в одном наборе
                if story_batch:
                    story_by_id = {row["id"]: row for row in story_batch}
                    cnt_stories += self._upsert_stories(session, list(story_by_id.values()))
                    story_batch.clear()
                if comment_batch:
                    comment_by_id = {row["id"]: row for row in comment_batch}
                    cnt_comments += self._upsert_comments(session, list(comment_by_id.values()))
                    comment_batch.clear()

            for item in iter_items(path):
                t = item.get("type")
                if t == "story":
                    story = self._story_row(item)
                    if story:
                        story_batch.append(story)
                elif t == "comment":
                    comment = self._comment_row(item)
                    if comment:
                        comment_batch.append(comment)

                if len(story_batch) + len(comment_batch) >= self.batch_size:
                    flush()

            if story_batch or comment_batch:
                flush()

        return {"stories": cnt_stories, "comments": cnt_comments}

    # Преобразование в dict для Core-вставки
    def _story_row(self, item: dict) -> Optional[dict]:
        if item.get("type") != "story" or not item.get("title"):
            return None
        ts = item.get("time")
        dt = datetime.fromtimestamp(ts, tz=timezone.utc) if isinstance(ts, (int, float)) else None
        return {
            "id": item.get("id"),
            "author": item.get("by"),
            "descendants": item.get("descendants"),
            "score": item.get("score"),
            "time": dt,
            "title": item.get("title"),
            "url": item.get("url"),
            "kids": item.get("kids", []) or [],
        }

    def _comment_row(self, item: dict) -> Optional[dict]:
        if item.get("type") != "comment":
            return None
        ts = item.get("time")
        dt = datetime.fromtimestamp(ts, tz=timezone.utc) if isinstance(ts, (int, float)) else None
        text_raw = item.get("text")
        text = unescape(text_raw) if isinstance(text_raw, str) else None
        return {
            "id": item.get("id"),
            "author": item.get("by"),
            "parent": item.get("parent"),
            "time": dt,
            "text": text,
        }

    def _upsert_comments(self, session, rows: list[dict]) -> int:
        tbl = Comment.__table__
        dialect = session.bind.dialect.name
        if dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            stmt = sqlite_insert(tbl).values(rows)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=[tbl.c.id],
                set_={
                    "author": excluded.author,
                    "parent": excluded.parent,
                    "time":   excluded.time,
                    "text":   excluded.text,
                },
            )
        elif dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(tbl).values(rows)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=[tbl.c.id],
                set_={
                    "author": excluded.author,
                    "parent": excluded.parent,
                    "time":   excluded.time,
                    "text":   excluded.text,
                },
            )
        elif dialect in ("mysql", "mariadb"):
            from sqlalchemy.dialects.mysql import insert as my_insert
            ins = my_insert(tbl).values(rows)
            stmt = ins.on_duplicate_key_update(
                author=ins.inserted.author,
                parent=ins.inserted.parent,
                time=ins.inserted.time,
                text=ins.inserted.text,
            )
        else:
            stmt = tbl.insert().values(rows)

        res = session.execute(stmt)
        session.commit()
        return res.rowcount


    def _upsert_stories(self, session, rows: list[dict]) -> int:
        tbl = Story.__table__
        dialect = session.bind.dialect.name
        if dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            stmt = sqlite_insert(tbl).values(rows)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=[tbl.c.id],
                set_={
                    "author":      excluded.author,
                    "descendants": excluded.descendants,
                    "score":       excluded.score,
                    "time":        excluded.time,
                    "title":       excluded.title,
                    "url":         excluded.url,
                    "kids":        excluded.kids,
                },
            )
        elif dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(tbl).values(rows)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=[tbl.c.id],
                set_={
                    "author":      excluded.author,
                    "descendants": excluded.descendants,
                    "score":       excluded.score,
                    "time":        excluded.time,
                    "title":       excluded.title,
                    "url":         excluded.url,
                    "kids":        excluded.kids,
                },
            )
        elif dialect in ("mysql", "mariadb"):
            from sqlalchemy.dialects.mysql import insert as my_insert
            ins = my_insert(tbl).values(rows)
            stmt = ins.on_duplicate_key_update(
                author=ins.inserted.author,
                descendants=ins.inserted.descendants,
                score=ins.inserted.score,
                time=ins.inserted.time,
                title=ins.inserted.title,
                url=ins.inserted.url,
                kids=ins.inserted.kids,
            )
        else:
            stmt = tbl.insert().values(rows)

        res = session.execute(stmt)
        session.commit()
        return res.rowcount

    def _to_story(self, item: dict) -> Optional[Story]:
        if item.get("type") != "story":
            return None
        title = item.get("title")
        if not title:
            return None

        ts = item.get("time")
        dt = (
            datetime.fromtimestamp(ts, tz=timezone.utc)
            if isinstance(ts, (int, float))
            else None
        )
        return Story(
            id=item.get("id"),
            author=item.get("by"),
            descendants=item.get("descendants"),
            score=item.get("score"),
            time=dt,
            title=title,
            url=item.get("url"),
            kids=item.get("kids", []) or [],
        )

    def _to_comment(self, item: dict) -> Optional[Comment]:
        if item.get("type") != "comment":
            return None
        
        ts = item.get("time")
        dt = (
            datetime.fromtimestamp(ts, tz=timezone.utc)
            if isinstance(ts, (int, float))
            else None
        )
        text_raw = item.get("text")
        text = unescape(text_raw) if isinstance(text_raw, str) else None

        return Comment(
            id=item.get("id"),
            author=item.get("by"),
            parent=item.get("parent"),
            time=dt,
            text=text,
        )

    def select_all_stories(self) -> Iterable[Story]:
        with self.SessionLocal() as session:
            yield from session.scalars(select(Story))

    def select_all_comments(self) -> Iterable[Comment]:
        with self.SessionLocal() as session:
            yield from session.scalars(select(Comment))

    def select_comments_by_parent(self, parent_id: int) -> Iterable[Comment]:
        with self.SessionLocal() as session:
            stmt = select(Comment).where(Comment.parent == parent_id)
            yield from session.scalars(stmt)


def iter_items(path: str | Path) -> Iterator[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")

    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj
