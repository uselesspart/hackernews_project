import pytest

from utils.clean_text import clean_text


@pytest.mark.parametrize("raw, expected", [
    (None, ""),
    ("", ""),
    ("  plain   text \n", "plain text"),
    ("I&#x27;m &quot;here&quot;", 'I\'m "here"'),
    ("<p>Hello<i>world</i></p>", "Hello world"),
    ("see [docs](https://example.com/x) now", "see docs now"),
    ("link https://example.com/a?b=c end", "link end"),
])
def test_clean_text(raw, expected):
    assert clean_text(raw) == expected
