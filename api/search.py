"""Подсказки при поиске технологии: по имени, ключу и синонимам, с терпимостью к опечаткам."""
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from analytics.catalog import TechInfo

EXACT, PREFIX, WORD_PREFIX, SUBSTRING = 100.0, 80.0, 70.0, 50.0
FUZZY_MAX, FUZZY_MIN_RATIO = 40.0, 0.75


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


@dataclass(frozen=True)
class Match:
    info: TechInfo
    stories: int
    score: float
    matched: str | None  # синоним, по которому нашлось (None — совпало имя или ключ)


def _score(query: str, candidate: str) -> float:
    if candidate == query:
        return EXACT
    if candidate.startswith(query):
        return PREFIX
    if any(word.startswith(query) for word in re.split(r"[\s./+-]+", candidate) if word):
        return WORD_PREFIX
    if query in candidate:
        return SUBSTRING
    if len(query) >= 3:
        # Опечатки: сравниваем с началом кандидата той же длины ("javscript" ~ "javascript")
        ratio = max(SequenceMatcher(None, query, candidate).ratio(),
                    SequenceMatcher(None, query, candidate[:len(query) + 1]).ratio())
        if ratio >= FUZZY_MIN_RATIO:
            return FUZZY_MAX * ratio
    return 0.0


def best_match(query: str, info: TechInfo) -> tuple[float, str | None]:
    """Лучшая оценка по имени/ключу (matched=None) и синонимам (matched=синоним)."""
    best, matched = max(_score(query, normalize(info.name)), _score(query, info.key)), None
    for alias in info.aliases:
        score = _score(query, normalize(alias))
        if score > best:
            best, matched = score, alias
    return best, matched


def suggest(query: str, entries: list[tuple[TechInfo, int]], limit: int = 8) -> list[Match]:
    """
    entries — (описание технологии, число статей). Пустой запрос — самые популярные технологии.
    Порядок: качество совпадения, затем число статей, затем имя.
    """
    q = normalize(query)
    if not q:
        ranked = sorted(entries, key=lambda e: (-e[1], e[0].name.lower()))
        return [Match(info, stories, 0.0, None) for info, stories in ranked[:limit]]

    matches = []
    for info, stories in entries:
        score, matched = best_match(q, info)
        if score > 0:
            matches.append(Match(info, stories, score, matched))
    matches.sort(key=lambda m: (-m.score, -m.stories, m.info.name.lower()))
    return matches[:limit]
