from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
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
