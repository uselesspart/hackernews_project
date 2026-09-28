import argparse
import csv
import glob
import os
import re
import sys
from collections import defaultdict

import numpy as np
from gensim.models import Word2Vec
from sklearn.linear_model import LogisticRegression
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils.cli import cli_main
from utils.io import read_nonempty_lines
from utils.vectors import cosine

SEED_POS = {
    "good", "great", "excellent", "amazing", "awesome", "fantastic", "love", "like",
    "happy", "satisfied", "recommend", "wonderful", "brilliant", "positive", "cool",
    "perfect", "nice", "solid", "helpful", "reliable"
}
SEED_NEG = {
    "bad", "terrible", "awful", "horrible", "hate", "disgusting", "trash", "worst",
    "sad", "angry", "disappointed", "scam", "fake", "useless", "broken", "poor",
    "buggy", "annoying", "ridiculous", "crap"
}
AUTO_THRESHOLD_MIN = 0.08


def tokenize(text):
    # Апостроф внутри слова сохраняется, чтобы "don't" не распадалось на "don" + "t"
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


NEGATIONS = {"not", "no", "never", "without", "none", "neither", "nor", "nothing",
             "nobody", "cannot", "dont", "doesnt", "didnt", "isnt", "arent", "wasnt",
             "werent", "cant", "couldnt", "wont", "wouldnt", "shouldnt", "havent", "hasnt"}


def is_negation(w):
    return w in NEGATIONS or w.endswith("n't")


INTENSIFIERS = {"very": 1.5, "really": 1.4, "so": 1.3, "extremely": 1.6, "super": 1.5, "highly": 1.4, "too": 1.3}
DIMINISHERS = {"slightly": 0.7, "a_little": 0.7, "somewhat": 0.75, "barely": 0.6, "hardly": 0.6}

def expand_lexicon(seed_pos, seed_neg, model, topn=80, sim_thr=0.6):
    pos_w, neg_w = defaultdict(float), defaultdict(float)
    for w in seed_pos:
        if w in model:
            pos_w[w] = max(pos_w[w], 1.0)
    for w in seed_neg:
        if w in model:
            neg_w[w] = max(neg_w[w], 1.0)
    for w in seed_pos:
        if w in model:
            for n, sim in model.most_similar(w, topn=topn):
                if sim >= sim_thr:
                    pos_w[n] = max(pos_w[n], sim)
    for w in seed_neg:
        if w in model:
            for n, sim in model.most_similar(w, topn=topn):
                if sim >= sim_thr:
                    neg_w[n] = max(neg_w[n], sim)
    pol = {}
    for w in set(pos_w) | set(neg_w):
        p = pos_w.get(w, 0.0) - neg_w.get(w, 0.0)
        pol[w] = float(np.tanh(p))
    return pol

def merge_lexicons(w2v_pol, vader_lex, alpha=0.7):
    merged = dict(w2v_pol)
    for w, v in vader_lex.items():
        v_norm = max(-1.0, min(1.0, v / 4.0))
        if w in merged:
            merged[w] = np.tanh(alpha * merged[w] + (1 - alpha) * v_norm)
        else:
            merged[w] = v_norm
    return merged

def phrase_vector(text, model):
    toks = tokenize(text)
    vecs = [model[w] for w in toks if w in model]
    if not vecs:
        return None
    return np.mean(vecs, axis=0)

class AspectAttention:
    """
    Вес слова = max(cos(слово, ключ), 0) ** p. Вектор ключа считается один раз,
    веса кэшируются по словам — вместо пересчёта для каждого комментария.
    """

    def __init__(self, model, keyword=None, p=2.0):
        self.model = model
        self.p = p
        self.kvec = phrase_vector(keyword, model) if keyword else None
        self._cache = {}

    def __call__(self, w):
        if self.kvec is None or w not in self.model:
            return 1.0
        att = self._cache.get(w)
        if att is None:
            att = max(cosine(self.model[w], self.kvec), 0.0) ** self.p
            self._cache[w] = att
        return att


def aspect_sentiment_score(text, model_comments, polarity_lex, keyword=None, p=2.0, neg_window=3,
                           attention=None):
    toks = tokenize(text)
    if attention is None:
        attention = AspectAttention(model_comments, keyword, p)

    score, weight_sum = 0.0, 0.0
    neg_span = 0
    modifier = 1.0

    toks_norm = []
    i = 0
    while i < len(toks):
        if i + 1 < len(toks) and toks[i] == "a" and toks[i + 1] == "little":
            toks_norm.append("a_little")
            i += 2
        else:
            toks_norm.append(toks[i])
            i += 1

    for w in toks_norm:
        if is_negation(w):
            neg_span = neg_window
            continue
        if w in INTENSIFIERS:
            modifier *= INTENSIFIERS[w]
            continue
        if w in DIMINISHERS:
            modifier *= DIMINISHERS[w]
            continue

        pol = polarity_lex.get(w, 0.0)
        if pol != 0.0:
            sign = -1.0 if neg_span > 0 else 1.0
            w_att = attention(w)
            contrib = pol * sign * modifier * w_att
            score += contrib
            weight_sum += abs(w_att)
            # Усилитель/ослабитель относится только к ближайшему оценочному слову
            modifier = 1.0

        if neg_span > 0:
            neg_span -= 1

    if weight_sum == 0.0:
        return 0.0
    return score / (weight_sum + 1e-9)

def label_from_score(s, thr=0.12):
    if s > thr:
        return 1
    if s < -thr:
        return -1
    return 0

def vader_aspect_score(text, keyword, vader, window=12):
    if vader is None:
        return None
    text_l = text.lower()
    toks = re.findall(r"[a-z']+", text_l)
    idxs = [i for i, w in enumerate(toks) if w == keyword.lower()]
    if not idxs:
        return vader.polarity_scores(text)["compound"]
    subscores = []
    for i in idxs:
        left = max(0, i - window)
        right = min(len(toks), i + window + 1)
        span = " ".join(toks[left:right])
        subscores.append(vader.polarity_scores(span)["compound"])
    return float(np.mean(subscores))

def doc_vec(tokens, model):
    vecs = [model[w] for w in tokens if w in model]
    if not vecs:
        return np.zeros(model.vector_size)
    return np.mean(vecs, axis=0)

def combined_doc_vec(text, model_titles, model_comments):
    toks = tokenize(text)
    v1 = doc_vec(toks, model_titles)
    v2 = doc_vec(toks, model_comments)
    return np.concatenate([v1, v2])

def bootstrap_classifier(texts, model_titles, model_comments, polarity_lex, keyword=None, top_percent=20):
    attention = AspectAttention(model_comments, keyword)
    scores = np.array([aspect_sentiment_score(t, model_comments, polarity_lex, attention=attention) for t in texts])
    labels = np.array([label_from_score(s) for s in scores])

    abs_scores = np.abs(scores)
    cut = np.percentile(abs_scores, 100 - top_percent)
    idx = abs_scores >= cut
    X = np.vstack([combined_doc_vec(texts[i], model_titles, model_comments) for i in np.where(idx)[0]])
    y = labels[idx]

    if len(y) < 50:
        print("Слишком мало уверенных псевдометок для bootstrap; используется lexicon", file=sys.stderr)
        return None

    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(X, y)
    return clf

def predict_with_classifier(clf, texts, model_titles, model_comments):
    X = np.vstack([combined_doc_vec(t, model_titles, model_comments) for t in texts])
    return clf.predict(X), clf.predict_proba(X)

def compute_corpus_summary(rows, mode, thr=0.12):
    labels = np.array([r[1] for r in rows], dtype=float)
    total = len(labels)
    pos = int((labels == 1).sum())
    neg = int((labels == -1).sum())
    neu = int((labels == 0).sum())

    summary = {
        "n_total": total,
        "n_pos": pos,
        "n_neg": neg,
        "n_neu": neu,
        "pos_share": round(pos / total, 6),
        "neg_share": round(neg / total, 6),
        "neu_share": round(neu / total, 6),
        "polarity_ratio": round((pos - neg) / max(pos + neg, 1), 6),
        "mean_label": round(float(labels.mean()), 6),
    }

    col = np.array([r[2] for r in rows], dtype=float)

    if mode in ("lexicon", "vader"):
        scores = col
        summary.update({
            "mean_score": round(float(scores.mean()), 6),
            "median_score": round(float(np.median(scores)), 6),
            "std_score": round(float(scores.std(ddof=0)), 6),
            "mean_abs_score": round(float(np.mean(np.abs(scores))), 6),
            "p25_score": round(float(np.percentile(scores, 25)), 6),
            "p75_score": round(float(np.percentile(scores, 75)), 6),
            "strong_fraction": round(float((np.abs(scores) >= thr).mean()), 6),
        })
        summary["sentiment_index"] = summary["mean_score"]
    else:
        conf = col
        summary.update({
            "avg_confidence": round(float(conf.mean()), 6),
            "median_confidence": round(float(np.median(conf)), 6),
            "p25_confidence": round(float(np.percentile(conf, 25)), 6),
            "p75_confidence": round(float(np.percentile(conf, 75)), 6),
        })
        summary["sentiment_index"] = summary["mean_label"]

    return summary

def labeled_rows(comments, scores, auto_thr, auto_percent, threshold):
    """(idx, label, score, text) по оценкам; при auto_thr порог — процентиль |score|."""
    thr = max(np.percentile(np.abs(scores), auto_percent), AUTO_THRESHOLD_MIN) if auto_thr else threshold
    rows = [(i, label_from_score(s, thr=thr), float(s), t) for i, (t, s) in enumerate(zip(comments, scores))]
    return rows, thr


def process_single_file(file_path, model_titles, model_comments, polarity_lex, vader, mode, keyword,
                        auto_thr, auto_percent, threshold, p, neg_window, top_percent):
    comments = read_nonempty_lines(file_path, errors="replace")
    attention = AspectAttention(model_comments, keyword, p)

    def lexicon_scores():
        return [aspect_sentiment_score(t, model_comments, polarity_lex, neg_window=neg_window, attention=attention)
                for t in comments]

    thr_used = threshold
    if mode == "lexicon":
        rows, thr_used = labeled_rows(comments, lexicon_scores(), auto_thr, auto_percent, threshold)
    elif mode == "vader":
        scores = [vader_aspect_score(t, keyword, vader) if keyword else vader.polarity_scores(t)["compound"]
                  for t in comments]
        rows, thr_used = labeled_rows(comments, scores, auto_thr, auto_percent, threshold)
    else:  # bootstrap
        clf = bootstrap_classifier(comments, model_titles, model_comments, polarity_lex,
                                   keyword=keyword, top_percent=top_percent)
        if clf is None:
            rows, thr_used = labeled_rows(comments, lexicon_scores(), auto_thr, auto_percent, threshold)
            mode = "lexicon_fallback"
        else:
            preds, probs = predict_with_classifier(clf, comments, model_titles, model_comments)
            rows = [(i, int(y), float(pmax), t)
                    for i, (t, y, pmax) in enumerate(zip(comments, preds, probs.max(axis=1)))]

    summary_mode = "lexicon" if mode == "lexicon_fallback" else mode
    summary = compute_corpus_summary(rows, mode=summary_mode, thr=thr_used)
    summary.update({
        "file": os.path.basename(file_path),
        "path": file_path,
        "mode": mode,
        "keyword": keyword or "",
        "threshold_used": float(thr_used),
    })
    return rows, summary

def list_files_in_dir(dir_path, pattern="*.txt", recursive=False):
    if recursive:
        glob_pat = os.path.join(dir_path, "**", pattern)
        return [p for p in glob.glob(glob_pat, recursive=True) if os.path.isfile(p)]
    else:
        glob_pat = os.path.join(dir_path, pattern)
        return [p for p in glob.glob(glob_pat) if os.path.isfile(p)]

def write_summaries_csv(summaries, out_path):
    fieldnames = [
        "file", "path", "mode", "keyword",
        "n_total", "n_pos", "n_neg", "n_neu",
        "pos_share", "neg_share", "neu_share",
        "polarity_ratio", "mean_label", "sentiment_index",
        "mean_score", "median_score", "std_score", "mean_abs_score", "p25_score", "p75_score", "strong_fraction",
        "avg_confidence", "median_confidence", "p25_confidence", "p75_confidence",
        "threshold_used"
    ]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for s in summaries:
            row = {k: s.get(k, "") for k in fieldnames}
            w.writerow(row)

def parse_args():
    p = argparse.ArgumentParser(
        prog="calculate_sentiment",
        description="Тональность комментариев по каждой технологии (лексикон w2v, VADER или bootstrap)"
    )
    p.add_argument("-i", "--input", help="Путь к одному файлу (по одному комментарию в строке).")
    p.add_argument("-d", "--dir", help="Папка с файлами для пакетной обработки.")
    p.add_argument("--pattern", default="*.txt", help="Глоб-шаблон для выбора файлов в папке (например, *.txt).")
    p.add_argument("--recursive", action="store_true", help="Рекурсивный проход по подпапкам.")
    # Имена флагов сохранены для совместимости; ожидается модель gensim Word2Vec (.model)
    p.add_argument("--titles-kv", default="w2v_titles.model", help="Модель Word2Vec (заголовки), .model")
    p.add_argument("--comments-kv", default="w2v_titles_comments.model",
                   help="Модель Word2Vec (заголовки+комментарии), .model")
    p.add_argument("--mode", choices=["lexicon", "vader", "bootstrap"], default="lexicon", help="Режим анализа.")
    p.add_argument("--keyword", default=None, help="Аспект/ключевое слово (опц.).")
    p.add_argument("--use-vader", action="store_true", help="Сливать лексикон w2v с VADER.")
    p.add_argument("--p", type=float, default=2.0, help="Степень внимания к ключу.")
    p.add_argument("--neg-window", type=int, default=3, help="Окно для отрицаний.")
    p.add_argument("--threshold", type=float, default=0.12, help="Порог меток {-1,0,1}.")
    p.add_argument("--auto-thr", action="store_true", help="Автокалибровка порога по распределению в файле.")
    p.add_argument("--auto-percent", type=int, default=60, help="Процентиль |score| для автопорога.")
    p.add_argument("--top-percent", type=int, default=20, help="Топ-%% уверенных примеров для bootstrap.")
    p.add_argument("--out-csv", default="corpus_summary.csv", help="Итоговый CSV по всем обработанным файлам.")
    p.add_argument("--save-rows-dir", default=None,
                   help="Папка для пофайловых TSV (idx, label, score/conf, text).")
    return p.parse_args()

def write_rows_tsv(rows, path):
    with open(path, "w", encoding="utf-8") as out:
        out.write("idx\tlabel\tscore_or_confidence\ttext\n")
        for idx, label, value, text in rows:
            out.write(f"{idx}\t{label}\t{value:.4f}\t{text}\n")


@cli_main
def main():
    args = parse_args()
    if args.input:
        files = [args.input]
    elif args.dir:
        files = list_files_in_dir(args.dir, pattern=args.pattern, recursive=args.recursive)
        if not files:
            raise ValueError(f"В папке {args.dir} нет файлов по шаблону {args.pattern}")
    else:
        raise ValueError("Необходимо указать --input или --dir")

    model_titles = Word2Vec.load(args.titles_kv).wv
    model_comments = Word2Vec.load(args.comments_kv).wv

    vader = SentimentIntensityAnalyzer() if args.use_vader or args.mode == "vader" else None
    polarity_lex = expand_lexicon(SEED_POS, SEED_NEG, model_comments, topn=100, sim_thr=0.62)
    if vader is not None:
        polarity_lex = merge_lexicons(polarity_lex, vader.lexicon)

    summaries = []
    for fp in files:
        print(f"Обработка: {fp}", file=sys.stderr)
        rows, summary = process_single_file(
            fp, model_titles, model_comments, polarity_lex, vader, args.mode, args.keyword,
            args.auto_thr, args.auto_percent, args.threshold,
            args.p, args.neg_window, args.top_percent
        )
        summaries.append(summary)
        if args.save_rows_dir:
            os.makedirs(args.save_rows_dir, exist_ok=True)
            write_rows_tsv(rows, os.path.join(args.save_rows_dir, os.path.basename(fp) + ".rows.tsv"))

    write_summaries_csv(summaries, args.out_csv)
    print(f"Готово: сводный CSV → {args.out_csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
