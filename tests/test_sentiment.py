import csv

import numpy as np
import pytest
from gensim.models import KeyedVectors, Word2Vec

from analytics.embeddings.scripts import calculate_sentiment as cs


def make_kv(vectors: dict[str, list[float]]) -> KeyedVectors:
    kv = KeyedVectors(vector_size=len(next(iter(vectors.values()))))
    kv.add_vectors(list(vectors), np.array(list(vectors.values()), dtype=np.float32))
    return kv


LEX = {"good": 0.7, "like": 0.8, "bad": -0.7, "slow": -0.5, "fast": 0.5}
NO_MODEL = make_kv({"unused": [1.0, 0.0]})


def score(text, **kwargs):
    return cs.aspect_sentiment_score(text, NO_MODEL, LEX, **kwargs)


@pytest.mark.parametrize("text, expected", [
    ("I don't like it", ["i", "don't", "like", "it"]),
    ("Rust's borrow checker", ["rust's", "borrow", "checker"]),
    ("C++ 2024!", ["c"]),
])
def test_tokenize(text, expected):
    assert cs.tokenize(text) == expected


@pytest.mark.parametrize("word, expected", [
    ("not", True), ("never", True), ("don't", True), ("isn't", True), ("dont", True),
    ("do", False), ("good", False),
])
def test_is_negation(word, expected):
    assert cs.is_negation(word) is expected


def test_score_without_polar_words_is_zero():
    assert score("the weather today") == 0.0


def test_score_sign():
    assert score("I like it") > 0
    assert score("this is bad") < 0


@pytest.mark.parametrize("text", ["I don't like it", "i do not like it", "never good"])
def test_negation_flips_sign(text):
    assert score(text) < 0


def test_negation_window_expires():
    # окно 1: отрицается только первое оценочное слово после "not"
    assert score("not good good", neg_window=1) == pytest.approx(0.0, abs=1e-6)


def test_intensifier_applies_only_to_next_polar_word():
    assert score("very good but bad") == pytest.approx((0.7 * 1.5 - 0.7) / 2)
    assert score("very good but very bad") == pytest.approx(0.0, abs=1e-6)


def test_diminisher_a_little():
    assert score("a little good") == pytest.approx(0.7 * 0.7)


def test_keyword_attention_weights_related_words():
    kv = make_kv({"rust": [1.0, 0.0], "fast": [1.0, 0.0], "slow": [0.0, 1.0]})
    # "slow" ортогонален ключу -> внимание 0, учитывается только "fast"
    s = cs.aspect_sentiment_score("fast slow", kv, LEX, keyword="rust")
    assert s == pytest.approx(0.5)


@pytest.mark.parametrize("s, thr, expected", [(0.5, 0.12, 1), (-0.5, 0.12, -1), (0.1, 0.12, 0), (0.1, 0.05, 1)])
def test_label_from_score(s, thr, expected):
    assert cs.label_from_score(s, thr) == expected


def test_expand_lexicon():
    kv = make_kv({
        "good": [1.0, 0.0], "great": [0.99, 0.1],
        "bad": [-1.0, 0.0], "awful": [-0.99, -0.1],
        "table": [0.0, 1.0],
    })
    pol = cs.expand_lexicon({"good", "missing"}, {"bad"}, kv, topn=5, sim_thr=0.6)
    assert pol["good"] > 0 and pol["great"] > 0
    assert pol["bad"] < 0 and pol["awful"] < 0
    assert "table" not in pol and "missing" not in pol


def test_merge_lexicons():
    merged = cs.merge_lexicons({"good": 0.5}, {"good": 4.0, "awful": -2.0}, alpha=0.5)
    assert merged["good"] == pytest.approx(np.tanh(0.5 * 0.5 + 0.5 * 1.0))
    assert merged["awful"] == pytest.approx(-0.5)


def test_vader_aspect_score():
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader = SentimentIntensityAnalyzer()
    assert cs.vader_aspect_score("rust is great", "rust", None) is None
    assert cs.vader_aspect_score("rust is great", "rust", vader) > 0
    # ключевого слова нет — оценивается весь текст
    assert cs.vader_aspect_score("this is terrible", "rust", vader) < 0


def test_compute_corpus_summary_lexicon():
    rows = [(0, 1, 0.5, "a"), (1, -1, -0.3, "b"), (2, 0, 0.0, "c"), (3, 1, 0.2, "d")]
    summary = cs.compute_corpus_summary(rows, mode="lexicon", thr=0.12)
    assert (summary["n_total"], summary["n_pos"], summary["n_neg"], summary["n_neu"]) == (4, 2, 1, 1)
    assert summary["polarity_ratio"] == pytest.approx(1 / 3, abs=1e-6)
    assert summary["mean_score"] == pytest.approx(0.1)
    assert summary["sentiment_index"] == summary["mean_score"]
    assert summary["strong_fraction"] == pytest.approx(0.75)


def test_compute_corpus_summary_bootstrap():
    rows = [(0, 1, 0.9, "a"), (1, -1, 0.7, "b")]
    summary = cs.compute_corpus_summary(rows, mode="bootstrap")
    assert summary["avg_confidence"] == pytest.approx(0.8)
    assert summary["sentiment_index"] == summary["mean_label"] == 0.0


def test_process_single_file_lexicon(tmp_path):
    path = tmp_path / "rust.txt"
    path.write_text("I like it\n\nthis is bad\nnothing here\n", encoding="utf-8")
    rows, summary = cs.process_single_file(
        str(path), NO_MODEL, NO_MODEL, LEX, None, "lexicon", None,
        auto_thr=False, auto_percent=60, threshold=0.12, p=2.0, neg_window=3, top_percent=20,
    )
    assert [r[1] for r in rows] == [1, -1, 0]
    assert summary["file"] == "rust.txt" and summary["n_total"] == 3


def _process(path, mode, kv=NO_MODEL, lex=LEX, vader=None, **overrides):
    params = dict(keyword=None, auto_thr=False, auto_percent=60, threshold=0.12, p=2.0,
                  neg_window=3, top_percent=20)
    params.update(overrides)
    return cs.process_single_file(str(path), kv, kv, lex, vader, mode, **params)


def test_process_single_file_vader(tmp_path):
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    path = tmp_path / "go.txt"
    path.write_text("I love this language\nThis is terrible and broken\n", encoding="utf-8")
    rows, summary = _process(path, "vader", vader=SentimentIntensityAnalyzer())
    assert [r[1] for r in rows] == [1, -1]
    assert summary["mode"] == "vader" and "mean_score" in summary


def test_process_single_file_auto_threshold(tmp_path):
    path = tmp_path / "rust.txt"
    path.write_text("good\nvery good\nbad\n", encoding="utf-8")
    _, summary = _process(path, "lexicon", auto_thr=True, auto_percent=50)
    assert summary["threshold_used"] >= 0.08


def test_process_single_file_bootstrap(tmp_path):
    kv = make_kv({"good": [1.0, 0.0], "nice": [0.9, 0.1], "bad": [-1.0, 0.0],
                  "broken": [-0.9, -0.1], "code": [0.0, 1.0]})
    lex = {"good": 0.8, "nice": 0.6, "bad": -0.8, "broken": -0.6}
    path = tmp_path / "rust.txt"
    path.write_text("good nice code\nbad broken code\n" * 150, encoding="utf-8")

    rows, summary = _process(path, "bootstrap", kv=kv, lex=lex, top_percent=50)
    assert summary["mode"] == "bootstrap"
    assert [r[1] for r in rows[:2]] == [1, -1]
    assert all(0.5 <= r[2] <= 1.0 for r in rows)  # уверенность классификатора
    assert "avg_confidence" in summary


def test_process_single_file_bootstrap_falls_back_to_lexicon(tmp_path):
    path = tmp_path / "rust.txt"
    path.write_text("good code\nbad code\n", encoding="utf-8")
    rows, summary = _process(path, "bootstrap")
    assert summary["mode"] == "lexicon_fallback"
    assert [r[1] for r in rows] == [1, -1]


def test_list_files_in_dir(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.csv").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("x")
    names = lambda files: sorted(p.replace("\\", "/").split("/")[-1] for p in files)
    assert names(cs.list_files_in_dir(str(tmp_path))) == ["a.txt"]
    assert names(cs.list_files_in_dir(str(tmp_path), recursive=True)) == ["a.txt", "c.txt"]


def test_main_end_to_end(run_cli, tmp_path):
    sentences = [["good", "great", "nice", "code"], ["bad", "awful", "broken", "code"]] * 50
    model_path = tmp_path / "w2v.model"
    Word2Vec(sentences, vector_size=8, min_count=1, seed=1, workers=1).save(str(model_path))

    comments_dir = tmp_path / "techs"
    comments_dir.mkdir()
    (comments_dir / "rust_1.txt").write_text("good code\nbad code\n", encoding="utf-8")
    (comments_dir / "go_2.txt").write_text("great code\n", encoding="utf-8")
    out_csv = tmp_path / "summary.csv"

    rc = run_cli(cs.main, "-d", comments_dir, "--titles-kv", model_path, "--comments-kv", model_path,
                 "--out-csv", out_csv, "--use-vader", "--save-rows-dir", tmp_path / "rows")
    assert rc == 0
    with out_csv.open(encoding="utf-8") as f:
        rows = {r["file"]: r for r in csv.DictReader(f)}
    assert set(rows) == {"rust_1.txt", "go_2.txt"}
    assert float(rows["go_2.txt"]["sentiment_index"]) > 0
    assert (tmp_path / "rows" / "rust_1.txt.rows.tsv").exists()
