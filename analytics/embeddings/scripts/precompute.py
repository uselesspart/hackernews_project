"""
Предрасчёт данных для API: метрики технологий, соседи по Word2Vec, координаты на карте,
частые слова, тональность с примерами комментариев и IRR. Результат пишется в таблицы
tech_metrics, tech_neighbor, tech_word, sentiment_example; API их только читает.
"""
import argparse
from collections import Counter
from datetime import UTC, datetime
from random import Random

import numpy as np
import pandas as pd
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from analytics.catalog import tech_info
from analytics.embeddings.projection import embed_2d
from analytics.embeddings.scripts.calculate_irr import compute_irr
from analytics.embeddings.scripts.calculate_sentiment import compute_corpus_summary, label_from_score
from db import session_scope
from db.models import SentimentExample, Story, Tech, TechMetrics, TechNeighbor, TechWord, story_tech
from db.queries import is_alive
from db.scripts.export_comments_for_techs import thread_comments_for_tech
from utils.clean_text import clean_text
from utils.cli import cli_main
from utils.groups import normalize_token
from utils.lemmatize import tokenize_and_lemmatize
from utils.words import build_frequencies

EXAMPLE_MAX_CHARS = 600


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


def sample_comments(comments: list[tuple[int, str]], max_n: int, seed: int = 0) -> list[tuple[int, str]]:
    """Не больше max_n комментариев; выборка воспроизводима и сохраняет порядок по id."""
    if len(comments) <= max_n:
        return comments
    return sorted(Random(seed).sample(comments, max_n))


def sentiment_profile(comments: list[tuple[int, str]], vader, threshold: float, n_examples: int):
    """Сводка VADER (как в calculate_sentiment --mode vader) и самые полярные комментарии."""
    scored = [(cid, text, vader.polarity_scores(text)["compound"])
              for cid, text in ((cid, clean_text(raw)) for cid, raw in comments) if text]
    if not scored:
        return None, []
    rows = [(i, label_from_score(s, threshold), s, text) for i, (_, text, s) in enumerate(scored)]
    summary = compute_corpus_summary(rows, mode="vader", thr=threshold)

    by_score = sorted(scored, key=lambda x: x[2])
    positive = [x for x in reversed(by_score) if x[2] > threshold][:n_examples]
    negative = [x for x in by_score if x[2] < -threshold][:n_examples]
    examples = [
        {"comment_id": cid, "label": label, "score": score, "text": text[:EXAMPLE_MAX_CHARS]}
        for label, group in ((1, positive), (-1, negative))
        for cid, text, score in group
    ]
    return summary, examples


def top_words(comments: list[tuple[int, str]], extra_stop: set[str], n: int, lemmatize: bool) -> list[tuple[str, int]]:
    texts = [" ".join(tokenize_and_lemmatize(clean_text(raw), lemmatize_en=lemmatize)) for _, raw in comments]
    return Counter(build_frequencies(texts, extra_stop=extra_stop)).most_common(n)


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
    present = [k for k in keys if normalize_token(k) in kv.key_to_index]
    if len(present) < 2:
        return {}, {}
    sim = cosine_similarity(np.stack([kv.get_vector(normalize_token(k)) for k in present]))

    neighbors = {}
    for i, key in enumerate(present):
        order = [j for j in np.argsort(-sim[i]) if j != i][:n_neighbors]
        neighbors[key] = [(present[j], float(sim[i, j])) for j in order]

    coords = {}
    if len(present) >= 3:
        emb = embed_2d(pd.DataFrame(sim, index=present, columns=present), present, "similarity")
        coords = {key: (float(x), float(y)) for key, (x, y) in zip(present, emb, strict=True)}
    return neighbors, coords


def irr_by_tech(session: Session, w2v: Word2Vec, family: str) -> dict[str, dict]:
    """IRR по всем живым статьям (базовая категория — статьи без технологий из топа)."""
    rows = session.execute(
        select(Story.title, Story.descendants)
        .where(is_alive(Story), Story.title.isnot(None), Story.descendants.isnot(None), Story.descendants >= 0)
    ).all()
    df = pd.DataFrame(rows, columns=["title", "descendants"])
    try:
        coefs = compute_irr(df, w2v, family=family)
    except Exception as e:  # мало данных, вырожденная модель — остальной предрасчёт от этого не зависит
        print(f"IRR пропущен: {e!r}")
        return {}
    coefs = coefs.set_index("feature")
    return {
        feature.removeprefix("has_"): {
            "irr": row.IRR, "irr_low": row.IRR_low, "irr_high": row.IRR_high, "irr_pval": row.pval,
        }
        for feature, row in coefs.iterrows()
        if feature.startswith("has_") and not feature.startswith("has_pair_")
    }


def precompute(session: Session, *, context_model: str | None = None, titles_model: str | None = None,
               max_comments: int = 5000, n_words: int = 100, n_neighbors: int = 10, n_examples: int = 3,
               threshold: float = 0.12, lemmatize: bool = True, family: str = "negbin") -> dict[str, int]:
    techs = {name: tech_id for tech_id, name in session.execute(select(Tech.id, Tech.name))}
    stats = story_stats(session)
    now = datetime.now(UTC)

    neighbors, coords = {}, {}
    if context_model:
        print("Соседи и карта по модели контекста...")
        neighbors, coords = neighbors_and_map(Word2Vec.load(context_model).wv, list(techs), n_neighbors)
    irr = {}
    if titles_model:
        print("IRR по всем статьям...")
        irr = irr_by_tech(session, Word2Vec.load(titles_model), family)

    vader = SentimentIntensityAnalyzer()
    metrics, words, examples = [], [], []
    for key, tech_id in techs.items():
        row = {"tech_id": tech_id, "computed_at": now, "stories": 0, "comments": 0, "sentiment_n": 0}
        row.update(stats.get(tech_id, {}))
        row.update(irr.get(key, {}))
        if key in coords:
            row["map_x"], row["map_y"] = coords[key]

        if row["stories"]:
            comments = sample_comments(thread_comments_for_tech(session, tech_id), max_comments)
            summary, tech_examples = sentiment_profile(comments, vader, threshold, n_examples)
            if summary:
                row.update(sentiment_n=summary["n_total"], sentiment_index=summary["sentiment_index"],
                           pos_share=summary["pos_share"], neu_share=summary["neu_share"],
                           neg_share=summary["neg_share"])
                examples.extend({"tech_id": tech_id, **e} for e in tech_examples)
            words.extend({"tech_id": tech_id, "word": w, "count": c}
                         for w, c in top_words(comments, stop_words_for(key), n_words, lemmatize))
            print(f"{key}: статей {row['stories']}, комментариев в анализе {len(comments)}")
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
    p.add_argument("--max-comments", type=int, default=5000,
                   help="Максимум комментариев на технологию для тональности и слов (по умолчанию 5000)")
    p.add_argument("--top-words", type=int, default=100, help="Сколько частых слов хранить (по умолчанию 100)")
    p.add_argument("--neighbors", type=int, default=10, help="Сколько соседей хранить (по умолчанию 10)")
    p.add_argument("--examples", type=int, default=3,
                   help="Сколько примеров комментариев каждого знака хранить (по умолчанию 3)")
    p.add_argument("--threshold", type=float, default=0.12, help="Порог меток тональности (по умолчанию 0.12)")
    p.add_argument("--family", choices=["negbin", "poisson"], default="negbin", help="Семейство GLM для IRR")
    p.add_argument("--no-lemmatize", action="store_true", help="Считать частые слова без лемматизации (без spaCy)")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    with session_scope(args.db) as session:
        counts = precompute(
            session, context_model=args.context_model, titles_model=args.titles_model,
            max_comments=args.max_comments, n_words=args.top_words, n_neighbors=args.neighbors,
            n_examples=args.examples, threshold=args.threshold, lemmatize=not args.no_lemmatize,
            family=args.family,
        )
    print(f"Готово: технологий {counts['techs']}, соседей {counts['neighbors']}, "
          f"слов {counts['words']}, примеров {counts['examples']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
