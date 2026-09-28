import argparse
from pathlib import Path

from analytics.embeddings.title_embedder import save_token_matrix_jsonl_gz
from utils.cli import cli_main


def parse_args():
    ap = argparse.ArgumentParser(
        prog="sentences_to_vectors",
        description="Преобразует файл предложений/лемм (TXT) в JSONL.GZ с токенами для обучения."
    )
    ap.add_argument("-i", "--input", required=True,
                    help="Путь к входному TXT (по одной строке = заголовок/леммы/токены)")
    ap.add_argument("-o", "--output", required=True, help="Путь к выходному файлу")
    return ap.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Файл не найден: {in_path}")
    save_token_matrix_jsonl_gz(in_path, args.output)
    print(f"Готово: токены сгенерированы из {in_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
