import argparse

from db import session_scope
from db.queries import iter_tech_names
from utils.cli import cli_main
from utils.io import EXPORT_FORMATS, write_records


def parse_args():
    p = argparse.ArgumentParser(
        prog="export_tech_names",
        description="Выгрузка технологий Tech из БД в файл (txt/csv/jsonl)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--out", required=True, help="Путь к выходному файлу (например, tech_names.txt)")
    p.add_argument("--format", choices=EXPORT_FORMATS, default="txt", help="Формат выхода (по умолчанию txt)")
    p.add_argument("--limit", type=int, default=None, help="Ограничение числа записей")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    with session_scope(args.db) as session:
        rows = iter_tech_names(session, limit=args.limit)
        write_records(args.out, args.format, ["id", "name"], rows, txt=lambda r: r[1])
    print(f"Готово: экспорт технологий в {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
