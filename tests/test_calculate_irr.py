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


def test_normalize_categories_dict_dedups_and_normalizes():
    raw = {"lang": ["Python", "python", " Stable Diffusion "], 1: ["Go"]}
    assert irr.normalize_categories_dict(raw) == {"lang": ["python", "stable_diffusion"], "1": ["go"]}


@pytest.mark.parametrize("title, expected", [
    ("Rust and C++ and Python and Go 1.22", ["rust", "cpp", "python"]),  # порядок появления, не более 3
    ("Python, python, PYTHON", ["python"]),
    ("Nothing here", []),
    (None, []),
])
def test_extract_tech_regex(title, expected):
    assert irr.extract_tech_regex(title) == expected


def test_cos():
    assert irr.cos(np.array([1.0, 0.0]), np.array([0.0, 0.0])) == 0.0
    assert irr.cos(np.array([1.0, 1.0]), np.array([2.0, 2.0])) == pytest.approx(1.0)


def test_title_stats_vecmap():
    vec_map = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0]), "c": np.array([1.0, 1.0])}
    assert irr.title_stats_vecmap(["a"], vec_map) == (0.0, 0.0, 0.0)
    assert irr.title_stats_vecmap(["a", "missing"], vec_map) == (0.0, 0.0, 0.0)
    mn, mean, mx = irr.title_stats_vecmap(["a", "b", "c"], vec_map)
    assert (mn, mx) == pytest.approx((0.0, np.sqrt(0.5)))
    assert mean == pytest.approx(2 * np.sqrt(0.5) / 3)


def test_title_stats_tokens():
    w2v = SimpleNamespace(wv=make_kv({"x": [1.0, 0.0], "y": [1.0, 0.0]}))
    assert irr.title_stats_tokens(["x", "y"], w2v) == pytest.approx((1.0, 1.0, 1.0))
    assert irr.title_stats_tokens(["x", "unknown"], w2v) == (0.0, 0.0, 0.0)


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
