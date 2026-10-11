"""Схемы ответов API."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Category(BaseModel):
    key: str
    name: str


class TechRef(BaseModel):
    key: str
    name: str


class Suggestion(TechRef):
    category: str | None = Field(description="Название основной категории")
    stories: int
    matched: str | None = Field(description="Синоним, по которому найдена технология; null — совпало имя")


class DatasetMeta(BaseModel):
    stories: int
    comments: int
    techs_with_stories: int
    period_start: datetime | None
    period_end: datetime | None
    computed_at: datetime | None = Field(description="Когда последний раз запускался precompute")


class SentimentBrief(BaseModel):
    index: float | None
    n: int = Field(description="Сколько комментариев оценено")
    reliable: bool


class IrrBrief(BaseModel):
    value: float | None
    low: float | None
    high: float | None
    pval: float | None
    reliable: bool
    significant: bool = Field(description="95% интервал не включает 1")


class TechListItem(TechRef):
    categories: list[Category]
    stories: int
    comments: int
    avg_score: float | None
    sentiment: SentimentBrief
    irr: IrrBrief
    map_x: float | None
    map_y: float | None


class CommentExample(BaseModel):
    comment_id: int
    label: Literal[1, -1]
    score: float
    text: str
    hn_url: str


class Sentiment(SentimentBrief):
    pos_share: float | None
    neu_share: float | None
    neg_share: float | None
    positive: list[CommentExample]
    negative: list[CommentExample]


class TechStats(BaseModel):
    stories: int
    comments: int
    avg_score: float | None
    first_story_at: datetime | None
    last_story_at: datetime | None
    rank: int | None = Field(description="Место по числу статей среди технологий с данными")
    share: float = Field(description="Доля от всех статей выборки")


class Neighbor(TechRef):
    similarity: float


class CoTech(TechRef):
    stories: int = Field(description="Число статей, где технологии упомянуты вместе")


class Word(BaseModel):
    word: str
    count: int


class Domain(BaseModel):
    domain: str
    count: int


class MapPoint(BaseModel):
    x: float
    y: float


class TechProfile(TechRef):
    aliases: list[str]
    categories: list[Category]
    areas: list[Category]
    stats: TechStats
    sentiment: Sentiment
    irr: IrrBrief
    neighbors: list[Neighbor]
    cooccurring: list[CoTech]
    words: list[Word]
    domains: list[Domain]
    map: MapPoint | None


class StoryOut(BaseModel):
    id: int
    title: str | None
    url: str | None
    domain: str | None
    score: int | None
    comments: int | None
    time: datetime | None
    hn_url: str


class StoriesPage(BaseModel):
    total: int
    items: list[StoryOut]


class TimelinePoint(BaseModel):
    period: date = Field(description="Начало периода (день, понедельник недели или 1-е число месяца)")
    stories: int


class Timeline(BaseModel):
    bucket: Literal["day", "week", "month"]
    span_days: float = Field(description="Охват выборки в днях: по нему фронтенд решает, показывать ли динамику")
    points: list[TimelinePoint]
