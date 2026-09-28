import argparse
import sys

from db.session import get_engine
from hackernews_handler import HNHandler
from utils.cli import cli_main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ingest",
        description="Загрузка Hacker News JSONL(.gz) в базу данных"
    )
    parser.add_argument(
        "-d", "--db",
        required=True,
        help="Строка подключения SQLAlchemy, например: sqlite:///test.db"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        nargs="+",
        help="Путь(и) к файлам JSONL или JSONL.GZ с сырыми данными"
    )
    parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=1000,
        help="Размер пакетной вставки (по умолчанию 1000)"
    )
    parser.add_argument(
        "--echo",
        action="store_true",
        help="Включить вывод SQL от SQLAlchemy"
    )
    return parser.parse_args()

@cli_main
def main() -> int:
    args = parse_args()
    handler = HNHandler(get_engine(args.db, echo=args.echo), batch_size=args.batch_size)

    total = {"stories": 0, "comments": 0}
    for path in args.input:
        print(f"Импорт из файла: {path}")
        try:
            counts = handler.ingest_from_path(path)
        except FileNotFoundError as e:
            print(f"Файл не найден: {e}", file=sys.stderr)
            return 2
        print(f"Готово: stories={counts['stories']}, comments={counts['comments']}")
        total["stories"] += counts["stories"]
        total["comments"] += counts["comments"]

    print(f"Всего загружено: stories={total['stories']}, comments={total['comments']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
