import pytest
from fastapi.testclient import TestClient
from gensim.models import Word2Vec

from analytics.embeddings.scripts.precompute import precompute
from api.config import Settings
from api.main import create_app
from db import session_scope


def make_client(db_url, **settings):
    return TestClient(create_app(Settings(db_url=db_url, cors_origins=["http://localhost:5173"], **settings)))


@pytest.fixture
def api_db(classified_db, tmp_path):
    model = tmp_path / "context.model"
    sentences = [["cpp", "rust", "go", "code"], ["rust", "go", "memory"], ["cpp", "templates"]] * 30
    Word2Vec(sentences, vector_size=8, min_count=1, seed=1, workers=1).save(str(model))
    with session_scope(classified_db) as session:
        precompute(session, context_model=str(model), lemmatize=False, threshold=0.05)
    return classified_db


@pytest.fixture
def client(api_db):
    with make_client(api_db, min_sentiment_comments=3, min_irr_stories=30) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta(client):
    meta = client.get("/api/meta").json()
    assert meta["stories"] == 3  # история 3 — dead
    assert meta["comments"] == 7
    assert meta["techs_with_stories"] == 4  # cpp, rust, go, postgresql
    assert meta["period_start"].startswith("2023-11-14")
    assert meta["computed_at"] is not None


@pytest.mark.parametrize("q, first, matched", [
    ("rust", "rust", None),
    ("golang", "go", "golang"),
    ("c++", "cpp", None),
    ("postgres", "postgresql", "postgres"),
])
def test_suggest(client, q, first, matched):
    items = client.get("/api/techs/suggest", params={"q": q}).json()
    assert items[0]["key"] == first
    assert items[0]["matched"] == matched
    assert set(items[0]) == {"key", "name", "category", "stories", "matched"}


def test_suggest_empty_query_is_popularity(client):
    items = client.get("/api/techs/suggest", params={"limit": 3}).json()
    assert [i["stories"] for i in items] == [1, 1, 1]
    assert {i["key"] for i in items} <= {"cpp", "rust", "go"}


def test_suggest_validation(client):
    assert client.get("/api/techs/suggest", params={"limit": 0}).status_code == 422


def test_list_techs(client):
    items = client.get("/api/techs").json()
    assert {i["key"] for i in items} == {"cpp", "rust", "go"}  # min_stories=1 по умолчанию
    cpp = next(i for i in items if i["key"] == "cpp")
    assert cpp["categories"] == [{"key": "programming_language", "name": "Язык программирования"}]
    assert cpp["sentiment"]["n"] == 3 and cpp["sentiment"]["reliable"] is True
    assert cpp["map_x"] is not None
    assert len(client.get("/api/techs", params={"min_stories": 0}).json()) > 100


def test_list_techs_sorted_by_sentiment_puts_unreliable_last(client):
    items = client.get("/api/techs", params={"sort": "sentiment"}).json()
    reliable = [i["sentiment"]["reliable"] for i in items]
    assert reliable == sorted(reliable, reverse=True)


def test_profile(client):
    p = client.get("/api/techs/cpp").json()
    assert (p["key"], p["name"]) == ("cpp", "C++")
    assert "cplusplus" in p["aliases"]
    assert p["stats"]["stories"] == 1 and p["stats"]["comments"] == 4
    assert p["stats"]["share"] == pytest.approx(1 / 3)
    assert p["stats"]["rank"] in (1, 2, 3)
    assert p["domains"] == [{"domain": "example.com", "count": 1}]
    assert {n["key"] for n in p["neighbors"]} == {"rust", "go"}
    assert p["map"] is not None

    s = p["sentiment"]
    assert s["reliable"] is True and s["n"] == 3
    assert [e["comment_id"] for e in s["negative"]] == [13]
    assert {e["comment_id"] for e in s["positive"]} == {10, 11}
    assert s["positive"][0]["hn_url"] == f"https://news.ycombinator.com/item?id={s['positive'][0]['comment_id']}"
    assert p["irr"] == {"value": None, "low": None, "high": None, "pval": None,
                        "reliable": False, "significant": False}


def test_profile_cooccurring_and_case_insensitive_key(client):
    p = client.get("/api/techs/RUST").json()
    assert p["key"] == "rust"
    assert p["cooccurring"] == [{"key": "go", "name": "Go", "stories": 1}]


def test_profile_of_tracked_tech_without_data(client):
    p = client.get("/api/techs/fossil").json()
    assert p["stats"]["stories"] == 0 and p["stats"]["rank"] is None
    assert p["sentiment"]["reliable"] is False
    assert p["neighbors"] == [] and p["map"] is None


def test_unknown_tech_404(client):
    r = client.get("/api/techs/kubernetes")
    assert r.status_code == 404
    assert "не отслеживается" in r.json()["detail"]


def test_stories(client):
    page = client.get("/api/techs/rust/stories").json()
    assert page["total"] == 1
    story = page["items"][0]
    assert story["title"] == "Rust vs Golang"
    assert story["hn_url"].endswith("?id=2")
    assert client.get("/api/techs/rust/stories", params={"offset": 1}).json()["items"] == []
    assert client.get("/api/techs/rust/stories", params={"sort": "bad"}).status_code == 422


def test_timeline_zero_fills_dataset_period(client):
    t = client.get("/api/techs/cpp/timeline", params={"bucket": "day"}).json()
    assert t["bucket"] == "day"
    assert t["span_days"] == pytest.approx(300 / 86400)
    assert t["points"] == [{"period": "2023-11-14", "stories": 1}]
    week = client.get("/api/techs/fossil/timeline").json()
    assert week["points"] == [{"period": "2023-11-13", "stories": 0}]  # понедельник недели


def test_reliability_threshold(api_db):
    with make_client(api_db, min_sentiment_comments=30) as c:
        assert c.get("/api/techs/cpp").json()["sentiment"]["reliable"] is False


def test_api_works_before_precompute(ingested_db):
    # Таблицы метрик создаются при старте, метрики пустые, но статьи и поиск работают
    with make_client(ingested_db) as c:
        assert c.get("/api/techs/cpp").json()["stats"]["stories"] == 0  # classify ещё не запускали
        assert c.get("/api/techs/suggest", params={"q": "rust"}).json()[0]["key"] == "rust"
        assert c.get("/api/meta").json()["computed_at"] is None


def test_cors(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
