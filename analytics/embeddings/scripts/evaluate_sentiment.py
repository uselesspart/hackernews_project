"""
Сравнение режимов тональности по ручной разметке (PLAN 2.5): какой режим выбрать для precompute.

Вход — CSV из db.scripts.export_sentiment_sample с заполненными label_comment и label_tech.
Каждый режим сравнивается с обеими разметками по macro-F1 (классы -1, 0, 1):
- vader — весь комментарий (без цитат и кода), как общий тон в precompute;
- vader_aspect — только предложения с упоминанием технологии, как аспектный тон в precompute;
- vader_window — окно ±12 слов вокруг ключа (calculate_sentiment --mode vader --keyword);
- lexicon, lexicon_aspect, bootstrap — режимы calculate_sentiment; нужны модели Word2Vec.
"""
import argparse
import csv

import numpy as np
from gensim.models import Word2Vec
from sklearn.metrics import f1_score
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.embeddings.scripts import calculate_sentiment as cs
from analytics.sentiment import mention_text, split_comment
from utils.cli import cli_main

DEFAULT_THRESHOLDS = (0.05, 0.1, 0.12, 0.2, 0.3, 0.4, 0.5)
PRECOMPUTE_THRESHOLD = 0.12
TARGETS = ("label_comment", "label_tech")


def read_labeled(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for t in TARGETS:
            value = (r.get(t) or "").strip()
            if value and value not in {"-1", "0", "1"}:
                raise ValueError(f"Комментарий {r.get('comment_id')}: {t}={value!r}, ожидается -1, 0, 1 или пусто")
            r[t] = int(value) if value else None
    return rows


def vader_scores(rows: list[dict]) -> dict[str, np.ndarray]:
    vader = SentimentIntensityAnalyzer()

    def aspect(r):
        pattern = COMPILED_PATTERNS.get(r["tech"])
        mention = mention_text(split_comment(r["text"]), pattern) if pattern else None
        return vader.polarity_scores(mention or r["text"])["compound"]

    return {
        "vader": np.array([vader.polarity_scores(r["text"])["compound"] for r in rows]),
        "vader_aspect": np.array([aspect(r) for r in rows]),
        "vader_window": np.array([cs.vader_aspect_score(r["text"], r["tech"], vader) for r in rows]),
    }


def lexicon_scores(rows: list[dict], comments_kv) -> dict[str, np.ndarray]:
    lex = cs.merge_lexicons(cs.expand_lexicon(cs.SEED_POS, cs.SEED_NEG, comments_kv, topn=100, sim_thr=0.62),
                            SentimentIntensityAnalyzer().lexicon)
    attention = {}

    def score(r, keyword):
        if keyword and keyword not in attention:
            attention[keyword] = cs.AspectAttention(comments_kv, keyword)
        return cs.aspect_sentiment_score(r["text"], comments_kv, lex, attention=attention.get(keyword))

    return {
        "lexicon": np.array([score(r, None) for r in rows]),
        "lexicon_aspect": np.array([score(r, r["tech"]) for r in rows]),
    }


def bootstrap_labels(rows: list[dict], titles_kv, comments_kv) -> np.ndarray | None:
    texts = [r["text"] for r in rows]
    lex = cs.expand_lexicon(cs.SEED_POS, cs.SEED_NEG, comments_kv, topn=100, sim_thr=0.62)
    clf = cs.bootstrap_classifier(texts, titles_kv, comments_kv, lex)
    if clf is None:
        return None
    return cs.predict_with_classifier(clf, texts, titles_kv, comments_kv)[0]


def macro_f1(y_true, y_pred) -> float:
    return float(f1_score(y_true, y_pred, labels=[-1, 0, 1], average="macro", zero_division=0))


def to_labels(scores: np.ndarray, thr: float) -> np.ndarray:
    return np.array([cs.label_from_score(s, thr) for s in scores])


def evaluate(rows: list[dict], scores: dict[str, np.ndarray], labels: dict[str, np.ndarray],
             thresholds=DEFAULT_THRESHOLDS) -> list[dict]:
    """
    Строка на (режим, разметка): F1 при пороге precompute и лучший порог.
    Лучший порог подобран на той же выборке — это оптимистичная оценка, а не проверка.
    """
    results = []
    for target in TARGETS:
        idx = [i for i, r in enumerate(rows) if r[target] is not None]
        if not idx:
            continue
        y = np.array([rows[i][target] for i in idx])
        for method, s in scores.items():
            by_thr = {thr: macro_f1(y, to_labels(s[idx], thr)) for thr in thresholds}
            best = max(by_thr, key=lambda t: (by_thr[t], -abs(t - PRECOMPUTE_THRESHOLD)))
            default = by_thr.get(PRECOMPUTE_THRESHOLD, macro_f1(y, to_labels(s[idx], PRECOMPUTE_THRESHOLD)))
            results.append({"target": target, "method": method, "n": len(idx), "f1": default,
                            "best_threshold": best, "best_f1": by_thr[best],
                            "accuracy": float((to_labels(s[idx], PRECOMPUTE_THRESHOLD) == y).mean())})
        for method, pred in labels.items():
            results.append({"target": target, "method": method, "n": len(idx), "f1": macro_f1(y, pred[idx]),
                            "best_threshold": None, "best_f1": None, "accuracy": float((pred[idx] == y).mean())})
    return results


def format_results(results: list[dict]) -> str:
    lines = []
    for target in TARGETS:
        part = sorted((r for r in results if r["target"] == target), key=lambda r: -r["f1"])
        if not part:
            continue
        lines.append(f"\nРазметка {target} (n={part[0]['n']}), macro-F1 при пороге {PRECOMPUTE_THRESHOLD}:")
        for r in part:
            best = (f"; лучший порог {r['best_threshold']:g} → {r['best_f1']:.3f} (на той же выборке)"
                    if r["best_threshold"] is not None else "")
            lines.append(f"  {r['method']:<15} F1 {r['f1']:.3f}, точность {r['accuracy']:.0%}{best}")
    return "\n".join(lines)


def parse_args():
    p = argparse.ArgumentParser(
        prog="evaluate_sentiment",
        description="Сравнение режимов тональности по ручной разметке (macro-F1)"
    )
    p.add_argument("-i", "--input", required=True, help="Размеченный CSV из db.scripts.export_sentiment_sample")
    p.add_argument("--comments-model", help="Модель Word2Vec контекста (.model): режимы lexicon и lexicon_aspect")
    p.add_argument("--titles-model", help="Модель Word2Vec заголовков (.model): вместе с --comments-model — bootstrap")
    p.add_argument("--out-csv", help="Сохранить таблицу результатов в CSV")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    rows = read_labeled(args.input)
    if not any(r[t] is not None for r in rows for t in TARGETS):
        raise ValueError("В файле нет ни одной заполненной метки label_comment или label_tech")

    scores, labels = vader_scores(rows), {}
    if args.comments_model:
        comments_kv = Word2Vec.load(args.comments_model).wv
        scores.update(lexicon_scores(rows, comments_kv))
        if args.titles_model:
            pred = bootstrap_labels(rows, Word2Vec.load(args.titles_model).wv, comments_kv)
            if pred is not None:
                labels["bootstrap"] = pred

    results = evaluate(rows, scores, labels)
    print(format_results(results))
    if args.out_csv:
        with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0]))
            writer.writeheader()
            writer.writerows(results)
        print(f"\nТаблица сохранена в {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
