import re

import pytest

from analytics.embeddings.patterns import PATTERNS
from analytics.embeddings.scripts.classify_tech import match_techs
from utils.groups import categories


@pytest.mark.parametrize("title, expected", [
    # Названия со спецсимволами
    ("Why C++ is still relevant", {"cpp"}),
    ("C++20 modules explained", {"cpp"}),
    ("C# vs Java performance", {"csharp", "java"}),
    ("Porting our .NET app to Linux", {"csharp", "linux"}),
    ("ASP.NET Core 8 released", {"csharp"}),
    ("Node.js 22 is out", {"javascript"}),
    # Язык C отдельно от C++
    ("Writing an OS in C", {"c"}),
    ("C and C++ interop", {"c", "cpp"}),
    ("C11 atomics in practice", {"c"}),
    # Обычные случаи
    ("Rust 1.80 released", {"rust"}),
    ("Postgres 17 performance", {"postgresql"}),
    ("Meta releases SAM 2", {"sam"}),
    ("Snowflake acquires Streamlit", {"snowflake"}),
    ("Running Llama 3 locally with llama.cpp", {"llama", "cpp"}),  # llama.cpp написан на C++
    ("Show HN: A Python tool for Git", {"python", "git"}),
])
def test_match_techs_detects(title, expected):
    assert match_techs(title, PATTERNS) == expected


@pytest.mark.parametrize("title", [
    "Plan C for climate",
    "USB-C is finally here",
    "Sam Altman returns to OpenAI",
    "Fossil fuels subsidies rise",
    "Our tech stack in 2024",
    "An influx of new users",
    "Bloom filters explained",
    "Snowflake IDs at scale",
    "Redshift of distant galaxies",
    "Charles Darwin's notebooks",
    "The node graph of Kubernetes",
    "A coin in mint condition",
    "The Stack Overflow developer survey",
])
def test_match_techs_avoids_false_positives(title):
    assert match_techs(title, PATTERNS) == set()


@pytest.mark.parametrize("title", ["", None])
def test_match_techs_empty_title(title):
    assert match_techs(title, PATTERNS) == set()


def test_all_patterns_are_case_insensitive():
    for tech, pats in PATTERNS.items():
        for pat in pats:
            assert pat.flags & re.IGNORECASE, (tech, pat.pattern)


def test_group_members_are_known_techs():
    # Группы в utils.groups ссылаются на ключи PATTERNS; опечатка тихо выкидывала бы технологию из группы
    unknown = {m for members in categories.values() for m in members} - set(PATTERNS)
    assert unknown == set()
