import sys
import re
import os
import glob
import csv
import numpy as np
import argparse
from gensim.models import Word2Vec
from collections import defaultdict
from sklearn.linear_model import LogisticRegression
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def tokenize(text):
    return re.findall(r"[a-z]+", text.lower())

def prep(text):
    return tokenize(text)

NEGATIONS = {"not", "no", "never", "without", "none", "neither"}
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

def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def phrase_vector(text, model):
    toks = prep(text)
    vecs = [model[w] for w in toks if w in model]
    if not vecs:
        return None
    return np.mean(vecs, axis=0)

def aspect_sentiment_score(text, model_comments, polarity_lex, keyword=None, p=2.0, neg_window=3):
    toks = prep(text)
    att = {}
    if keyword:
        kvec = phrase_vector(keyword, model_comments)
        if kvec is not None:
            for w in toks:
                if w in model_comments:
                    s = cos(model_comments[w], kvec)
                    att[w] = max(s, 0.0) ** p
        else:
            att = {w: 1.0 for w in toks}
    else:
        att = {w: 1.0 for w in toks}

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
        if w in NEGATIONS:
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
            w_att = att.get(w, 1.0)
            contrib = pol * sign * modifier * w_att
            score += contrib
            weight_sum += abs(w_att)

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
    toks = prep(text)
    v1 = doc_vec(toks, model_titles)
    v2 = doc_vec(toks, model_comments)
    return np.concatenate([v1, v2])

def bootstrap_classifier(texts, model_titles, model_comments, polarity_lex, keyword=None, top_percent=20):
    scores = np.array([aspect_sentiment_score(t, model_comments, polarity_lex, keyword=keyword) for t in texts])
    labels = np.array([label_from_score(s) for s in scores])

    abs_scores = np.abs(scores)
    cut = np.percentile(abs_scores, 100 - top_percent)
    idx = abs_scores >= cut
    X = np.vstack([combined_doc_vec(texts[i], model_titles, model_comments) for i in np.where(idx)[0]])
    y = labels[idx]

    if len(y) < 50:
        print("Too few confident pseudo-labels; adjust seeds or top_percent.")
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

def read_comments_from_file(path):
    comments = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                comments.append(line)
    return comments

def process_single_file(file_path, model_titles, model_comments, polarity_lex, vader, mode, keyword, 
                        auto_thr, auto_percent, threshold, p, neg_window, top_percent):
    comments = read_comments_from_file(file_path)
    rows = []
    thr_used = threshold

    if mode == "lexicon":
        scores = [aspect_sentiment_score(t, model_comments, polarity_lex, keyword=keyword, p=p, neg_window=neg_window) for t in comments]
        if auto_thr:
            abs_scores = np.abs(scores)
            thr_used = max(np.percentile(abs_scores, auto_percent), 0.08)
        labels = [label_from_score(s, thr=thr_used) for s in scores]
        for i, (t, s, y) in enumerate(zip(comments, scores, labels)):
            rows.append((i, y, float(s), t))

    elif mode == "vader":
        scores = []
        for t in comments:
            if keyword:
                s = vader_aspect_score(t, keyword, vader)
            else:
                s = vader.polarity_scores(t)["compound"] if vader else 0.0
            scores.append(s)
        thr_used = threshold if not auto_thr else max(np.percentile(np.abs(scores), auto_percent), 0.08)
        labels = [label_from_score(s, thr=thr_used) for s in scores]
        for i, (t, s, y) in enumerate(zip(comments, scores, labels)):
            rows.append((i, y, float(s), t))

    elif mode == "bootstrap":
        clf = bootstrap_classifier(comments, model_titles, model_comments, polarity_lex, keyword=keyword, top_percent=top_percent)
        if clf is None:
            scores = [aspect_sentiment_score(t, model_comments, polarity_lex, keyword=keyword, p=p, neg_window=neg_window) for t in comments]
            thr_used = threshold if not auto_thr else max(np.percentile(np.abs(scores), auto_percent), 0.08)
            labels = [label_from_score(s, thr=thr_used) for s in scores]
            for i, (t, s, y) in enumerate(zip(comments, scores, labels)):
                rows.append((i, y, float(s), t))
            mode = "lexicon_fallback"
        else:
            preds, probs = predict_with_classifier(clf, comments, model_titles, model_comments)
            maxp = probs.max(axis=1)
            for i, (t, y, pmax) in enumerate(zip(comments, preds, maxp)):
                rows.append((i, int(y), float(pmax), t))

    summary = compute_corpus_summary(rows, mode="vader" if mode == "vader" else ("lexicon" if mode.startswith("lexicon") else "bootstrap"), thr=thr_used)
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
        prog="export_titles",
        description="Отрисовка карты отношений между словами"
    )
    p.add_argument("-i", "--input", type=str, help="Путь к одному файлу (по одному комментарию в строке).")
    p.add_argument("-d", "--dir", type=str, help="Папка с файлами для пакетной обработки.")
    p.add_argument("--pattern", type=str, default="*.txt", help="Глоб‑шаблон для выбора файлов в папке (например, *.txt).")
    p.add_argument("--recursive", action="store_true", help="Рекурсивный проход по подпапкам.")
    p.add_argument("--titles-kv", type=str, default="w2v_titles.kv", help="Путь к модели w2v (заголовки).")
    p.add_argument("--comments-kv", type=str, default="w2v_titles_comments.kv", help="Путь к модели w2v (заголовки+комменты).")
    p.add_argument("--mode", type=str, choices=["lexicon", "vader", "bootstrap"], default="lexicon", help="Режим анализа.")
    p.add_argument("--keyword", type=str, default=None, help="Аспект/ключевое слово (опц.).")
    p.add_argument("--use-vader", action="store_true", help="Сливать лексикон w2v с VADER.")
    p.add_argument("--p", type=float, default=2.0, help="Степень внимания к ключу.")
    p.add_argument("--neg-window", type=int, default=3, help="Окно для отрицаний.")
    p.add_argument("--threshold", type=float, default=0.12, help="Порог меток {-1,0,1}.")
    p.add_argument("--auto-thr", action="store_true", help="Автокалибровка порога по распределению в файле.")
    p.add_argument("--auto-percent", type=int, default=60, help="Процентиль |score| для автопорога.")
    p.add_argument("--top-percent", type=int, default=20, help="Топ-% уверенных примеров для bootstrap.")
    p.add_argument("--out-csv", type=str, default="corpus_summary.csv", help="Итоговый CSV по всем обработанным файлам.")
    p.add_argument("--save-rows-dir", type=str, default=None, help="Папка для сохранения пер-файловых TSV (idx, label, score/conf, text).")
    return p.parse_args()

def main():
    try:
        args = parse_args()

        model = Word2Vec.load(args.titles_kv)
        model_titles = model.wv
        model = Word2Vec.load(args.comments_kv)
        model_comments = model.wv

        vader = None
        vader_lex = {}
        try:
            if args.use_vader or args.mode == "vader":
                vader = SentimentIntensityAnalyzer()
                vader_lex = vader.lexicon
        except Exception:
            pass

        seed_pos = {
            "good", "great", "excellent", "amazing", "awesome", "fantastic", "love", "like",
            "happy", "satisfied", "recommend", "wonderful", "brilliant", "positive", "cool",
            "perfect", "nice", "solid", "helpful", "reliable"
        }
        seed_neg = {
            "bad", "terrible", "awful", "horrible", "hate", "disgusting", "trash", "worst",
            "sad", "angry", "disappointed", "scam", "fake", "useless", "broken", "poor",
            "buggy", "annoying", "ridiculous", "crap"
        }
        w2v_pol = expand_lexicon(seed_pos, seed_neg, model_comments, topn=100, sim_thr=0.62)
        polarity_lex = merge_lexicons(w2v_pol, vader_lex) if vader_lex else w2v_pol

        if args.input:
            files = [args.input]
        elif args.dir:
            files = list_files_in_dir(args.dir, pattern=args.pattern, recursive=args.recursive)
            if not files:
                print("В папке нет файлов по шаблону.", file=sys.stderr)
                sys.exit(1)
        else:
            print("Необходимо указать --input или --dir", file=sys.stderr)
            sys.exit(1)

        summaries = []
        for fp in files:
            print(f"Processing: {fp}", file=sys.stderr)
            rows, summary = process_single_file(
                fp, model_titles, model_comments, polarity_lex, vader, args.mode, args.keyword,
                args.auto_thr, args.auto_percent, args.threshold,
                args.p, args.neg_window, args.top_percent
            )
            summaries.append(summary)

            if args.save_rows_dir:
                os.makedirs(args.save_rows_dir, exist_ok=True)
                out_tsv = os.path.join(args.save_rows_dir, os.path.basename(fp) + ".rows.tsv")
                with open(out_tsv, "w", encoding="utf-8") as out:
                    out.write("idx\tlabel\tscore_or_confidence\ttext\n")
                    for r in rows:
                        out.write(f"{r[0]}\t{r[1]}\t{r[2]:.4f}\t{r[3]}\n")

        write_summaries_csv(summaries, args.out_csv)
        print(f"Готово: сводный CSV → {args.out_csv}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
