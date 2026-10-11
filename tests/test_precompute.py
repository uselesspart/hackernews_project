import numpy as np
import pytest
from gensim.models import Word2Vec
from sqlalchemy import create_engine, select

from analytics.embeddings.scripts import precompute as pc
from db import session_scope
from db.models import SentimentExample, Tech, TechMetrics, TechNeighbor, TechWord
from hackernews_handler import HNHandler
from tests.conftest import write_jsonl


@pytest.fixture
def context_model(tmp_path):
    sentences = [["cpp", "rust", "go", "code"], ["rust", "go", "memory"], ["cpp", "templates"]] * 30
    path = tmp_path / "context.model"
    Word2Vec(sentences, vector_size=8, min_count=1, seed=1, workers=1).save(str(path))
    return str(path)


def _metrics(session) -> dict[str, TechMetrics]:
    return {name: m for name, m in session.execute(select(Tech.name, TechMetrics).join(TechMetrics))}


def test_precompute_without_models(classified_db):
    with session_scope(classified_db) as session:
        counts = pc.precompute(session, lemmatize=False)
        metrics = _metrics(session)

    assert counts["techs"] == len(metrics) > 100  # строка на каждую технологию из tech
    cpp, rust, pg = metrics["cpp"], metrics["rust"], metrics["postgresql"]
    assert (cpp.stories, cpp.comments, cpp.avg_score) == (1, 4, 10.0)
    assert rust.stories == 1
    assert pg.stories == 0  # единственная статья про Postgres — dead
    # Тональность по комментариям веток: у C++ живые 10, 11 и 13 (12 — dead)
    assert cpp.sentiment_n == 3
    assert cpp.sentiment_index is not None
    assert cpp.irr is None and cpp.map_x is None  # без моделей не считаются


def test_precompute_words_and_examples(classified_db):
    with session_scope(classified_db) as session:
        pc.precompute(session, lemmatize=False, threshold=0.05)
        cpp_id = session.scalar(select(Tech.id).where(Tech.name == "cpp"))
        words = dict(session.execute(select(TechWord.word, TechWord.count).where(TechWord.tech_id == cpp_id)).all())
        examples = session.scalars(select(SentimentExample).where(SentimentExample.tech_id == cpp_id)).all()

    assert {"great", "language", "agree"} <= set(words)
    assert "cpp" not in words  # название самой технологии исключено
    by_label = {label: {e.comment_id for e in examples if e.label == label} for label in (1, -1)}
    assert by_label == {1: {10, 11}, -1: {13}}  # "Great language", "I agree" / "reply to dead"


def test_precompute_is_idempotent(classified_db):
    with session_scope(classified_db) as session:
        first = pc.precompute(session, lemmatize=False)
        second = pc.precompute(session, lemmatize=False)
        assert first == second
        assert session.query(TechMetrics).count() == first["techs"]


def test_precompute_neighbors_and_map(classified_db, context_model):
    with session_scope(classified_db) as session:
        counts = pc.precompute(session, context_model=context_model, lemmatize=False, n_neighbors=2)
        metrics = _metrics(session)
        rows = session.execute(
            select(Tech.name, TechNeighbor.similarity)
            .join(Tech, Tech.id == TechNeighbor.neighbor_id)
            .where(TechNeighbor.tech_id == metrics["rust"].tech_id)
        ).all()

    # Из технологий в словаре модели только cpp, rust и go: по 2 соседа у каждой
    assert counts["neighbors"] == 3 * 2
    assert {name for name, _ in rows} == {"cpp", "go"}
    assert all(-1 <= sim <= 1 for _, sim in rows)
    assert all(metrics[k].map_x is not None for k in ("cpp", "rust", "go"))
    assert metrics["python"].map_x is None  # нет в словаре модели


def test_neighbors_and_map_need_enough_techs():
    kv = Word2Vec([["rust", "code"]] * 10, vector_size=4, min_count=1, seed=1, workers=1).wv
    assert pc.neighbors_and_map(kv, ["rust", "python"], 5) == ({}, {})


def test_sample_comments_is_deterministic():
    comments = [(i, f"c{i}") for i in range(100)]
    sample = pc.sample_comments(comments, 10)
    assert sample == pc.sample_comments(comments, 10)
    assert len(sample) == 10 and sample == sorted(sample)
    assert pc.sample_comments(comments[:5], 10) == comments[:5]


def test_stop_words_for():
    assert {"go", "golang", "goroutine"} <= pc.stop_words_for("go")
    assert "stable_diffusion" in pc.stop_words_for("stable_diffusion")


def test_irr_uses_all_stories(db_url, tmp_path):
    # Статьи про Rust собирают больше комментариев, чем статьи без технологий — IRR > 1
    rng = np.random.default_rng(0)
    items, next_id = [], 1
    for i in range(400):
        tech = ["rust", "python", None][i % 3]
        title = {"rust": "Rust internals", "python": "Python tips", None: "Random news"}[tech]
        mu = {"rust": 30, "python": 10, None: 10}[tech]
        items.append({"id": next_id, "type": "story", "title": title,
                      "descendants": int(rng.poisson(mu)), "score": 1, "time": 1700000000 + i})
        next_id += 1
    engine = create_engine(db_url)
    HNHandler(engine).ingest_from_path(write_jsonl(tmp_path / "items.jsonl", items))
    engine.dispose()

    model = tmp_path / "titles.model"
    Word2Vec([["rust", "python", "code"]] * 20, vector_size=4, min_count=1, seed=1, workers=1).save(str(model))
    with session_scope(db_url) as session:
        irr = pc.irr_by_tech(session, Word2Vec.load(str(model)), "negbin")

    assert irr["rust"]["irr"] == pytest.approx(3.0, rel=0.15)
    assert irr["python"]["irr"] == pytest.approx(1.0, rel=0.15)
    assert irr["rust"]["irr_low"] > 1


def test_irr_failure_does_not_break_precompute(classified_db, tmp_path):
    model = tmp_path / "titles.model"
    Word2Vec([["rust", "code"]] * 10, vector_size=4, min_count=1, seed=1, workers=1).save(str(model))
    with session_scope(classified_db) as session:
        counts = pc.precompute(session, titles_model=str(model), lemmatize=False)
    assert counts["techs"] > 0


def test_precompute_cli(run_cli, classified_db, context_model, capsys):
    assert run_cli(pc.main, "-d", classified_db, "--context-model", context_model, "--no-lemmatize") == 0
    assert "Готово: технологий" in capsys.readouterr().out
