import numpy as np
import pandas as pd
import pytest
from gensim.models import KeyedVectors, Word2Vec

from analytics.embeddings.scripts import build_rel_matrix as brm


def make_kv(vectors):
    kv = KeyedVectors(vector_size=2)
    kv.add_vectors(list(vectors), np.array(list(vectors.values()), dtype=np.float32))
    return kv


KV = make_kv({"python": [1.0, 0.0], "rust": [0.0, 1.0], "stable_diffusion": [1.0, 1.0]})


def test_collect_tokens_normalizes_and_filters():
    names, tokens = brm.collect_tokens(KV, ["Python", "Stable Diffusion", "unknown"])
    assert names == ["Python", "Stable Diffusion"]
    assert tokens == ["python", "stable_diffusion"]


def test_collect_tokens_requires_two():
    with pytest.raises(ValueError):
        brm.collect_tokens(KV, ["python", "unknown"])


def test_group_vectors_from_tokens():
    names, vecs, members = brm.group_vectors_from_tokens(
        KV, ["python", "rust"], {"a": ["python", "rust"], "b": ["rust"], "c": ["missing"]}
    )
    assert names == ["a", "b"]
    np.testing.assert_allclose(vecs, [[0.5, 0.5], [0.0, 1.0]])
    assert members == {"a": ["python", "rust"], "b": ["rust"]}


def test_group_vectors_min_group_size():
    with pytest.raises(ValueError):
        brm.group_vectors_from_tokens(KV, ["python", "rust"], {"a": ["python", "rust"], "b": ["rust"]},
                                      min_group_size=2)


@pytest.fixture
def model_and_techs(tmp_path):
    sentences = [["python", "rust", "cpp", "java"], ["python", "java"], ["rust", "cpp"]] * 30
    model = tmp_path / "w2v.model"
    Word2Vec(sentences, vector_size=8, min_count=1, seed=1, workers=1).save(str(model))
    techs = tmp_path / "techs.txt"
    techs.write_text("python\nrust\ncpp\njava\nhaskell\n\n", encoding="utf-8")
    return model, techs


@pytest.mark.parametrize("distance, diag", [(False, 1.0), (True, 0.0)])
def test_main_word_matrix(run_cli, tmp_path, model_and_techs, distance, diag):
    model, techs = model_and_techs
    out = tmp_path / "matrix.csv"
    args = ["-i", techs, "-m", model, "-o", out] + (["--distance"] if distance else [])
    assert run_cli(brm.main, *args) == 0

    df = pd.read_csv(out, index_col=0)
    assert list(df.index) == list(df.columns) == ["python", "rust", "cpp", "java"]
    np.testing.assert_allclose(np.diag(df), diag, atol=1e-5)
    np.testing.assert_allclose(df.to_numpy(), df.to_numpy().T, atol=1e-6)


def test_main_group_matrix(run_cli, tmp_path, model_and_techs):
    model, techs = model_and_techs
    out = tmp_path / "groups.csv"
    assert run_cli(brm.main, "-i", techs, "-m", model, "-o", out, "--groups") == 0
    df = pd.read_csv(out, index_col=0)
    assert "programming_language" in df.index
    assert df.shape[0] == df.shape[1] >= 2
