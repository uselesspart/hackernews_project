import pytest

from utils import lemmatize
from utils.lemmatize import (
    DEFAULT_PRESERVE_WORDS,
    TECH_TOKENS,
    canonicalize_tech_mentions,
    iter_tokenized_lines,
    load_preserve_words,
    tokenize_and_lemmatize,
)


@pytest.mark.parametrize("text, expected", [
    ("I love C++", "I love  cpp "),
    ("C# and F#", " csharp  and  fsharp "),
    ("ASP.NET and .NET", " dotnet  and  dotnet "),
    ("Node.js, Vue.js", " nodejs ,  vuejs "),
    ("Stable Diffusion on SQL Server", " stable_diffusion  on  sqlserver "),
    ("example.net is a domain", "example.net is a domain"),
    ("Plain text", "Plain text"),
])
def test_canonicalize_tech_mentions(text, expected):
    assert canonicalize_tech_mentions(text) == expected


def test_tech_tokens_are_preserved_by_default():
    assert TECH_TOKENS <= DEFAULT_PRESERVE_WORDS


@pytest.mark.parametrize("kwargs, expected", [
    ({}, ["hello", "world", "<NUM>"]),
    ({"keep_punct": True}, ["hello", ",", "world", "<NUM>", "!"]),
    ({"num_token": None}, ["hello", "world", "42"]),
    ({"lower": False}, ["Hello", "World", "<NUM>"]),
])
def test_tokenize_without_lemmatization(kwargs, expected):
    assert tokenize_and_lemmatize("Hello, World 42!", lemmatize_en=False, **kwargs) == expected


def test_tokenize_keeps_tech_tokens_and_compounds():
    tokens = tokenize_and_lemmatize("C++ vs C#: state-of-the-art", lemmatize_en=False)
    assert tokens == ["cpp", "vs", "csharp", "state-of-the-art"]


def test_tokenize_empty_text():
    assert tokenize_and_lemmatize("...", lemmatize_en=False) == []


def test_lemmatize_without_spacy_fails_loudly(monkeypatch, tmp_path):
    # Раньше без spaCy лемматизация молча отключалась, и модели учились на сырых словах
    monkeypatch.setattr(lemmatize, "_en_nlp", None)
    monkeypatch.setattr(lemmatize, "_en_nlp_error", ModuleNotFoundError("No module named 'click'"))
    monkeypatch.setattr(lemmatize, "_LEMMA_CACHE", {})
    with pytest.raises(RuntimeError, match="click"):
        tokenize_and_lemmatize("cats running")

    path = tmp_path / "in.txt"
    path.write_text("cats running\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="--no-lemmatize"):
        list(iter_tokenized_lines(path))
    # Без лемматизации spaCy не нужен
    assert list(iter_tokenized_lines(path, lemmatize_en=False)) == [["cats", "running"]]


@pytest.mark.spacy
@pytest.mark.parametrize("text, expected", [
    ("cats were running", ["cat", "be", "run"]),
    ("I don't like it", ["I", "do", "not", "like", "it"]),
    ("Windows and Kubernetes", ["windows", "and", "kubernetes"]),
    ("We moved to .NET and Node.js", ["we", "move", "to", "dotnet", "and", "nodejs"]),
    ("state-of-the-art models", ["state-of-the-art", "model"]),
    ("John's cats", ["john", "cat"]),
])
def test_tokenize_and_lemmatize(text, expected):
    preserve = load_preserve_words(None)
    assert tokenize_and_lemmatize(text, preserve_words=preserve) == expected


@pytest.mark.spacy
def test_custom_preserve_words():
    assert tokenize_and_lemmatize("running shoes", preserve_words={"running"}) == ["running", "shoe"]


@pytest.mark.spacy
@pytest.mark.parametrize("chunk_size", [1, 2, 1000])
def test_iter_tokenized_lines_matches_per_line_lemmatization(tmp_path, chunk_size):
    lines = ["Cats were running fast", "", "I don't like C++ or C#", "Running cats!", "Windows 11 users"]
    path = tmp_path / "in.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    preserve = load_preserve_words(None)

    expected = [tokenize_and_lemmatize(line, preserve_words=preserve) for line in lines if line]
    lemmatize._LEMMA_CACHE.clear()
    got = list(iter_tokenized_lines(path, preserve_words=preserve, chunk_size=chunk_size))
    assert got == expected


@pytest.mark.spacy
def test_lemma_cache_does_not_leak_preserved_words():
    # Слово, закэшированное как лемма, должно оставаться нетронутым, если его защитили позже
    assert tokenize_and_lemmatize("running", preserve_words=set()) == ["run"]
    assert tokenize_and_lemmatize("running", preserve_words={"running"}) == ["running"]
    assert tokenize_and_lemmatize("running", preserve_words=set()) == ["run"]


def test_load_preserve_words_from_file(tmp_path):
    path = tmp_path / "preserve.txt"
    path.write_text("# comment\nFooBar\n\nbaz\n", encoding="utf-8")
    words = load_preserve_words(path)
    assert {"foobar", "baz"} <= words
    assert words >= DEFAULT_PRESERVE_WORDS
    assert "# comment" not in words


def test_load_preserve_words_does_not_mutate_defaults(tmp_path):
    before = set(DEFAULT_PRESERVE_WORDS)
    load_preserve_words(None).add("extra")
    assert before == DEFAULT_PRESERVE_WORDS


def test_iter_tokenized_lines(tmp_path):
    path = tmp_path / "in.txt"
    path.write_text("First line\n\nSecond 2\n", encoding="utf-8")
    assert list(iter_tokenized_lines(path, lemmatize_en=False)) == [["first", "line"], ["second", "<NUM>"]]
    assert list(iter_tokenized_lines(path, lemmatize_en=False, preserve_empty=True)) == [
        ["first", "line"], [], ["second", "<NUM>"]
    ]
