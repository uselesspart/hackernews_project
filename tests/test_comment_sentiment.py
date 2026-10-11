import re

import pytest

from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.sentiment import (
    EXAMPLE_MAX_CHARS,
    TechSentiment,
    excerpt,
    mention_text,
    sentences,
    split_comment,
)

RUST = COMPILED_PATTERNS["rust"]


def test_split_comment_drops_quotes_and_code():
    raw = ("> Rust is terrible<p>I disagree, it is great."
           "<p><pre><code>  fn main() { panic!() }\n</code></pre>\nWorks for me.")
    parts = split_comment(raw)
    assert parts.paragraphs == ("I disagree, it is great.", "Works for me.")
    assert parts.has_quote and parts.has_code
    assert "terrible" not in parts.prose and "panic" not in parts.prose


def test_split_comment_plain_and_empty():
    parts = split_comment("Just <i>text</i> here")
    assert parts.prose == "Just text here"
    assert not parts.has_quote and not parts.has_code
    assert split_comment(None).prose == "" and split_comment("> only a quote").prose == ""


def test_split_comment_unclosed_pre():
    assert split_comment("Before<p><pre><code>x = 1").prose == "Before"


def test_sentences():
    assert sentences("I like Rust. It is fast! Is it? 3 more.") == ["I like Rust.", "It is fast!", "Is it?", "3 more."]
    assert sentences("e.g. this stays one") == ["e.g. this stays one"]


def test_mention_text_keeps_only_sentences_with_tech():
    parts = split_comment("The weather is awful. Rust is lovely.<p>Nothing here. I use cargo build daily.")
    assert mention_text(parts, RUST) == "Rust is lovely. I use cargo build daily."
    assert mention_text(split_comment("No mention at all."), RUST) is None


def test_excerpt_short_and_no_pattern():
    assert excerpt("short text", RUST) == "short text"
    long = "x" * 1000
    assert excerpt(long) == long[:EXAMPLE_MAX_CHARS]


def test_excerpt_starts_near_late_mention():
    text = "Intro sentence. " * 60 + "Rust is great here. Tail."
    out = excerpt(text, RUST)
    assert out.startswith("… Rust is great here.")
    assert len(out) <= EXAMPLE_MAX_CHARS


def test_excerpt_long_sentence_without_full_stop():
    text = "word " * 200 + "and Rust shines"
    out = excerpt(text, RUST)
    assert out.startswith("… ") and "Rust shines" in out
    assert len(out) <= EXAMPLE_MAX_CHARS
    assert not re.match(r"… \S*word\S", out)  # начинается с границы слова


def _add(acc, cid, raw, whole, aspect):
    acc.add(cid, split_comment(raw), whole, aspect, RUST)


def test_tech_sentiment_summaries():
    acc = TechSentiment(n_examples=2, threshold=0.1)
    _add(acc, 1, "Rust is great", 0.8, 0.8)
    _add(acc, 2, "Bad weather", -0.6, None)
    _add(acc, 3, "Meh", 0.0, None)
    whole, aspect = acc.summary("whole"), acc.summary("aspect")
    assert whole["n_total"] == 3 and whole["pos_share"] == pytest.approx(1 / 3)
    assert aspect["n_total"] == 1 and aspect["sentiment_index"] == pytest.approx(0.8)
    assert TechSentiment(1, 0.1).summary("aspect") is None


def test_examples_prefer_mentions_and_skip_quotes_and_code():
    acc = TechSentiment(n_examples=2, threshold=0.1)
    _add(acc, 1, "Lovely day, unrelated", 0.95, None)        # самый позитивный, но не о Rust
    _add(acc, 2, "Rust is nice", 0.5, 0.5)
    _add(acc, 3, "> quoted<p>Rust rocks", 0.9, 0.9)            # цитата — не пример
    _add(acc, 4, "Rust<p><pre><code>x</code></pre>", 0.9, 0.9)  # код — не пример
    _add(acc, 5, "Awful mess everywhere", -0.9, None)          # негатив только без упоминания
    examples = acc.examples()

    positive = [e for e in examples if e["label"] == 1]
    negative = [e for e in examples if e["label"] == -1]
    assert [(e["comment_id"], e["mentions"]) for e in positive] == [(2, True)]
    assert [(e["comment_id"], e["mentions"], e["score"]) for e in negative] == [(5, False, -0.9)]


def test_examples_top_k_order_and_ties():
    acc = TechSentiment(n_examples=2, threshold=0.1)
    for cid, score in [(1, 0.5), (2, 0.9), (3, 0.9), (4, 0.7)]:
        _add(acc, cid, "Rust ok", score, score)
    ids = [e["comment_id"] for e in acc.examples() if e["label"] == 1]
    assert ids == [2, 3]  # по убыванию тона, при равенстве — меньший id


def test_no_examples_requested():
    acc = TechSentiment(n_examples=0, threshold=0.1)
    _add(acc, 1, "Rust is great", 0.8, 0.8)
    assert acc.examples() == [] and len(acc.whole) == 1
