from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


story_tech = Table(
    "story_tech",
    Base.metadata,
    Column("story_id", ForeignKey("story.id"), primary_key=True),
    Column("tech_id", ForeignKey("tech.id"), primary_key=True),
)


class Story(Base):
    __tablename__ = "story"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author: Mapped[Optional[str]] = mapped_column(String(50))
    descendants: Mapped[Optional[int]] = mapped_column(Integer)
    score: Mapped[Optional[int]] = mapped_column(Integer)
    time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    title: Mapped[Optional[str]] = mapped_column(String)
    url: Mapped[Optional[str]] = mapped_column(String)
    kids: Mapped[list[int]] = mapped_column(JSON, default=list)

    techs: Mapped[List["Tech"]] = relationship(
        secondary=story_tech,
        back_populates="stories",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Story(id={self.id!r}, title={self.title!r}, time={self.time!r})"


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author: Mapped[Optional[str]] = mapped_column(String(50))
    parent: Mapped[Optional[int]] = mapped_column(Integer)
    time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    text: Mapped[Optional[str]] = mapped_column(String)

    def __repr__(self) -> str:
        return f"Comment(id={self.id!r}, author={self.author!r}, time={self.time!r})"


class Tech(Base):
    __tablename__ = "tech"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    stories: Mapped[List[Story]] = relationship(
        secondary=story_tech,
        back_populates="techs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Tech(id={self.id!r}, name={self.name!r})"
