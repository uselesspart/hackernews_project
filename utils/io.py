import csv
import gzip
import json
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import IO, Any

EXPORT_FORMATS = ("txt", "csv", "jsonl")


def open_text(path: str | Path, mode: str = "rt", errors: str = "strict") -> IO[str]:
    """Открывает .gz прозрачно, остальные файлы — как обычный текст в UTF-8."""
    p = Path(path)
    if p.suffix == ".gz":
        return gzip.open(p, mode, encoding="utf-8", errors=errors)
    return open(p, mode.replace("t", ""), encoding="utf-8", errors=errors)


def iter_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """Объекты из JSONL(.gz); пустые, битые и не-объектные строки пропускаются."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")
    with open_text(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def write_records(path: str | Path, fmt: str, fields: Sequence[str], records: Iterable[Sequence],
                  txt: Callable[[Sequence], str]) -> None:
    """
    Пишет записи в txt (одна строка на запись, текст строит txt(record)),
    csv (с заголовком fields) или jsonl (объект {field: value}). Каталог создаётся при необходимости.
    """
    if fmt not in EXPORT_FORMATS:
        raise ValueError(f"Неизвестный формат {fmt!r}, ожидается один из {EXPORT_FORMATS}")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        if fmt == "txt":
            f.writelines(txt(r) + "\n" for r in records)
        elif fmt == "csv":
            writer = csv.writer(f)
            writer.writerow(fields)
            writer.writerows(records)
        else:
            f.writelines(json.dumps(dict(zip(fields, r, strict=True)), ensure_ascii=False) + "\n"
                         for r in records)


def read_nonempty_lines(path: str | Path, errors: str = "strict") -> list[str]:
    """Строки файла без пробелов по краям; пустые строки пропускаются."""
    with open_text(path, errors=errors) as f:
        return [s for s in (line.strip() for line in f) if s]
