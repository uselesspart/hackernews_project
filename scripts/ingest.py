import argparse
import sys
from pathlib import Path
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hackernews_handler import HNHandler

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="hn_ingest",
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

def main() -> int:
    args = parse_args()

    try:
        engine = create_engine(args.db, echo=args.echo)
    except Exception as e:
        print(f"Ошибка создания engine для '{args.db}': {e}", file=sys.stderr)
        return 1

    handler = HNHandler(engine, batch_size=args.batch_size)

    total_stories = 0
    total_comments = 0

    for path in args.input:
        try:
            print(f"Импорт из файла: {path}")
            counts = handler.ingest_from_path(path)
            print(f"Готово: stories={counts['stories']}, comments={counts['comments']}")
            total_stories += counts["stories"]
            total_comments += counts["comments"]
        except FileNotFoundError as e:
            print(f"Файл не найден: {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"Ошибка импорта из '{path}': {e}", file=sys.stderr)
            return 3

    print(f"Всего загружено: stories={total_stories}, comments={total_comments}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
