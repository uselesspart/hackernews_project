import gzip
import json

import pandas as pd
import pytest
from gensim.models import Word2Vec

from analytics.embeddings.patterns import PATTERNS
from analytics.embeddings.scripts import lemmatize_file, sentences_to_vectors, train_model
from analytics.embeddings.title_embedder import save_token_matrix_jsonl_gz


def _read_jsonl_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_save_token_matrix_jsonl_gz(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("C++ beats C# in 2024\n\nhello world\n", encoding="utf-8")
    out = tmp_path / "nested" / "tokens.jsonl.gz"
    save_token_matrix_jsonl_gz(src, out, lemmatize_en=False)
    assert _read_jsonl_gz(out) == [["cpp", "beats", "csharp", "in", "<NUM>"], ["hello", "world"]]


def test_jsonl_gz_corpus_skips_empty_and_invalid(tmp_path):
    path = tmp_path / "tokens.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write('["a", "b"]\n[]\n{"x": 1}\n["c"]\n')
    corpus = train_model.JsonlGzCorpus(path)
    assert list(corpus) == [["a", "b"], ["c"]]
    assert list(corpus) == [["a", "b"], ["c"]]  # итерируется повторно (нужно Word2Vec)


@pytest.fixture
def tokens_file(tmp_path):
    path = tmp_path / "titles.tokens.jsonl.gz"
    sentences = [["python", "pytest", "code"], ["rust", "cargo.toml", "code"], ["python", "rust"]] * 20
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for s in sentences:
            f.write(json.dumps(s) + "\n")
    return path


def test_train_model_main(run_cli, tmp_path, tokens_file):
    out_dir = tmp_path / "models"
    rc = run_cli(train_model.main, "-p", tokens_file, "-o", out_dir, "--vector-size", 8,
                 "--min-count", 1, "--epochs", 1, "--workers", 1, "--aggregate-synonyms")
    assert rc == 0

    base = out_dir / "w2v_titles_8d"
    model = Word2Vec.load(str(base) + ".model")
    assert {"python", "rust", "code"} <= set(model.wv.index_to_key)
    assert (out_dir / "w2v_titles_8d.txt").exists()
    assert (out_dir / "w2v_titles_8d.csv").exists()

    aggregated = pd.read_csv(out_dir / "w2v_titles_8d.aggregated.csv", index_col=0)
    assert {"python", "rust"} <= set(aggregated.index)
    assert aggregated.shape[1] == 8


def test_aggregate_synonyms_weights_by_count(tokens_file):
    model = Word2Vec(train_model.JsonlGzCorpus(tokens_file), vector_size=4, min_count=1, seed=1, workers=1)
    df = train_model.aggregate_synonyms(model, {"python": PATTERNS["python"], "none": PATTERNS["haskell"]})
    assert list(df.index) == ["python"]  # "python" и "pytest" слились, haskell-токенов нет


def test_sentences_to_vectors_missing_input(run_cli, tmp_path):
    assert run_cli(sentences_to_vectors.main, "-i", tmp_path / "missing.txt", "-o", tmp_path / "o.gz") == 1


@pytest.mark.spacy
def test_sentences_to_vectors_main(run_cli, tmp_path):
    src = tmp_path / "lem.txt"
    src.write_text("python be great\n", encoding="utf-8")
    out = tmp_path / "tokens.jsonl.gz"
    assert run_cli(sentences_to_vectors.main, "-i", src, "-o", out) == 0
    assert _read_jsonl_gz(out) == [["python", "be", "great"]]


@pytest.mark.spacy
def test_lemmatize_file_main(run_cli, tmp_path):
    src = tmp_path / "titles.txt"
    src.write_text("Cats were running\nWhy C++ matters in 2024\n", encoding="utf-8")
    out = tmp_path / "titles_lem.txt"
    run_cli(lemmatize_file.main, "-i", src, "-o", out, "--add-preserve", "running")
    assert out.read_text(encoding="utf-8").splitlines() == [
        "cat be running",
        "why cpp matter in <NUM>",
    ]


def test_lemmatize_file_no_lemmatize(run_cli, tmp_path):
    src = tmp_path / "titles.txt"
    src.write_text("Cats were running!\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    run_cli(lemmatize_file.main, "-i", src, "-o", out, "--no-lemmatize", "--keep-punct", "--num-token", "None")
    assert out.read_text(encoding="utf-8").splitlines() == ["cats were running !"]
