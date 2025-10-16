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
        story_batch: list[Story] = []
        comment_batch: list[Comment] = []
        cnt_stories = 0
        cnt_comments = 0

        with self.SessionLocal() as session:
            for item in iter_items(path):
                t = item.get("type")
                if t == "story":
                    story = self._to_story(item)
                    if story:
                        story_batch.append(story)
                elif t == "comment":
                    comment = self._to_comment(item)
                    if comment:
                        comment_batch.append(comment)

                if len(story_batch) + len(comment_batch) >= self.batch_size:
                    if story_batch:
                        session.add_all(story_batch)
                    if comment_batch:
                        session.add_all(comment_batch)
                    session.commit()
                    cnt_stories += len(story_batch)
                    cnt_comments += len(comment_batch)
                    story_batch.clear()
                    comment_batch.clear()

            if story_batch or comment_batch:
                if story_batch:
                    session.add_all(story_batch)
                if comment_batch:
                    session.add_all(comment_batch)
                session.commit()
                cnt_stories += len(story_batch)
                cnt_comments += len(comment_batch)

        return {"stories": cnt_stories, "comments": cnt_comments}

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
