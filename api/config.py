"""Настройки API из переменных окружения."""
import os
from dataclasses import dataclass, field


def _csv_env(name: str, default: str) -> list[str]:
    return [s.strip() for s in os.environ.get(name, default).split(",") if s.strip()]


@dataclass(frozen=True)
class Settings:
    db_url: str = field(default_factory=lambda: os.environ.get("HN_DB_URL", "sqlite:///hn.db"))
    # Адреса фронтенда в разработке (Vite — 5173, CRA/Next — 3000)
    cors_origins: list[str] = field(
        default_factory=lambda: _csv_env("HN_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    )
    # Ниже этих объёмов метрика считается ненадёжной: API отдаёт её с reliable=false
    min_sentiment_comments: int = field(default_factory=lambda: int(os.environ.get("HN_MIN_SENTIMENT_COMMENTS", 30)))
    min_irr_stories: int = field(default_factory=lambda: int(os.environ.get("HN_MIN_IRR_STORIES", 30)))
