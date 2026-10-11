from collections.abc import Iterator

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .models import Comment, Story, Tech, story_tech


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


def story_tech_keys(session: Session) -> dict[int, list[str]]:
    """id статьи -> ключи её технологий."""
    out: dict[int, list[str]] = {}
    stmt = select(story_tech.c.story_id, Tech.name).join(Tech, Tech.id == story_tech.c.tech_id)
    for story_id, key in session.execute(stmt):
        out.setdefault(story_id, []).append(key)
    return out


def iter_tech_thread_comments(session: Session) -> Iterator[tuple[int, str, int]]:
    """
    (id, текст, id статьи) всех живых комментариев веток к живым статьям, у которых есть технология.
    Один проход вместо запроса на каждую технологию: комментарий статьи о Rust и Go читается один раз.
    """
    base = (
        select(Comment.id.label("id"), Comment.text.label("text"), Story.id.label("story_id"),
               Comment.dead.label("dead"), Comment.deleted.label("deleted"))
        .join(Story, Comment.parent == Story.id)
        .where(is_alive(Story), Story.id.in_(select(story_tech.c.story_id)))
        .cte(name="tech_threads", recursive=True)
    )
    thread = base.union_all(
        select(Comment.id, Comment.text, base.c.story_id, Comment.dead, Comment.deleted)
        .join(base, Comment.parent == base.c.id)
    )
    # Ответы на dead/deleted комментарии остаются — отбрасываются только сами помеченные
    stmt = (
        select(thread.c.id, thread.c.text, thread.c.story_id)
        .where(thread.c.text.isnot(None), thread.c.text != "[dead]",
               or_(thread.c.dead.is_(None), thread.c.dead.is_(False)),
               or_(thread.c.deleted.is_(None), thread.c.deleted.is_(False)))
        .order_by(thread.c.id)
    )
    yield from session.execute(stmt.execution_options(yield_per=5000)).tuples()


def iter_tech_names(session: Session, limit: int | None = None) -> Iterator[tuple[int, str]]:
    stmt = select(Tech.id, Tech.name).where(Tech.name.isnot(None), Tech.name != "").order_by(Tech.id)
    if limit:
        stmt = stmt.limit(limit)
    yield from session.execute(stmt.execution_options(yield_per=1000)).tuples()
