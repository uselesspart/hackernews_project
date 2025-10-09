from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.types import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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

    def __repr__(self) -> str:
        return f"Story(id={self.id!r}, title={self.title!r} time={self.time!r})"
    

class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author: Mapped[Optional[str]] = mapped_column(String(50))
    parent: Mapped[Optional[int]] = mapped_column(Integer)
    time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    text: Mapped[Optional[str]] = mapped_column(String)

    def __repr__(self) -> str:
        return f"Story(id={self.id!r}, title={self.author!r} time={self.time!r})"
