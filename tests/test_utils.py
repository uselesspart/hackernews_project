import gzip
import sys

import numpy as np
import pytest

from utils.cli import cli_main
from utils.groups import normalize_categories, normalize_token
from utils.io import iter_jsonl, open_text, read_nonempty_lines
from utils.vectors import cosine

# --- utils.vectors ------------------------------------------------------------

def test_cosine():
    assert cosine(np.array([1.0, 0.0]), np.array([0.0, 0.0])) == 0.0
    assert cosine(np.array([1.0, 1.0]), np.array([2.0, 2.0])) == pytest.approx(1.0)
    assert cosine(np.array([1.0, 0.0]), np.array([-3.0, 0.0])) == pytest.approx(-1.0)


# --- utils.groups -------------------------------------------------------------

def test_normalize_token():
    assert normalize_token(" Stable Diffusion ") == "stable_diffusion"


def test_normalize_categories_dedups_and_keeps_order():
    raw = {"lang": ["Python", "python", " Stable Diffusion ", "Go"], 1: ["Go"]}
    assert normalize_categories(raw) == {"lang": ["python", "stable_diffusion", "go"], "1": ["go"]}


# --- utils.io -----------------------------------------------------------------

def test_iter_jsonl_plain_and_gzip(tmp_path):
    lines = ['{"id": 1}', "", "not json", "[1, 2]", '{"id": 2}']
    plain = tmp_path / "a.jsonl"
    plain.write_text("\n".join(lines), encoding="utf-8")
    packed = tmp_path / "a.jsonl.gz"
    with gzip.open(packed, "wt", encoding="utf-8") as f:
        f.write("\n".join(lines))

    assert list(iter_jsonl(plain)) == [{"id": 1}, {"id": 2}]
    assert list(iter_jsonl(packed)) == [{"id": 1}, {"id": 2}]


def test_iter_jsonl_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(iter_jsonl(tmp_path / "nope.jsonl"))


def test_open_text_writes_utf8(tmp_path):
    path = tmp_path / "out.txt.gz"
    with open_text(path, "wt") as f:
        f.write("привет\n")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        assert f.read() == "привет\n"


def test_read_nonempty_lines(tmp_path):
    path = tmp_path / "lines.txt"
    path.write_bytes(b"  a \n\n b\n\xff\n")  # \xff — невалидный UTF-8
    assert read_nonempty_lines(path, errors="replace") == ["a", "b", "�"]
    with pytest.raises(UnicodeDecodeError):
        read_nonempty_lines(path)


# --- utils.cli ----------------------------------------------------------------

def test_cli_main_return_codes(capsys, monkeypatch):
    @cli_main
    def ok():
        return None

    @cli_main
    def fails():
        raise ValueError("boom")

    @cli_main
    def interrupted():
        raise KeyboardInterrupt

    assert ok() == 0
    assert fails() == 1
    assert "Ошибка: boom" in capsys.readouterr().err
    assert interrupted() == 130


def test_cli_main_traceback_in_debug_mode(capsys, monkeypatch):
    @cli_main
    def fails():
        raise ValueError("boom")

    monkeypatch.setenv("HN_DEBUG", "1")
    assert fails() == 1
    err = capsys.readouterr().err
    assert "Traceback" in err and "ValueError: boom" in err


def test_cli_main_lets_system_exit_through():
    # argparse при --help/ошибке аргументов делает sys.exit — это не должно превращаться в "Ошибка"
    @cli_main
    def exits():
        sys.exit(2)

    with pytest.raises(SystemExit):
        exits()
