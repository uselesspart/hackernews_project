import csv

import numpy as np
import pytest
from gensim.models import Word2Vec
from sqlalchemy import create_engine

from analytics.embeddings.scripts import evaluate_sentiment as ev
from analytics.embeddings.scripts import tune_model
from db import session_scope
from db.scripts import export_sentiment_sample as ess
from hackernews_handler import HNHandler
from tests.conftest import write_jsonl


@pytest.fixture
def sample_db(db_url, tmp_path):
    from analytics.embeddings.scripts.classify_tech import classify_stories
    items = [{"id": 1, "type": "story", "title": "Rust 2.0 released", "descendants": 30, "score": 5,
              "time": 1700000000},
             {"id": 2, "type": "story", "title": "Python tips", "descendants": 5, "score": 5, "time": 1700000100}]
    texts = [f"Rust is great, version {i}." if i % 3 == 0 else f"Nice weather number {i}." for i in range(30)]
    items += [{"id": 100 + i, "type": "comment", "parent": 1, "text": t, "time": 1700000001 + i}
              for i, t in enumerate(texts)]
    items += [{"id": 200 + i, "type": "comment", "parent": 2, "text": f"Python works {i}.", "time": 1700000200 + i}
              for i in range(5)]
    engine = create_engine(db_url)
    HNHandler(engine).ingest_from_path(write_jsonl(tmp_path / "items.jsonl", items))
    engine.dispose()
    with session_scope(db_url) as session:
        classify_stories(session)
    return db_url


def test_sample_comments_balances_mentions(sample_db):
    with session_scope(sample_db) as session:
        assert ess.top_techs(session, 2) == ["python", "rust"]
        rows = ess.sample_comments(session, ["rust", "python"], per_tech=8, seed=1)
        again = ess.sample_comments(session, ["rust", "python"], per_tech=8, seed=1)
    assert rows == again
    rust = [r for r in rows if r["tech"] == "rust"]
    assert len(rust) == 8 and sum(r["mentions"] for r in rust) == 4
    assert all(("Rust" in r["text"]) == bool(r["mentions"]) for r in rust)
    # У Python все 5 реплик с упоминанием: недостающие «без упоминания» добираются из другого пула
    python = [r for r in rows if r["tech"] == "python"]
    assert len(python) == 5 and all(r["mentions"] for r in python)


def test_export_sentiment_sample_cli(run_cli, sample_db, tmp_path):
    out = tmp_path / "sample.csv"
    assert run_cli(ess.main, "-d", sample_db, "-o", out, "--techs", "rust", "--per-tech", "6") == 0
    with out.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 6 and list(rows[0]) == ess.FIELDS
    assert rows[0]["hn_url"].startswith("https://news.ycombinator.com/item?id=")


def _labeled(tmp_path, rows):
    path = tmp_path / "labeled.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ess.FIELDS)
        writer.writeheader()
        for i, (tech, text, lc, lt) in enumerate(rows):
            writer.writerow({"tech": tech, "comment_id": i, "hn_url": "", "mentions": 1, "text": text,
                             "label_comment": lc, "label_tech": lt})
    return path


LABELED = [
    # Весь комментарий негативен, а о Rust — позитивно: аспектный режим должен это увидеть
    ("rust", "The weather is awful and terrible today. Rust is great and lovely.", "-1", "1"),
    ("rust", "I hate this horrible meeting. Rust is wonderful.", "-1", "1"),
    ("rust", "Rust is awful and broken.", "-1", "-1"),
    ("rust", "Rust exists.", "0", "0"),
    ("rust", "Lovely day.", "1", ""),
]


def test_read_labeled_validates(tmp_path):
    rows = ev.read_labeled(_labeled(tmp_path, LABELED))
    assert rows[0]["label_comment"] == -1 and rows[4]["label_tech"] is None
    with pytest.raises(ValueError, match="ожидается"):
        ev.read_labeled(_labeled(tmp_path, [("rust", "x", "2", "")]))


def test_evaluate_aspect_beats_whole_on_tech_labels(tmp_path):
    rows = ev.read_labeled(_labeled(tmp_path, LABELED))
    results = ev.evaluate(rows, ev.vader_scores(rows), {})
    f1 = {(r["target"], r["method"]): r for r in results}
    assert f1[("label_tech", "vader_aspect")]["f1"] > f1[("label_tech", "vader")]["f1"]
    assert f1[("label_comment", "vader")]["f1"] >= f1[("label_comment", "vader_aspect")]["f1"]
    assert f1[("label_tech", "vader")]["n"] == 4  # пустые метки не учитываются
    assert "label_tech" in ev.format_results(results)


def test_evaluate_cli_with_models(run_cli, tmp_path, capsys):
    sentences = [["rust", "great", "lovely", "good"], ["awful", "terrible", "bad"], ["weather", "today"]] * 30
    model = tmp_path / "w2v.model"
    Word2Vec(sentences, vector_size=8, min_count=1, seed=1, workers=1).save(str(model))
    out = tmp_path / "results.csv"
    assert run_cli(ev.main, "-i", _labeled(tmp_path, LABELED), "--comments-model", model,
                   "--titles-model", model, "--out-csv", out) == 0
    printed = capsys.readouterr().out
    assert "lexicon_aspect" in printed and "vader_window" in printed
    assert out.exists()


def test_evaluate_cli_requires_labels(run_cli, tmp_path):
    assert run_cli(ev.main, "-i", _labeled(tmp_path, [("rust", "x", "", "")])) == 1


def test_tune_model_grid_and_rank(tmp_path):
    rng = np.random.default_rng(0)
    langs, dbs = ["rust", "cpp", "go"], ["postgresql", "mysql", "sqlite"]
    sentences = [[*rng.choice(langs, 2), "compiler", "memory"] for _ in range(200)]
    sentences += [[*rng.choice(dbs, 2), "query", "index"] for _ in range(200)]
    configs = tune_model.grid([8, 16], [1], [5], [3])
    results = tune_model.rank(tune_model.tune(sentences, configs, workers=1))
    assert len(results) == 2 and {r["vector_size"] for r in results} == {8, 16}
    assert all(r["techs"] == 6 and r["pairs"] >= 3 for r in results)
    assert results[0]["mrr"] >= results[1]["mrr"]
