import numpy as np
import pytest
from gensim.models import KeyedVectors

from analytics.embeddings import w2v_quality as wq
from analytics.embeddings.patterns import PATTERNS


def make_kv(vectors: dict[str, list[float]]) -> KeyedVectors:
    kv = KeyedVectors(vector_size=len(next(iter(vectors.values()))))
    kv.add_vectors(list(vectors), np.array(list(vectors.values()), dtype=np.float32))
    return kv


def test_check_pairs_use_tracked_techs():
    assert {t for pair in wq.CHECK_PAIRS for t in pair} <= set(PATTERNS)


def test_quality_report_ranks_and_hit_rate():
    kv = make_kv({
        "rust": [1.0, 0.1, 0.0], "cpp": [1.0, 0.0, 0.0], "go": [0.0, 1.0, 0.0],
        "postgresql": [0.0, 0.0, 1.0], "mysql": [0.1, 0.0, 1.0], "word": [1.0, 1.0, 1.0],
    })
    report = wq.quality_report(kv, ["rust", "cpp", "go", "postgresql", "mysql", "python"],
                               pairs=[("rust", "cpp"), ("rust", "go"), ("postgresql", "mysql"), ("python", "r")], k=1)
    pairs = {(p["a"], p["b"]): p["rank"] for p in report["pairs"]}
    assert pairs == {("rust", "cpp"): 1, ("rust", "go"): 2, ("postgresql", "mysql"): 1}  # python нет в словаре
    assert report["techs"] == 5
    assert report["hit_rate"] == pytest.approx(2 / 3)
    assert report["mrr"] == pytest.approx((1 + 0.5 + 1) / 3)
    assert not report["degenerate"]
    assert "место 2" in wq.format_report(report)


def test_quality_report_detects_degenerate_model():
    kv = make_kv({"rust": [1.0, 0.001], "cpp": [1.0, 0.002], "go": [1.0, 0.0]})
    report = wq.quality_report(kv, ["rust", "cpp", "go"])
    assert report["degenerate"] and report["mean_similarity"] > 0.99
    assert "вырождена" in wq.format_report(report)


def test_quality_report_without_techs():
    report = wq.quality_report(make_kv({"word": [1.0, 0.0]}), ["rust"])
    assert report["techs"] == 0 and not report["degenerate"] and report["hit_rate"] is None
    assert "ни одной пары" in wq.format_report(report)
