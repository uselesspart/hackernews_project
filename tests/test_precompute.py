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


def test_precompute_skips_neighbors_of_degenerate_model(classified_db, tmp_path):
    # Как на корпусе в 20 тыс. элементов: векторы технологий почти совпадают (близость ~0.999)
    model = Word2Vec([["cpp", "rust", "go", "code"]] * 10, vector_size=8, min_count=1, seed=1, workers=1)
    base = np.ones(8, dtype=np.float32)
    for i, word in enumerate(["cpp", "rust", "go"]):
        model.wv.vectors[model.wv.key_to_index[word]] = base + 1e-3 * i
    path = tmp_path / "degenerate.model"
    model.save(str(path))

    with session_scope(classified_db) as session:
        assert pc.precompute(session, context_model=str(path), lemmatize=False)["neighbors"] == 0
        assert _metrics(session)["rust"].map_x is None
        forced = pc.precompute(session, context_model=str(path), lemmatize=False, allow_degenerate=True)
    assert forced["neighbors"] > 0


def test_neighbors_and_map_need_enough_techs():
    kv = Word2Vec([["rust", "code"]] * 10, vector_size=4, min_count=1, seed=1, workers=1).wv
    assert pc.neighbors_and_map(kv, ["rust", "python"], 5) == ({}, {})


def test_comment_counts_for_every_tech_of_story(classified_db):
    # "Rust vs Golang": единственный живой комментарий "Rust is nice" засчитан обеим технологиям,
    # но аспектный тон — только Rust: Go в нём не упомянут
    with session_scope(classified_db) as session:
        pc.precompute(session, lemmatize=False)
        metrics = _metrics(session)
    rust, go = metrics["rust"], metrics["go"]
    assert rust.sentiment_n == go.sentiment_n == 1
    assert (rust.aspect_n, go.aspect_n) == (1, 0)
    assert rust.aspect_index is not None and go.aspect_index is None


def _ingest(db_url, tmp_path, items):
    from analytics.embeddings.scripts.classify_tech import classify_stories
    engine = create_engine(db_url)
    HNHandler(engine).ingest_from_path(write_jsonl(tmp_path / "items.jsonl", items))
    engine.dispose()
    with session_scope(db_url) as session:
        classify_stories(session)


def test_precompute_uses_all_comments_without_quotes_and_code(db_url, tmp_path):
    comments = [
        "&gt; Rust is terrible and awful<p>I love Rust, it is wonderful.",
        "Rust<p><pre><code>fn horrible_function() {}</code></pre>",
        "Lovely weather today, great and wonderful.",
        "Rust compile times are awful and painful.",
    ] + [f"Item {i} was checked." for i in range(40)]  # «Neutral» у VADER — позитивное слово
    items = [{"id": 1, "type": "story", "title": "Rust in production", "descendants": len(comments),
              "score": 5, "time": 1700000000}]
    items += [{"id": 100 + i, "type": "comment", "parent": 1, "text": t, "time": 1700000001 + i}
              for i, t in enumerate(comments)]
    _ingest(db_url, tmp_path, items)

    with session_scope(db_url) as session:
        pc.precompute(session, lemmatize=False, threshold=0.05)
        rust = _metrics(session)["rust"]
        examples = session.scalars(select(SentimentExample).where(SentimentExample.tech_id == rust.tech_id)).all()
        words = set(session.scalars(select(TechWord.word).where(TechWord.tech_id == rust.tech_id)))

    assert rust.sentiment_n == len(comments)
    # Упоминают Rust: 100 (без цитаты), 101 (только слово, код вырезан), 103
    assert rust.aspect_n == 3
    by_label = {label: [(e.comment_id, e.mentions) for e in examples if e.label == label] for label in (1, -1)}
    # Негативный пример — реплика о Rust. Позитивных реплик о Rust без цитат и кода нет
    # (в 100 — цитата, в 101 — код), поэтому позитивный пример — из комментариев целиком
    assert by_label == {1: [(102, False)], -1: [(103, True)]}
    assert "horrible_function" not in words and "terrible" not in words  # код и цитата не в словах
    assert "wonderful" in words


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
