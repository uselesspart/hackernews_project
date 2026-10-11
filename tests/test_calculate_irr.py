from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from gensim.models import KeyedVectors, Word2Vec

from analytics.embeddings.scripts import calculate_irr as irr


def make_kv(vectors):
    kv = KeyedVectors(vector_size=2)
    kv.add_vectors(list(vectors), np.array(list(vectors.values()), dtype=np.float32))
    return kv


@pytest.mark.parametrize("title, expected", [
    ("Rust and C++ and Python and Go 1.22", ["rust", "cpp", "python"]),  # порядок появления, не более 3
    ("Python, python, PYTHON", ["python"]),
    ("Nothing here", []),
    (None, []),
])
def test_extract_tech_regex(title, expected):
    assert irr.extract_tech_regex(title) == expected


def test_pair_similarity_stats():
    vec_map = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0]), "c": np.array([1.0, 1.0]),
               "bad": np.array([np.nan, 1.0])}
    sim = irr.PairSimilarity(vec_map)
    assert sim.stats(["a"]) == (0.0, 0.0, 0.0)
    assert sim.stats(["a", "missing", "bad"]) == (0.0, 0.0, 0.0)  # нет вектора / NaN-вектор
    mn, mean, mx = sim.stats(["a", "b", "c"])
    assert (mn, mx) == pytest.approx((0.0, np.sqrt(0.5)))
    assert mean == pytest.approx(2 * np.sqrt(0.5) / 3)


def test_token_vec_map():
    w2v = SimpleNamespace(wv=make_kv({"x": [1.0, 0.0], "y": [1.0, 0.0]}))
    vec_map = irr.token_vec_map(w2v, ["x", "y", "unknown"])
    assert set(vec_map) == {"x", "y"}
    assert irr.PairSimilarity(vec_map).stats(["x", "y"]) == pytest.approx((1.0, 1.0, 1.0))


def test_build_group_maps():
    w2v = SimpleNamespace(wv=make_kv({"python": [1.0, 0.0], "rust": [0.0, 1.0]}))
    group_to_tokens, token_to_groups, group_vecs = irr.build_group_maps(
        w2v, {"lang": ["python", "rust", "missing"], "empty": ["missing"]}
    )
    assert group_to_tokens == {"lang": ["python", "rust"]}
    assert token_to_groups == {"python": ["lang"], "rust": ["lang"]}
    np.testing.assert_allclose(group_vecs["lang"], [0.5, 0.5])


def _synthetic_counts(n, effects, alpha=0.5, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({f"has_{t}": rng.integers(0, 2, n) for t in effects})
    log_mu = np.log(10) + sum(np.log(e) * X[f"has_{t}"] for t, e in effects.items())
    mu = np.exp(log_mu)
    y = rng.poisson(rng.gamma(1 / alpha, mu * alpha)).astype(float)
    return X.astype(float), y


@pytest.mark.parametrize("family", ["negbin", "poisson"])
def test_fit_count_model_recovers_irr(family):
    effects = {"rust": 2.0, "cpp": 0.5}
    X, y = _synthetic_counts(8000, effects)
    result, alpha = irr.fit_count_model(X, y, family)

    ci = result.conf_int()
    for tech, true_irr in effects.items():
        col = f"has_{tech}"
        assert np.exp(result.params[col]) == pytest.approx(true_irr, rel=0.1)
        assert np.exp(ci.loc[col, 0]) <= true_irr <= np.exp(ci.loc[col, 1])
    if family == "negbin":
        assert alpha == pytest.approx(0.5, rel=0.25)
    else:
        assert alpha is None


def test_linearly_dependent_columns():
    X = pd.DataFrame({"const": 1.0, "a": [0, 1, 0, 1.0], "b": [1, 0, 1, 0.0], "c": [1, 2, 3, 4.0]})
    # b = const - a
    assert irr.linearly_dependent_columns(X) == ["b"]


@pytest.mark.parametrize("family", ["negbin", "poisson"])
def test_fit_count_model_drops_dependent_columns(capsys, family):
    X, y = _synthetic_counts(2000, {"rust": 2.0})
    X["copy"] = X["has_rust"]
    result, _ = irr.fit_count_model(X, y, family)
    assert "copy" in capsys.readouterr().out
    assert list(result.params.index) == ["const", "has_rust"]
    assert np.isfinite(result.bse).all()


# --- main ------------------------------------------------------------------

TITLES = ["Python and Rust", "Rust and C++", "Python tips", "Rust internals", "Why C++ matters", "Random news"]


@pytest.fixture
def w2v_path(tmp_path):
    sentences = [["python", "rust", "cpp", "code"], ["python", "data"], ["rust", "cpp", "systems"]] * 30
    path = tmp_path / "w2v.model"
    Word2Vec(sentences, vector_size=8, min_count=1, seed=1, workers=1).save(str(path))
    return path


def _meta(n, seed=0, nan_every=None):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "id": range(n),
        "title": [TITLES[i % len(TITLES)] for i in range(n)],
        "descendants": rng.poisson(10, n).astype(float),
    })
    if nan_every:
        df.loc[df.index % nan_every == 0, "descendants"] = np.nan
    return df


def _run(run_cli, tmp_path, df, name, *extra):
    meta = tmp_path / f"{name}.csv"
    out = tmp_path / f"{name}_coefs.csv"
    df.to_csv(meta, index=False)
    assert run_cli(irr.main, "-i", meta, "-m", tmp_path / "w2v.model", "-o", out, *extra) == 0
    return pd.read_csv(out).set_index("feature")


def test_main_output_format(run_cli, tmp_path, w2v_path):
    coefs = _run(run_cli, tmp_path, _meta(600), "basic")
    assert list(coefs.columns) == ["coef", "se", "pval", "conf_low", "conf_high", "IRR", "IRR_low", "IRR_high"]
    # sim_* и парные признаки на 6 типах заголовков частично линейно зависимы и могут быть исключены
    assert {"const", "has_python", "has_rust", "has_cpp"} <= set(coefs.index)
    assert np.isfinite(coefs.to_numpy()).all()
    np.testing.assert_allclose(coefs["IRR"], np.exp(coefs["coef"]))
    assert (coefs["IRR_low"] <= coefs["IRR"]).all() and (coefs["IRR"] <= coefs["IRR_high"]).all()


def test_main_filtered_rows_do_not_shift_features(run_cli, tmp_path, w2v_path):
    # Регрессия: после фильтрации NaN признаки sim_* сопоставлялись не тем строкам.
    # Результат с NaN-строками должен совпадать с результатом на заранее очищенных данных.
    df = _meta(900, nan_every=4)
    with_nan = _run(run_cli, tmp_path, df, "with_nan")
    cleaned = _run(run_cli, tmp_path, df.dropna().reset_index(drop=True), "cleaned")
    pd.testing.assert_frame_equal(with_nan, cleaned)


def test_main_groups_mode(run_cli, tmp_path, w2v_path):
    coefs = _run(run_cli, tmp_path, _meta(600), "groups", "--groups")
    assert any(f.startswith("has_") for f in coefs.index)
    assert "has_python" not in coefs.index  # технологии заменены группами


def test_main_fails_without_techs(run_cli, tmp_path, w2v_path):
    df = pd.DataFrame({"title": ["Random news"] * 10, "descendants": [1] * 10})
    meta = tmp_path / "meta.csv"
    df.to_csv(meta, index=False)
    assert run_cli(irr.main, "-i", meta, "-m", w2v_path, "-o", tmp_path / "out.csv") == 1


# --- мультиколлинеарность, контроли, все технологии ----------------------------

def test_variance_inflation_and_high_vif_columns():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 2, 2000).astype(float)
    noise = (rng.random(2000) < 0.01).astype(float)
    X = pd.DataFrame({
        "has_rust": a,
        "has_pair_rust__go": np.abs(a - noise),  # почти копия has_rust
        "has_python": rng.integers(0, 2, 2000).astype(float),
    })
    vif = irr.variance_inflation(X)
    assert vif["has_rust"] > 10 and vif["has_python"] < 2
    # Из пары почти одинаковых признаков убирается парный, а не технология
    assert irr.high_vif_columns(X, 10) == ["has_pair_rust__go"]
    assert irr.high_vif_columns(X[["has_rust", "has_python"]], 10) == []


def test_fit_count_model_drops_collinear_with_max_vif(capsys):
    X, y = _synthetic_counts(3000, {"rust": 2.0})
    flip = np.random.default_rng(1).random(len(X)) < 0.005
    X["has_pair_rust__go"] = np.where(flip, 1 - X["has_rust"], X["has_rust"])
    result, _ = irr.fit_count_model(X, y, "negbin", max_vif=10)
    assert "has_pair_rust__go" in capsys.readouterr().out
    assert np.exp(result.params["has_rust"]) == pytest.approx(2.0, rel=0.15)
    assert np.isfinite(result.bse).all()


def test_control_features():
    df = pd.DataFrame({"title": ["Show HN: My Rust tool", "Ask HN: Python or Go?", "Rust 2.0", None],
                       "url": ["https://x.dev", None, "https://y.dev", ""]})
    feats = irr.control_features(df)
    assert list(feats["title_words"]) == [5, 5, 2, 0]
    assert list(feats["show_hn"]) == [1, 0, 0, 0]
    assert list(feats["ask_hn"]) == [0, 1, 0, 0]
    assert list(feats["has_url"]) == [1, 0, 1, 0]
    assert "has_url" not in irr.control_features(df[["title"]])


def _format_df(n=3000, seed=0):
    # Rust пишут в Ask HN, а Ask HN обсуждают втрое активнее: без контроля IRR Rust завышен
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        tech = ["Rust", "Python", "News"][i % 3]
        ask = rng.random() < (0.6 if tech == "Rust" else 0.1)
        title = f"{'Ask HN: ' if ask else ''}{tech} {'question' if ask else 'release'}"
        mu = 10 * (3 if ask else 1)
        rows.append({"title": title, "descendants": rng.poisson(rng.gamma(2, mu / 2)),
                     "url": None if ask else "https://example.com"})
    return pd.DataFrame(rows)


def test_compute_irr_controls_separate_format_from_topic():
    w2v = SimpleNamespace(wv=make_kv({"rust": [1.0, 0.0], "python": [0.0, 1.0]}))
    df = _format_df()
    with_controls = irr.compute_irr(df, w2v).set_index("feature")
    without = irr.compute_irr(df, w2v, controls=False).set_index("feature")
    assert without.loc["has_rust", "IRR"] > 1.5
    assert with_controls.loc["has_rust", "IRR"] == pytest.approx(1.0, abs=0.15)
    # В синтетике Ask HN, отсутствие ссылки и длина заголовка совпадают — остаётся один из контролей
    assert {"title_words", "ask_hn", "has_url"} & set(with_controls.index)


def test_compute_irr_top_n_and_silent_features(capsys):
    w2v = SimpleNamespace(wv=make_kv({"rust": [1.0, 0.0], "python": [0.0, 1.0], "ruby": [1.0, 1.0]}))
    df = pd.DataFrame({
        "title": ["Rust news"] * 20 + ["Python news"] * 20 + ["Ruby news"] * 6 + ["Other"] * 20,
        "descendants": [5.0] * 20 + [3.0] * 20 + [0.0] * 6 + [2.0, 4.0] * 10,
    })
    # Без контролей: в игрушечных заголовках длина отделяет статьи о технологиях от прочих
    top1 = irr.compute_irr(df, w2v, top_n=1, controls=False)
    assert [f for f in top1["feature"] if f.startswith("has_")] == ["has_rust"]

    everything = irr.compute_irr(df, w2v, top_n=None, controls=False)
    # У Ruby ни одного комментария: оценка ушла бы в минус бесконечность — признак исключён
    assert "has_ruby" in capsys.readouterr().out
    assert set(everything["feature"]) >= {"has_rust", "has_python"} and "has_ruby" not in set(everything["feature"])
    assert np.isfinite(everything[["IRR", "IRR_low", "IRR_high"]].to_numpy()).all()


def test_main_cli_options(run_cli, tmp_path, w2v_path):
    df = _meta(600)
    df["url"] = "https://example.com"
    coefs = _run(run_cli, tmp_path, df, "opts", "--top-n", "0", "--max-vif", "0", "--no-controls")
    assert "title_words" not in coefs.index and {"has_python", "has_rust", "has_cpp"} <= set(coefs.index)
