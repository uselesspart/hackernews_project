"""
Предрасчёт данных для API: метрики технологий, соседи по Word2Vec, координаты на карте,
частые слова, тональность с примерами комментариев и IRR. Результат пишется в таблицы
tech_metrics, tech_neighbor, tech_word, sentiment_example; API их только читает.

Тональность и слова считаются по всем комментариям веток за один проход: комментарий
к статье о Rust и Go читается и оценивается один раз, а засчитывается обеим технологиям.
"""
import argparse
from collections import Counter
from datetime import UTC, datetime
from math import isfinite

import pandas as pd
from gensim.models import Word2Vec
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from analytics.catalog import tech_info
from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.embeddings.projection import embed_2d
from analytics.embeddings.scripts.calculate_irr import compute_irr
from analytics.embeddings.w2v_quality import format_report, quality_report, tech_similarity
from analytics.sentiment import CommentParts, TechSentiment, mention_text, split_comment
from db import session_scope
from db.models import SentimentExample, Story, Tech, TechMetrics, TechNeighbor, TechWord, story_tech
from db.queries import is_alive, iter_tech_thread_comments, story_tech_keys
from utils.cli import cli_main
from utils.groups import normalize_token
from utils.lemmatize import tokenize_and_lemmatize_many
from utils.words import content_words

# Комментарии обрабатываются пачками: новые слова пачки уходят в spaCy одним вызовом
CHUNK_SIZE = 5000


def story_stats(session: Session) -> dict[int, dict]:
    """Число статей, сумма комментариев, средний score и период — по каждой технологии."""
    stmt = (
        select(
            story_tech.c.tech_id,
            func.count(Story.id),
            func.coalesce(func.sum(Story.descendants), 0),
            func.avg(Story.score),
            func.min(Story.time),
            func.max(Story.time),
        )
        .join(Story, Story.id == story_tech.c.story_id)
        .where(is_alive(Story))
        .group_by(story_tech.c.tech_id)
    )
    return {
        tech_id: {"stories": n, "comments": int(comments), "avg_score": avg_score,
                  "first_story_at": first, "last_story_at": last}
        for tech_id, n, comments, avg_score, first, last in session.execute(stmt)
    }


def comment_profiles(session: Session, keys: list[str], *, threshold: float, n_examples: int,
                     lemmatize: bool) -> tuple[dict[str, TechSentiment], dict[str, Counter]]:
    """
    Тональность (весь комментарий и предложения с упоминанием технологии) и частые слова
    по всем комментариям веток. Цитаты и код не входят ни в оценку, ни в слова.
    """
    story_keys = story_tech_keys(session)
    vader = SentimentIntensityAnalyzer()
    sentiments = {key: TechSentiment(n_examples, threshold) for key in keys}
    words = {key: Counter() for key in keys}
    stops = {key: stop_words_for(key) for key in keys}

    def process(chunk: list[tuple[int, CommentParts, list[str]]]) -> None:
        lemmas = tokenize_and_lemmatize_many([parts.prose for _, parts, _ in chunk], lemmatize_en=lemmatize)
        for (cid, parts, tech_keys), tokens in zip(chunk, lemmas, strict=True):
            whole = vader.polarity_scores(parts.prose)["compound"]
            content = content_words(" ".join(tokens))
            for key in tech_keys:
                pattern = COMPILED_PATTERNS.get(key)
                mention = mention_text(parts, pattern) if pattern else None
                aspect = vader.polarity_scores(mention)["compound"] if mention else None
                sentiments[key].add(cid, parts, whole, aspect, pattern)
                words[key].update(w for w in content if w not in stops[key])

    chunk, done = [], 0
    for cid, raw, story_id in iter_tech_thread_comments(session):
        tech_keys = [k for k in story_keys.get(story_id, ()) if k in sentiments]
        parts = split_comment(raw)
        if not tech_keys or not parts.prose:
            continue
        chunk.append((cid, parts, tech_keys))
        if len(chunk) >= CHUNK_SIZE:
            process(chunk)
            done += len(chunk)
            chunk = []
            print(f"  комментариев обработано: {done}")
    process(chunk)
    return sentiments, words


def stop_words_for(key: str) -> set[str]:
    """Название самой технологии и её однословные синонимы не несут информации в её облаке слов."""
    info = tech_info(key)
    words = {key, normalize_token(info.name)}
    words.update(a.lower() for a in info.aliases if " " not in a)
    return words


def neighbors_and_map(kv, keys: list[str], n_neighbors: int):
    """
    Соседи по косинусной близости и 2D-координаты t-SNE для технологий, которые есть в словаре модели.
    Возвращает ({key: [(neighbor_key, sim), ...]}, {key: (x, y)}).
    """
    present, sim = tech_similarity(kv, keys)
    if len(present) < 2:
        return {}, {}

    neighbors = {}
    for i, key in enumerate(present):
        order = [j for j in (-sim[i]).argsort() if j != i][:n_neighbors]
        neighbors[key] = [(present[j], float(sim[i, j])) for j in order]

    coords = {}
    if len(present) >= 3:
        emb = embed_2d(pd.DataFrame(sim, index=present, columns=present), present, "similarity")
        coords = {key: (float(x), float(y)) for key, (x, y) in zip(present, emb, strict=True)}
    return neighbors, coords


def _finite(value) -> float | None:
    """inf и NaN в БД не пишем: JSON их не допускает, а как измерение они ничего не значат."""
    value = float(value)
    return value if isfinite(value) else None


def irr_by_tech(session: Session, w2v: Word2Vec, family: str) -> dict[str, dict]:
    """IRR по всем живым статьям (базовая категория — статьи без отслеживаемых технологий)."""
    rows = session.execute(
        select(Story.title, Story.descendants, Story.url)
        .where(is_alive(Story), Story.title.isnot(None), Story.descendants.isnot(None), Story.descendants >= 0)
    ).all()
    df = pd.DataFrame(rows, columns=["title", "descendants", "url"])
    try:
        # Все технологии не реже MIN_FREQ статей, а не топ-50: API нужен IRR для каждой
        coefs = compute_irr(df, w2v, family=family, top_n=None)
    except Exception as e:  # мало данных, вырожденная модель — остальной предрасчёт от этого не зависит
        print(f"IRR пропущен: {e!r}")
        return {}
    coefs = coefs.set_index("feature")
    return {
        feature.removeprefix("has_"): {
            "irr": _finite(row.IRR), "irr_low": _finite(row.IRR_low), "irr_high": _finite(row.IRR_high),
            "irr_pval": _finite(row.pval),
        }
        for feature, row in coefs.iterrows()
        if feature.startswith("has_") and not feature.startswith("has_pair_")
    }


def sentiment_columns(s: TechSentiment) -> dict:
    """Колонки tech_metrics: общий тон (sentiment_*, *_share) и аспектный (aspect_*)."""
    row = {"sentiment_n": len(s.whole), "aspect_n": len(s.aspect)}
    for prefix, summary in (("", s.summary("whole")), ("aspect_", s.summary("aspect"))):
        if summary:
            row[f"{prefix or 'sentiment_'}index"] = summary["sentiment_index"]
            row.update({f"{prefix}{k}": summary[k] for k in ("pos_share", "neu_share", "neg_share")})
    return row


def precompute(session: Session, *, context_model: str | None = None, titles_model: str | None = None,
               n_words: int = 100, n_neighbors: int = 10, n_examples: int = 3, threshold: float = 0.12,
               lemmatize: bool = True, family: str = "negbin", allow_degenerate: bool = False) -> dict[str, int]:
    techs = {name: tech_id for tech_id, name in session.execute(select(Tech.id, Tech.name))}
    stats = story_stats(session)
    now = datetime.now(UTC)

    neighbors, coords = {}, {}
    if context_model:
        print("Соседи и карта по модели контекста...")
        kv = Word2Vec.load(context_model).wv
        report = quality_report(kv, list(techs))
        print(format_report(report))
        if report["degenerate"] and not allow_degenerate:
            # Порядок соседей у такой модели — шум, а страница подаёт его как «похожий контекст»
            print("Соседи и карта пропущены: модель не различает технологии "
                  "(записать всё равно — --allow-degenerate-model)")
        else:
            neighbors, coords = neighbors_and_map(kv, list(techs), n_neighbors)
    irr = {}
    if titles_model:
        print("IRR по всем статьям...")
        irr = irr_by_tech(session, Word2Vec.load(titles_model), family)

    print("Тональность и слова по всем комментариям...")
    with_stories = [key for key, tech_id in techs.items() if stats.get(tech_id, {}).get("stories")]
    sentiments, tech_words = comment_profiles(session, with_stories, threshold=threshold,
                                              n_examples=n_examples, lemmatize=lemmatize)

    metrics, words, examples = [], [], []
    for key, tech_id in techs.items():
        row = {"tech_id": tech_id, "computed_at": now, "stories": 0, "comments": 0, "sentiment_n": 0, "aspect_n": 0}
        row.update(stats.get(tech_id, {}))
        row.update(irr.get(key, {}))
        if key in coords:
            row["map_x"], row["map_y"] = coords[key]

        if key in sentiments:
            s = sentiments[key]
            row.update(sentiment_columns(s))
            examples.extend({"tech_id": tech_id, **e} for e in s.examples())
            words.extend({"tech_id": tech_id, "word": w, "count": c} for w, c in tech_words[key].most_common(n_words))
            print(f"{key}: статей {row['stories']}, комментариев {len(s.whole)}, с упоминанием {len(s.aspect)}")
        metrics.append(row)

    neighbor_rows = [
        {"tech_id": techs[key], "neighbor_id": techs[other], "similarity": sim}
        for key, items in neighbors.items() for other, sim in items
    ]

    # Полный пересчёт: старые результаты удаляются в той же транзакции
    for model in (TechMetrics, TechNeighbor, TechWord, SentimentExample):
        session.execute(delete(model))
    for model, rows in ((TechMetrics, metrics), (TechNeighbor, neighbor_rows),
                        (TechWord, words), (SentimentExample, examples)):
        if rows:
            session.execute(insert(model), rows)
    session.commit()
    return {"techs": len(metrics), "neighbors": len(neighbor_rows), "words": len(words), "examples": len(examples)}


def parse_args():
    p = argparse.ArgumentParser(
        prog="precompute",
        description="Предрасчёт метрик технологий для API "
                    "(таблицы tech_metrics, tech_neighbor, tech_word, sentiment_example)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("--context-model", help="Модель Word2Vec контекста (.model): соседи и карта. Без неё — пропускаются")
    p.add_argument("--titles-model", help="Модель Word2Vec заголовков (.model): IRR. Без неё — пропускается")
    p.add_argument("--top-words", type=int, default=100, help="Сколько частых слов хранить (по умолчанию 100)")
    p.add_argument("--neighbors", type=int, default=10, help="Сколько соседей хранить (по умолчанию 10)")
    p.add_argument("--examples", type=int, default=3,
                   help="Сколько примеров комментариев каждого знака хранить (по умолчанию 3)")
    p.add_argument("--threshold", type=float, default=0.12, help="Порог меток тональности (по умолчанию 0.12)")
    p.add_argument("--family", choices=["negbin", "poisson"], default="negbin", help="Семейство GLM для IRR")
    p.add_argument("--no-lemmatize", action="store_true", help="Считать частые слова без лемматизации (без spaCy)")
    p.add_argument("--allow-degenerate-model", action="store_true",
                   help="Записать соседей и карту, даже если модель контекста не различает технологии")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    with session_scope(args.db) as session:
        counts = precompute(
            session, context_model=args.context_model, titles_model=args.titles_model,
            n_words=args.top_words, n_neighbors=args.neighbors, n_examples=args.examples,
            threshold=args.threshold, lemmatize=not args.no_lemmatize, family=args.family,
            allow_degenerate=args.allow_degenerate_model,
        )
    print(f"Готово: технологий {counts['techs']}, соседей {counts['neighbors']}, "
          f"слов {counts['words']}, примеров {counts['examples']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
