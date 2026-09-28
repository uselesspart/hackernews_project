from collections.abc import Iterator

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .models import Story, Tech


def is_alive(model):
    """Условие: запись не помечена в HN как dead/deleted (NULL — для старых данных)."""
    return and_(
        or_(model.dead.is_(None), model.dead.is_(False)),
        or_(model.deleted.is_(None), model.deleted.is_(False)),
    )


def has_techs():
    """Условие: у истории есть хотя бы одна технология (после classify_tech)."""
    return Story.techs.any()


def iter_story_titles(session: Session,
                      keep_deleted: bool = False,
                      limit: int | None = None,
                      with_techs_only: bool = False) -> Iterator[tuple[int, str]]:
    stmt = select(Story.id, Story.title).where(Story.title.isnot(None), Story.title != "").order_by(Story.id)
    if not keep_deleted:
        stmt = stmt.where(is_alive(Story))
    if with_techs_only:
        stmt = stmt.where(has_techs())
    if limit:
        stmt = stmt.limit(limit)
    yield from session.execute(stmt.execution_options(yield_per=1000)).tuples()


def iter_tech_names(session: Session, limit: int | None = None) -> Iterator[tuple[int, str]]:
    stmt = select(Tech.id, Tech.name).where(Tech.name.isnot(None), Tech.name != "").order_by(Tech.id)
    if limit:
        stmt = stmt.limit(limit)
    yield from session.execute(stmt.execution_options(yield_per=1000)).tuples()
