from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


story_tech = Table(
    "story_tech",
    Base.metadata,
    Column("story_id", ForeignKey("story.id"), primary_key=True),
    # Составной PK (story_id, tech_id) не помогает поиску по tech_id — нужен отдельный индекс
    Column("tech_id", ForeignKey("tech.id"), primary_key=True, index=True),
)


class Story(Base):
    __tablename__ = "story"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author: Mapped[str | None] = mapped_column(String(50))
    descendants: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[int | None] = mapped_column(Integer)
    time: Mapped[datetime | None] = mapped_column(DateTime)
    title: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    kids: Mapped[list[int]] = mapped_column(JSON, default=list)
    dead: Mapped[bool | None] = mapped_column(Boolean)
    deleted: Mapped[bool | None] = mapped_column(Boolean)

    techs: Mapped[list["Tech"]] = relationship(
        secondary=story_tech,
        back_populates="stories",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Story(id={self.id!r}, title={self.title!r}, time={self.time!r})"


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author: Mapped[str | None] = mapped_column(String(50))
    # По parent строятся ветки (JOIN с историей и рекурсивный CTE) — без индекса это полный скан
    parent: Mapped[int | None] = mapped_column(Integer, index=True)
    time: Mapped[datetime | None] = mapped_column(DateTime)
    text: Mapped[str | None] = mapped_column(String)
    dead: Mapped[bool | None] = mapped_column(Boolean)
    deleted: Mapped[bool | None] = mapped_column(Boolean)

    def __repr__(self) -> str:
        return f"Comment(id={self.id!r}, author={self.author!r}, time={self.time!r})"


class Tech(Base):
    __tablename__ = "tech"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Не selectin: иначе загрузка любого Tech тянет за собой все его истории (тысячи строк)
    stories: Mapped[list[Story]] = relationship(
        secondary=story_tech,
        back_populates="techs",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"Tech(id={self.id!r}, name={self.name!r})"


# --- Предрассчитанные данные для API (заполняются analytics.embeddings.scripts.precompute) ---

class TechMetrics(Base):
    """Сводные метрики технологии. Порог достоверности решает API: здесь хранятся и объёмы выборок."""
    __tablename__ = "tech_metrics"

    tech_id: Mapped[int] = mapped_column(ForeignKey("tech.id"), primary_key=True)
    stories: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)  # сумма descendants статей
    avg_score: Mapped[float | None] = mapped_column(Float)
    first_story_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_story_at: Mapped[datetime | None] = mapped_column(DateTime)

    sentiment_n: Mapped[int] = mapped_column(Integer, default=0)  # сколько комментариев оценено
    sentiment_index: Mapped[float | None] = mapped_column(Float)
    pos_share: Mapped[float | None] = mapped_column(Float)
    neu_share: Mapped[float | None] = mapped_column(Float)
    neg_share: Mapped[float | None] = mapped_column(Float)

    irr: Mapped[float | None] = mapped_column(Float)
    irr_low: Mapped[float | None] = mapped_column(Float)
    irr_high: Mapped[float | None] = mapped_column(Float)
    irr_pval: Mapped[float | None] = mapped_column(Float)

    map_x: Mapped[float | None] = mapped_column(Float)
    map_y: Mapped[float | None] = mapped_column(Float)

    computed_at: Mapped[datetime | None] = mapped_column(DateTime)


class TechNeighbor(Base):
    """Ближайшие технологии по косинусной близости векторов Word2Vec."""
    __tablename__ = "tech_neighbor"

    tech_id: Mapped[int] = mapped_column(ForeignKey("tech.id"), primary_key=True)
    neighbor_id: Mapped[int] = mapped_column(ForeignKey("tech.id"), primary_key=True)
    similarity: Mapped[float] = mapped_column(Float)


class TechWord(Base):
    """Частые слова (леммы) в комментариях к статьям о технологии."""
    __tablename__ = "tech_word"

    tech_id: Mapped[int] = mapped_column(ForeignKey("tech.id"), primary_key=True)
    word: Mapped[str] = mapped_column(String(100), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)


class SentimentExample(Base):
    """Самые положительные и отрицательные комментарии технологии (со ссылкой на комментарий HN)."""
    __tablename__ = "sentiment_example"

    tech_id: Mapped[int] = mapped_column(ForeignKey("tech.id"), primary_key=True)
    comment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[int] = mapped_column(Integer)  # 1 — положительный, -1 — отрицательный
    score: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(String)
