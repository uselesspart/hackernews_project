import pytest

from analytics.catalog import AREA_GROUPS, CATALOG, GROUP_NAMES, tech_info
from analytics.embeddings.patterns import PATTERNS
from api.search import normalize, suggest
from utils.groups import categories as GROUPS


def test_catalog_covers_all_patterns():
    assert set(CATALOG) == set(PATTERNS)


def test_every_tech_has_a_category():
    assert [key for key, info in CATALOG.items() if not info.categories] == []


def test_every_group_has_a_display_name():
    assert set(GROUPS) <= set(GROUP_NAMES)


def test_areas_and_categories_are_split():
    info = CATALOG["python"]
    assert info.categories == ("programming_language",)
    assert set(info.areas) <= set(AREA_GROUPS)
    assert "ai" in info.areas


def test_aliases_are_lowercase_and_unique():
    for info in CATALOG.values():
        assert all(a == a.lower() for a in info.aliases), info.key
        assert len(set(info.aliases)) == len(info.aliases), info.key


def test_tech_info_for_unknown_key():
    info = tech_info("kubernetes")
    assert (info.key, info.name, info.aliases) == ("kubernetes", "kubernetes", ())


ENTRIES = [(info, {"javascript": 19, "rust": 14, "ruby": 5, "go": 4, "postgresql": 11,
                   "typescript": 2, "druid": 0}.get(key, 0))
           for key, info in CATALOG.items()]


def keys(query, limit=8):
    return [m.info.key for m in suggest(query, ENTRIES, limit)]


@pytest.mark.parametrize("query, expected_first", [
    ("rust", "rust"),
    ("Rust", "rust"),
    ("  rust  ", "rust"),
    ("golang", "go"),
    ("postgres", "postgresql"),
    ("pg", "postgresql"),
    ("c#", "csharp"),
    ("c++", "cpp"),
    ("dotnet", "csharp"),
    ("javscript", "javascript"),   # опечатка
    ("chatgpt", "gpt"),
    ("stable diff", "stable_diffusion"),
])
def test_suggest_first_hit(query, expected_first):
    assert keys(query)[0] == expected_first


def test_suggest_reports_matched_alias():
    match = suggest("golang", ENTRIES)[0]
    assert match.matched == "golang"
    assert suggest("Go", ENTRIES)[0].matched is None  # совпало имя


def test_suggest_prefix_ranks_by_popularity():
    # "ru": Rust и Ruby — префиксные совпадения, Rust популярнее
    assert keys("ru")[:2] == ["rust", "ruby"]


def test_suggest_empty_query_returns_most_popular():
    assert keys("", limit=3) == ["javascript", "rust", "postgresql"]


def test_suggest_nothing_found():
    assert keys("xyzzy") == []


def test_suggest_limit():
    assert len(keys("a", limit=5)) == 5


def test_normalize():
    assert normalize("  Stable   Diffusion ") == "stable diffusion"
