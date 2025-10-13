from __future__ import annotations

import argparse
from pathlib import Path

from ..titles import TitleEmbedder


def parse_args():
    ap = argparse.ArgumentParser(
        prog="sentences_to_vectors",
        description="Преобразует файл предложений/лемм (TXT) в JSONL.GZ с токенами для обучения."
    )
    ap.add_argument(
        "-i", "--input",
        required=True,
        help="Путь к входному TXT (по одной строке = заголовок/леммы/токены)"
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    try:
        in_path = Path(args.input)
        if not in_path.exists():
            raise FileNotFoundError(f"Файл не найден: {in_path}")

        e = TitleEmbedder()
        e.sentences_to_vectors(in_path.as_posix())

        print(f"Готово: токены сгенерированы из {in_path}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())