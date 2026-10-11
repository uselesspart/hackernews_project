"""Запросы к БД для API: живые (статьи, связи) и чтение предрассчитанных таблиц."""
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from db.models import Comment, SentimentExample, Story, Tech, TechMetrics, TechNeighbor, TechWord, story_tech
from db.queries import is_alive

HN_ITEM_URL = "https://news.ycombinator.com/item?id={}"

STORY_SORTS = {
    "score": Story.score.desc(),
    "comments": Story.descendants.desc(),
    "time": Story.time.desc(),
}


def hn_url(item_id: int) -> str:
    return HN_ITEM_URL.format(item_id)


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    netloc = urlparse(url).netloc.lower()
    return netloc.removeprefix("www.") or None


def tech_rows(session: Session) -> dict[str, tuple[int, TechMetrics | None]]:
    """key -> (tech_id, метрики или None, если precompute ещё не запускался)."""
    stmt = select(Tech.name, Tech.id, TechMetrics).outerjoin(TechMetrics, TechMetrics.tech_id == Tech.id)
    return {name: (tech_id, metrics) for name, tech_id, metrics in session.execute(stmt)}


def alive_story_count(session: Session) -> int:
    return session.scalar(select(func.count(Story.id)).where(is_alive(Story))) or 0


def dataset_meta(session: Session) -> dict:
    start, end = period_bounds(session)
    return {
        "stories": alive_story_count(session),
        "comments": session.scalar(select(func.count(Comment.id))) or 0,
        "techs_with_stories": session.scalar(select(func.count(func.distinct(story_tech.c.tech_id)))) or 0,
        "period_start": start,
        "period_end": end,
        "computed_at": session.scalar(select(func.max(TechMetrics.computed_at))),
    }


def _tech_stories(tech_id: int):
    return (
        select(Story)
        .join(story_tech, story_tech.c.story_id == Story.id)
        .where(story_tech.c.tech_id == tech_id, is_alive(Story))
    )


def live_stats(session: Session, tech_id: int) -> dict:
    sub = _tech_stories(tech_id).subquery()
    n, comments, avg_score, first, last = session.execute(
        select(func.count(sub.c.id), func.coalesce(func.sum(sub.c.descendants), 0),
               func.avg(sub.c.score), func.min(sub.c.time), func.max(sub.c.time))
    ).one()
    return {"stories": n, "comments": int(comments), "avg_score": avg_score,
            "first_story_at": first, "last_story_at": last}


def cooccurring(session: Session, tech_id: int, limit: int = 10) -> list[tuple[str, int]]:
    """Технологии, упомянутые в тех же статьях: (key, число общих статей)."""
    own, other = aliased(story_tech), aliased(story_tech)
    n = func.count(other.c.story_id)
    stmt = (
        select(Tech.name, n)
        .select_from(own)
        .join(other, (other.c.story_id == own.c.story_id) & (other.c.tech_id != own.c.tech_id))
        .join(Tech, Tech.id == other.c.tech_id)
        .join(Story, Story.id == own.c.story_id)
        .where(own.c.tech_id == tech_id, is_alive(Story))
        .group_by(Tech.name)
        .order_by(n.desc(), Tech.name)
        .limit(limit)
    )
    return [(name, count) for name, count in session.execute(stmt)]


def domains(session: Session, tech_id: int, limit: int = 10) -> list[tuple[str, int]]:
    urls = session.scalars(select(Story.url).join(story_tech, story_tech.c.story_id == Story.id)
                           .where(story_tech.c.tech_id == tech_id, is_alive(Story), Story.url.isnot(None)))
    return Counter(d for d in map(domain_of, urls) if d).most_common(limit)


def neighbors(session: Session, tech_id: int) -> list[tuple[str, float]]:
    stmt = (
        select(Tech.name, TechNeighbor.similarity)
        .join(Tech, Tech.id == TechNeighbor.neighbor_id)
        .where(TechNeighbor.tech_id == tech_id)
        .order_by(TechNeighbor.similarity.desc())
    )
    return [(name, sim) for name, sim in session.execute(stmt)]


def words(session: Session, tech_id: int, limit: int) -> list[tuple[str, int]]:
    stmt = (select(TechWord.word, TechWord.count).where(TechWord.tech_id == tech_id)
            .order_by(TechWord.count.desc(), TechWord.word).limit(limit))
    return [(w, c) for w, c in session.execute(stmt)]


def sentiment_examples(session: Session, tech_id: int) -> list[SentimentExample]:
    return list(session.scalars(
        select(SentimentExample).where(SentimentExample.tech_id == tech_id)
        .order_by(SentimentExample.score.desc())
    ))


def stories_page(session: Session, tech_id: int, sort: str, limit: int, offset: int) -> tuple[int, list[Story]]:
    base = _tech_stories(tech_id)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = session.scalars(base.order_by(STORY_SORTS[sort], Story.id.desc()).limit(limit).offset(offset))
    return total, list(items)


def story_times(session: Session, tech_id: int) -> list[datetime]:
    return [t for t in session.scalars(select(Story.time).join(story_tech, story_tech.c.story_id == Story.id)
                                       .where(story_tech.c.tech_id == tech_id, is_alive(Story),
                                              Story.time.isnot(None)))]


def period_bounds(session: Session) -> tuple[datetime | None, datetime | None]:
    return session.execute(select(func.min(Story.time), func.max(Story.time)).where(is_alive(Story))).one()
