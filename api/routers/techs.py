from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from analytics.catalog import CATALOG, GROUP_NAMES, TechInfo, tech_info
from api import queries as q
from api.config import Settings
from api.deps import SessionDep, SettingsDep
from api.schemas import (
    Category,
    CommentExample,
    CoTech,
    Domain,
    IrrBrief,
    MapPoint,
    Neighbor,
    Sentiment,
    SentimentBrief,
    StoriesPage,
    StoryOut,
    Suggestion,
    TechListItem,
    TechProfile,
    TechStats,
    Timeline,
    TimelinePoint,
    Word,
)
from api.search import suggest
from db.models import TechMetrics

router = APIRouter(prefix="/api/techs", tags=["techs"])


def _categories(keys) -> list[Category]:
    return [Category(key=k, name=GROUP_NAMES.get(k, k)) for k in keys]


def _all_techs(session: Session) -> dict[str, tuple[TechInfo, int | None, TechMetrics | None]]:
    """Каталог + технологии из БД: key -> (описание, tech_id или None, метрики или None)."""
    rows = q.tech_rows(session)
    keys = list(dict.fromkeys([*CATALOG, *rows]))
    return {key: (tech_info(key), *rows.get(key, (None, None))) for key in keys}


def _sentiment_brief(m: TechMetrics | None, settings: Settings) -> SentimentBrief:
    n = m.sentiment_n if m else 0
    return SentimentBrief(index=m.sentiment_index if m else None, n=n,
                          reliable=n >= settings.min_sentiment_comments and m.sentiment_index is not None)


def _irr_brief(m: TechMetrics | None, stories: int, settings: Settings) -> IrrBrief:
    if m is None or m.irr is None:
        return IrrBrief(value=None, low=None, high=None, pval=None, reliable=False, significant=False)
    significant = m.irr_low is not None and m.irr_high is not None and (m.irr_low > 1 or m.irr_high < 1)
    return IrrBrief(value=m.irr, low=m.irr_low, high=m.irr_high, pval=m.irr_pval,
                    reliable=stories >= settings.min_irr_stories, significant=significant)


def _resolve(session: Session, key: str):
    techs = _all_techs(session)
    key = key.lower()
    if key not in techs:
        raise HTTPException(status_code=404, detail=f"Технология {key!r} не отслеживается")
    return key, techs


@router.get("/suggest", response_model=list[Suggestion], summary="Подсказки для строки поиска")
def suggest_techs(session: SessionDep, q_: str = Query("", alias="q", max_length=100),
                  limit: int = Query(8, ge=1, le=50)):
    entries = [(info, m.stories if m else 0) for info, _, m in _all_techs(session).values()]
    return [
        Suggestion(key=m.info.key, name=m.info.name, stories=m.stories, matched=m.matched,
                   category=GROUP_NAMES.get(m.info.categories[0]) if m.info.categories else None)
        for m in suggest(q_, entries, limit)
    ]


@router.get("", response_model=list[TechListItem], summary="Список технологий с метриками (рейтинги, карта)")
def list_techs(session: SessionDep, settings: SettingsDep,
               sort: Literal["stories", "comments", "sentiment", "irr", "name"] = "stories",
               min_stories: int = Query(1, ge=0), limit: int = Query(200, ge=1, le=500)):
    items = []
    for key, (info, _, m) in _all_techs(session).items():
        stories = m.stories if m else 0
        if stories < min_stories:
            continue
        items.append(TechListItem(
            key=key, name=info.name, categories=_categories(info.categories),
            stories=stories, comments=m.comments if m else 0, avg_score=m.avg_score if m else None,
            sentiment=_sentiment_brief(m, settings), irr=_irr_brief(m, stories, settings),
            map_x=m.map_x if m else None, map_y=m.map_y if m else None,
        ))
    sort_keys = {
        "stories": lambda i: -i.stories,
        "comments": lambda i: -i.comments,
        # Ненадёжные значения — в конце списка, чтобы рейтинг не возглавила технология с тремя комментариями
        "sentiment": lambda i: (not i.sentiment.reliable, -(i.sentiment.index or 0)),
        "irr": lambda i: (not i.irr.reliable, -(i.irr.value or 0)),
        "name": lambda i: i.name.lower(),
    }
    items.sort(key=lambda i: (sort_keys[sort](i), i.name.lower()))
    return items[:limit]


@router.get("/{key}", response_model=TechProfile, summary="Страница технологии")
def tech_profile(key: str, session: SessionDep, settings: SettingsDep,
                 words_limit: int = Query(50, ge=0, le=100)):
    key, techs = _resolve(session, key)
    info, tech_id, m = techs[key]

    if tech_id is None:
        stats = {"stories": 0, "comments": 0, "avg_score": None, "first_story_at": None, "last_story_at": None}
    else:
        stats = q.live_stats(session, tech_id)
    ranked = sorted((k for k, (_, _, mm) in techs.items() if mm and mm.stories), key=lambda k: -techs[k][2].stories)
    total = q.alive_story_count(session)

    def ref_name(k: str) -> str:
        return tech_info(k).name

    examples = [
        CommentExample(comment_id=e.comment_id, label=e.label, score=e.score, text=e.text,
                       hn_url=q.hn_url(e.comment_id))
        for e in (q.sentiment_examples(session, tech_id) if tech_id else [])
    ]
    brief = _sentiment_brief(m, settings)
    return TechProfile(
        key=key, name=info.name, aliases=list(info.aliases),
        categories=_categories(info.categories), areas=_categories(info.areas),
        stats=TechStats(**stats, rank=ranked.index(key) + 1 if key in ranked else None,
                        share=stats["stories"] / total if total else 0.0),
        sentiment=Sentiment(
            **brief.model_dump(),
            pos_share=m.pos_share if m else None, neu_share=m.neu_share if m else None,
            neg_share=m.neg_share if m else None,
            positive=[e for e in examples if e.label == 1],
            negative=sorted((e for e in examples if e.label == -1), key=lambda e: e.score),
        ),
        irr=_irr_brief(m, stats["stories"], settings),
        neighbors=[Neighbor(key=k, name=ref_name(k), similarity=s)
                   for k, s in (q.neighbors(session, tech_id) if tech_id else [])],
        cooccurring=[CoTech(key=k, name=ref_name(k), stories=n)
                     for k, n in (q.cooccurring(session, tech_id) if tech_id else [])],
        words=[Word(word=w, count=c) for w, c in (q.words(session, tech_id, words_limit) if tech_id else [])],
        domains=[Domain(domain=d, count=c) for d, c in (q.domains(session, tech_id) if tech_id else [])],
        map=MapPoint(x=m.map_x, y=m.map_y) if m and m.map_x is not None else None,
    )


@router.get("/{key}/stories", response_model=StoriesPage, summary="Статьи о технологии")
def tech_stories(key: str, session: SessionDep, sort: Literal["score", "comments", "time"] = "score",
                 limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    key, techs = _resolve(session, key)
    tech_id = techs[key][1]
    if tech_id is None:
        return StoriesPage(total=0, items=[])
    total, stories = q.stories_page(session, tech_id, sort, limit, offset)
    return StoriesPage(total=total, items=[
        StoryOut(id=s.id, title=s.title, url=s.url, domain=q.domain_of(s.url), score=s.score,
                 comments=s.descendants, time=s.time, hn_url=q.hn_url(s.id))
        for s in stories
    ])


def _bucket_start(t: datetime, bucket: str) -> date:
    d = t.date()
    if bucket == "week":
        return d - timedelta(days=d.weekday())
    if bucket == "month":
        return d.replace(day=1)
    return d


def _next_bucket(d: date, bucket: str) -> date:
    if bucket == "day":
        return d + timedelta(days=1)
    if bucket == "week":
        return d + timedelta(weeks=1)
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


@router.get("/{key}/timeline", response_model=Timeline, summary="Число статей по периодам")
def tech_timeline(key: str, session: SessionDep, bucket: Literal["day", "week", "month"] = "week"):
    key, techs = _resolve(session, key)
    tech_id = techs[key][1]
    start, end = q.period_bounds(session)
    if start is None or end is None:
        return Timeline(bucket=bucket, span_days=0.0, points=[])

    counts: dict[date, int] = {}
    for t in (q.story_times(session, tech_id) if tech_id else []):
        b = _bucket_start(t, bucket)
        counts[b] = counts.get(b, 0) + 1

    # Нули в пустых периодах: ось общая для всех технологий — весь период выборки
    points, current, last = [], _bucket_start(start, bucket), _bucket_start(end, bucket)
    while current <= last:
        points.append(TimelinePoint(period=current, stories=counts.get(current, 0)))
        current = _next_bucket(current, bucket)
    return Timeline(bucket=bucket, span_days=(end - start).total_seconds() / 86400, points=points)
