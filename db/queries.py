from typing import Iterator, Tuple
from sqlalchemy import or_
from sqlalchemy.orm import Session
from .models import Story


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