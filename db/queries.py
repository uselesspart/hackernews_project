from sqlalchemy import or_
from sqlalchemy.orm import Session
from .models import Story, Tech, Comment
from typing import Tuple, Iterator
from scripts.clean_text import clean_text

def iter_story_titles(session: Session,
                      keep_deleted: bool = False,
                      limit: int | None = None) -> Iterator[Tuple[int, str]]:
    q = session.query(Story.id, Story.title)
    q = q.filter(Story.title.isnot(None)).filter(Story.title != "")

    if not keep_deleted:
        if hasattr(Story, "deleted"):
            q = q.filter(or_(Story.deleted.is_(None), Story.deleted.is_(False)))
        if hasattr(Story, "dead"):
            q = q.filter(or_(Story.dead.is_(None), Story.dead.is_(False)))

    if limit:
        q = q.limit(limit)

    for row in q.yield_per(1000):
        yield row.id, row.title

def iter_tech_names(session: Session,
                      limit: int | None = None) -> Iterator[Tuple[int, str]]:
    q = session.query(Tech.id, Tech.name)
    q = q.filter(Tech.name.isnot(None)).filter(Tech.name != "")

    if limit:
        q = q.limit(limit)

    for row in q.yield_per(1000):
        yield row.id, row.name

def iter_story_titles_comments(session: Session,
                               keep_deleted: bool = False,
                               limit: int | None = None) -> Iterator[Tuple[int, str]]:
    q = session.query(Story.id, Story.title)
    q = q.filter(Story.title.isnot(None)).filter(Story.title != "")

    if limit:
        q = q.limit(limit)

    for story in q.yield_per(1000):
        parts = []
        cq = session.query(Comment).filter(Comment.parent == story.id)
        for comment in cq.yield_per(1000):
            if comment.text:
                parts.append(clean_text(comment.text))
        context = " ".join(p for p in parts if p).strip()
        if context:
            yield story.id, story.title, context
