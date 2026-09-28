import argparse
import json
from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from random import Random
from typing import Any

from utils.cli import cli_main
from utils.io import iter_jsonl


def parse_sets(values: list[str]) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    for v in values:
        if ":" not in v:
            raise ValueError(f"Invalid --sets entry '{v}', expected name:count")
        name, cnt = v.split(":", 1)
        name = name.strip()
        try:
            n = int(cnt)
        except ValueError:
            raise ValueError(f"Invalid count in --sets entry '{v}'") from None
        if not name or n < 1:
            raise ValueError(f"Invalid --sets entry '{v}'")
        result.append((name, n))
    return result


def reservoir_sample(stream: Iterator[dict[str, Any]],
                     k: int,
                     rnd: Random) -> list[dict[str, Any]]:
    res: list[dict[str, Any]] = []
    for t, item in enumerate(stream, start=1):
        if len(res) < k:
            res.append(item)
        else:
            j = rnd.randint(1, t)
            if j <= k:
                res[j - 1] = item
    return res


def filter_stream(stream: Iterator[dict[str, Any]],
                  types: list[str] | None = None,
                  skip_deleted: bool = True,
                  unique_by_id: bool = True) -> Iterator[dict[str, Any]]:
    seen_ids: set[int] = set()
    for obj in stream:
        if types and obj.get("type") not in types:
            continue
        if skip_deleted and (obj.get("deleted") or obj.get("dead")):
            continue
        if unique_by_id:
            _id = obj.get("id")
            if _id is None:
                continue
            if _id in seen_ids:
                continue
            seen_ids.add(_id)
        yield obj


def write_sets_files(root_out: str | Path,
                     sets: list[tuple[str, int]],
                     items: list[dict[str, Any]],
                     fmt: str = "json",
                     pretty: bool = True) -> None:
    out_root = Path(root_out)
    out_root.mkdir(parents=True, exist_ok=True)

    idx = 0
    for set_name, count in sets:
        if idx + count > len(items):
            raise RuntimeError("Not enough sampled items to fill all sets")

        slice_items = items[idx:idx + count]
        idx += count

        suffix = ".jsonl" if fmt == "jsonl" else ".json"
        out_path = out_root / f"{set_name}{suffix}"

        with open(out_path, "w", encoding="utf-8") as f:
            if fmt == "jsonl":
                for obj in slice_items:
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            else:
                json.dump(
                    slice_items,
                    f,
                    ensure_ascii=False,
                    indent=(2 if pretty else None),
                    sort_keys=pretty,
                )
                f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create_samples",
        description="Создание демонстрационных сэмплов из JSONL(.gz), один файл на набор"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Путь к исходному файлу JSONL или JSONL.GZ (например, raw_data/44_45Mil.jsonl.gz)"
    )
    parser.add_argument(
        "-o", "--out-root",
        default="samples",
        help="Корневая папка для файлов наборов (по умолчанию 'samples')"
    )
    parser.add_argument(
        "--sets",
        required=True,
        nargs="+",
        help="Списки наборов вида name:count (например: small_set_01:10 small_set_02:20)"
    )
    parser.add_argument(
        "--filter-types",
        nargs="*",
        default=None,
        help="Фильтр по типам объектов (например: story comment)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Сид генератора случайных чисел (по умолчанию 42)"
    )
    parser.add_argument(
        "--mode",
        choices=["random", "head"],
        default="random",
        help="Способ выборки: random (reservoir) или head (первые K) (по умолчанию random)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "jsonl"],
        default="json",
        help="Формат выходных файлов: json (массив) или jsonl (строка на объект)"
    )
    parser.add_argument(
        "--no-pretty",
        action="store_true",
        help="Не форматировать JSON (только для --format json)"
    )
    parser.add_argument(
        "--keep-deleted",
        action="store_true",
        help="Не отфильтровывать deleted/dead элементы"
    )
    return parser.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    sets = parse_sets(args.sets)
    total_k = sum(c for _, c in sets)

    stream = filter_stream(
        iter_jsonl(args.input),
        types=args.filter_types,
        skip_deleted=not args.keep_deleted,
        unique_by_id=True,
    )
    if args.mode == "head":
        sampled = list(islice(stream, total_k))
    else:
        sampled = reservoir_sample(stream, total_k, Random(args.seed))

    if len(sampled) < total_k:
        raise RuntimeError(
            f"Недостаточно элементов после фильтров: нужно {total_k}, получено {len(sampled)}"
        )

    write_sets_files(args.out_root, sets, sampled, fmt=args.format, pretty=not args.no_pretty)

    suffix = ".jsonl" if args.format == "jsonl" else ".json"
    print("Готово:")
    for name, cnt in sets:
        print(f"- {args.out_root}/{name}{suffix} ({cnt} объектов)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
