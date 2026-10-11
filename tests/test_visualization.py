import numpy as np
import pandas as pd
import pytest

from analytics.embeddings import projection
from analytics.embeddings.scripts.calculate_sentiment import write_summaries_csv
from utils import words
from visualization import draw_irr_plot, draw_relationship_map, draw_sentiment_plot, draw_wordcloud

PNG_MAGIC = b"\x89PNG"


def assert_png(path):
    assert path.read_bytes()[:4] == PNG_MAGIC


# --- draw_relationship_map --------------------------------------------------

def _sim_matrix(names, seed=0):
    rng = np.random.default_rng(seed)
    vecs = rng.normal(size=(len(names), 4))
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    return pd.DataFrame(vecs @ vecs.T, index=names, columns=names)


def test_detect_matrix_type():
    names = ["a", "b", "c"]
    sim = _sim_matrix(names)
    assert projection.detect_matrix_type(sim) == "similarity"
    assert projection.detect_matrix_type(1 - sim) == "distance"
    features = pd.DataFrame(np.ones((3, 5)), index=names)
    assert projection.detect_matrix_type(features) == "features"


def test_pick_perplexity():
    assert projection.pick_perplexity(3) == 2.0
    assert projection.pick_perplexity(100) == 30.0
    with pytest.raises(ValueError):
        projection.pick_perplexity(2)


@pytest.mark.parametrize("with_labels_file", [False, True])
def test_relationship_map_main(run_cli, tmp_path, with_labels_file):
    names = ["python", "rust", "cpp", "java", "go", "ruby"]
    matrix = tmp_path / "matrix.csv"
    _sim_matrix(names).to_csv(matrix)
    out = tmp_path / "plots" / "map.png"
    args = ["-m", matrix, "-o", out]
    if with_labels_file:
        labels = tmp_path / "labels.txt"
        labels.write_text("python\nrust\ncpp\nunknown\n", encoding="utf-8")
        args += ["-t", labels]
    assert run_cli(draw_relationship_map.main, *args) == 0
    assert_png(out)


def test_relationship_map_too_few_labels(run_cli, tmp_path):
    matrix = tmp_path / "matrix.csv"
    _sim_matrix(["a", "b"]).to_csv(matrix)
    assert run_cli(draw_relationship_map.main, "-m", matrix, "-o", tmp_path / "x.png") == 1


# --- draw_wordcloud ---------------------------------------------------------

def test_build_frequencies_filters_stop_words_and_short_tokens():
    freqs = words.build_frequencies(["the rust compiler is fast", "rust <b>compiler</b> go"])
    assert freqs == {"rust": 2, "compiler": 2, "fast": 1}


def test_build_frequencies_does_not_mutate_global_stop_words():
    before = set(words.EN_STOP)
    freqs = words.build_frequencies(["rust compiler"], extra_stop={"rust"})
    assert freqs == {"compiler": 1}
    assert before == words.EN_STOP


def test_wordcloud_main(run_cli, tmp_path):
    src = tmp_path / "rust_lem.txt"
    src.write_text("rust compiler borrow checker\nrust naïve café ownership\n", encoding="utf-8")
    out = tmp_path / "wc.png"
    assert run_cli(draw_wordcloud.main, "-i", src, "-o", out, "--extra", "Rust") == 0
    assert_png(out)


# --- draw_irr_plot ----------------------------------------------------------

def test_irr_plot_main(run_cli, tmp_path):
    coefs = pd.DataFrame({
        "feature": ["const", "has_python", "has_rust", "has_pair_python__rust", "sim_mean"],
        "IRR": [10.0, 1.5, 0.7, 2.0, 1.1],
        "IRR_low": [9.0, 1.2, 0.5, 1.0, 0.9],
        "IRR_high": [11.0, 1.8, 0.9, 3.0, 1.3],
    })
    src = tmp_path / "coefs.csv"
    coefs.to_csv(src, index=False)
    out = tmp_path / "plots" / "irr.png"
    assert run_cli(draw_irr_plot.main, "-i", src, "-o", out) == 0
    assert_png(out)


# --- draw_sentiment_plot ----------------------------------------------------

def test_sentiment_plot_from_calculate_sentiment_output(tmp_path):
    summaries = [
        {"file": "rust_5.txt", "mode": "lexicon", "keyword": "", "sentiment_index": 0.2},
        {"file": "go_6.txt", "mode": "lexicon", "keyword": "speed", "sentiment_index": -0.1},
    ]
    src = tmp_path / "summary.csv"
    write_summaries_csv(summaries, src)
    out = tmp_path / "sentiment.png"
    assert draw_sentiment_plot.plot_summary_csv(src, out) == {"bar": out}
    assert_png(out)


def test_sentiment_plot_without_keyword_column(tmp_path):
    src = tmp_path / "summary.csv"
    pd.DataFrame({"file": ["a.txt", "b.txt"], "mode": ["vader", "vader"],
                  "sentiment_index": [0.1, 0.3]}).to_csv(src, index=False)
    out = tmp_path / "sentiment.png"
    draw_sentiment_plot.plot_summary_csv(src, out, sort_by="missing_column")
    assert_png(out)


def test_sentiment_plot_empty_csv(tmp_path):
    src = tmp_path / "empty.csv"
    src.write_text("file,mode,keyword,sentiment_index\n", encoding="utf-8")
    with pytest.raises(ValueError):
        draw_sentiment_plot.plot_summary_csv(src, tmp_path / "x.png")
