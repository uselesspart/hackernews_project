import argparse
import contextlib
import gzip
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from utils.cli import cli_main


def iter_files(input_dir: Path, pattern: str, recursive: bool) -> Iterable[Path]:
    yield from sorted(input_dir.rglob(pattern) if recursive else input_dir.glob(pattern))


def _digest(text: str) -> bytes:
    return hashlib.blake2s(text.encode("utf-8"), digest_size=16).digest()


def _dedup_key_line(line: str) -> bytes:
    # Нормализуем перевод строки и считаем хеш содержимого
    return _digest(line.rstrip("\r\n"))


def _dedup_key_json(line: str) -> bytes:
    raw = line.rstrip("\r\n")
    # Канонизируем JSON: сортировка ключей, компактные разделители; невалидный JSON сравниваем как строку
    with contextlib.suppress(json.JSONDecodeError):
        raw = json.dumps(json.loads(raw), separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return _digest(raw)

def merge_jsonl_gz(
    input_dir: Path,
    output_path: Path,
    pattern: str = "*.jsonl.gz",
    recursive: bool = False,
    encoding: str = "utf-8",
    dedup: str = "line",  # 'line' или 'json'
) -> None:
    files = list(iter_files(input_dir, pattern, recursive))
    if not files:
        raise FileNotFoundError(f"Не нашёл файлов по маске {pattern} в {input_dir}")

    if dedup not in {"line", "json"}:
        raise ValueError("Параметр --dedup должен быть 'line' или 'json'")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    make_key = _dedup_key_json if dedup == "json" else _dedup_key_line
    seen = set()  # множество ключей (хешей) уже записанных строк

    total_in_lines = 0
    total_out_lines = 0
    total_duplicates = 0

    with gzip.open(output_path, "wt", encoding=encoding, newline="\n") as w:
        for idx, f in enumerate(files, 1):
            in_lines = 0
            out_lines = 0
            duplicates = 0
            with gzip.open(f, "rt", encoding=encoding, errors="strict") as r:
                for line in r:
                    in_lines += 1
                    key = make_key(line)
                    if key in seen:
                        duplicates += 1
                        continue
                    seen.add(key)
                    w.write(line)
                    out_lines += 1

            total_in_lines += in_lines
            total_out_lines += out_lines
            total_duplicates += duplicates
            print(f"[{idx}/{len(files)}] {f.name}: вход {in_lines}, уникальных {out_lines}, дубликатов {duplicates}")

    print(f"Готово: {output_path}")
    print(f"Итого: вход {total_in_lines}, уникальных записано {total_out_lines}, удалено дубликатов {total_duplicates}")
    if dedup == "json":
        print("Дедуп по JSON: пробелы и порядок ключей игнорируются (канонизация JSON).")
    else:
        print("Дедуп по строкам: учитывается точное совпадение содержимого (без учёта перевода строки).")

def parse_args():
    parser = argparse.ArgumentParser(
        prog="combine",
        description="Склейка *.jsonl.gz в один .jsonl.gz с удалением дубликатов",
    )
    parser.add_argument("-i", "--input_dir", type=Path, required=True, help="Папка с файлами")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Путь к выходному .jsonl.gz")
    parser.add_argument("--pattern", default="*.jsonl.gz", help="Маска файлов (по умолчанию *.jsonl.gz)")
    parser.add_argument("--recursive", action="store_true", help="Искать рекурсивно")
    parser.add_argument("--dedup", choices=["line", "json"], default="line",
                        help="Как определять дубликаты: 'line' (по строкам) или 'json' (по канонизированному JSON)")
    return parser.parse_args()


@cli_main
def main():
    args = parse_args()
    merge_jsonl_gz(args.input_dir, args.output, args.pattern, args.recursive, dedup=args.dedup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
