"""
Тональность комментариев HN для предрасчёта: разбор комментария на прозу, цитаты и код,
аспектный тон (только предложения, где упомянута технология) и выбор примеров.

Цитаты («> ...») — чужие слова: их тон принадлежит другому автору и часто противоположен
ответу. Код не несёт тона, но VADER находит в нём «оценочные» токены. Поэтому оценивается
только собственная проза комментария.
"""
import heapq
import re
from dataclasses import dataclass, field
from re import Pattern

from analytics.embeddings.scripts.calculate_sentiment import compute_corpus_summary, label_from_score
from utils.clean_text import clean_text

EXAMPLE_MAX_CHARS = 600
# Сколько текста до упоминания оставить в выдержке, если упоминание дальше EXAMPLE_MAX_CHARS
EXCERPT_LEAD_CHARS = 120

_PRE = re.compile(r"<pre>.*?(?:</pre>|$)", re.IGNORECASE | re.DOTALL)
_PARAGRAPH = re.compile(r"<p>", re.IGNORECASE)
# Конец предложения: знак препинания, пробел и начало следующего (заглавная, цифра или кавычка)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])")


@dataclass(frozen=True)
class CommentParts:
    paragraphs: tuple[str, ...]  # собственная проза автора, очищенная от HTML
    has_quote: bool
    has_code: bool

    @property
    def prose(self) -> str:
        return " ".join(self.paragraphs)


def split_comment(raw: str | None) -> CommentParts:
    """Абзацы прозы без цитат и блоков кода. Текст в БД уже раскодирован (ingest), теги — как в HN."""
    if not raw:
        return CommentParts((), False, False)
    without_code, n_code = _PRE.subn("<p>", raw)
    paragraphs = [p for p in (clean_text(chunk) for chunk in _PARAGRAPH.split(without_code)) if p]
    prose = tuple(p for p in paragraphs if not p.startswith(">"))
    return CommentParts(prose, has_quote=len(prose) < len(paragraphs), has_code=n_code > 0)


def sentences(paragraph: str) -> list[str]:
    return [s for s in _SENTENCE_END.split(paragraph) if s]


def mention_text(parts: CommentParts, pattern: Pattern) -> str | None:
    """Предложения с упоминанием технологии одной строкой; None — технология не упомянута."""
    found = [s for p in parts.paragraphs if pattern.search(p) for s in sentences(p) if pattern.search(s)]
    return " ".join(found) if found else None


def excerpt(text: str, pattern: Pattern | None = None, max_chars: int = EXAMPLE_MAX_CHARS) -> str:
    """
    Не длиннее max_chars. Если упоминание технологии не попадает в начало, выдержка начинается
    с его предложения и помечается «… », чтобы цитата под заголовком «о Rust» была о Rust.
    """
    m = pattern.search(text) if pattern else None
    if m is None or m.end() <= max_chars:
        return text[:max_chars]
    start = text.rfind(". ", 0, m.start()) + 2 if ". " in text[:m.start()] else 0
    if m.start() - start > EXCERPT_LEAD_CHARS:
        # Длинное предложение: начинаем незадолго до упоминания, с границы слова
        start = text.find(" ", m.start() - EXCERPT_LEAD_CHARS) + 1
    return "… " + text[start:start + max_chars - 2]


class _TopK:
    """k элементов с наибольшим ключом; при равенстве — с меньшим id (воспроизводимо)."""

    def __init__(self, k: int):
        self.k = k
        self._heap: list[tuple[float, int, str]] = []

    def push(self, key: float, item_id: int, text: str) -> None:
        entry = (key, -item_id, text)
        if len(self._heap) < self.k:
            heapq.heappush(self._heap, entry)
        elif entry > self._heap[0]:
            heapq.heapreplace(self._heap, entry)

    def items(self) -> list[tuple[int, float, str]]:
        return [(-neg_id, key, text) for key, neg_id, text in sorted(self._heap, reverse=True)]


@dataclass
class TechSentiment:
    """Накопитель тональности одной технологии: весь комментарий и аспект (предложения с упоминанием)."""
    n_examples: int
    threshold: float
    whole: list[float] = field(default_factory=list)
    aspect: list[float] = field(default_factory=list)

    def __post_init__(self):
        k = self.n_examples
        self._examples = {(scope, sign): _TopK(k) for scope in ("aspect", "whole") for sign in (1, -1)}

    def add(self, comment_id: int, parts: CommentParts, whole_score: float,
            aspect_score: float | None, pattern: Pattern | None) -> None:
        self.whole.append(whole_score)
        if aspect_score is not None:
            self.aspect.append(aspect_score)
        # Примеры — только комментарии без цитат и кода: цитата показывала бы чужие слова
        if parts.has_quote or parts.has_code or self.n_examples == 0:
            return
        for scope, score in (("whole", whole_score), ("aspect", aspect_score)):
            if score is None:
                continue
            sign = label_from_score(score, self.threshold)
            if sign:
                text = excerpt(parts.prose, pattern if scope == "aspect" else None)
                self._examples[(scope, sign)].push(score * sign, comment_id, text)

    def summary(self, scope: str) -> dict | None:
        scores = self.whole if scope == "whole" else self.aspect
        if not scores:
            return None
        rows = [(i, label_from_score(s, self.threshold), s, "") for i, s in enumerate(scores)]
        return compute_corpus_summary(rows, mode="vader", thr=self.threshold)

    def examples(self) -> list[dict]:
        """
        По каждому знаку — примеры из реплик с упоминанием технологии, а если таких нет —
        из комментариев целиком. mentions говорит фронтенду, о чём подпись: «о Rust» или «в обсуждениях».
        """
        out = []
        for sign in (1, -1):
            scope = "aspect" if self._examples[("aspect", sign)].items() else "whole"
            out.extend(
                {"comment_id": cid, "label": sign, "score": key * sign, "text": text, "mentions": scope == "aspect"}
                for cid, key, text in self._examples[(scope, sign)].items()
            )
        return out
