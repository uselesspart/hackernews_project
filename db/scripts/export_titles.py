import argparse

from db import session_scope
from db.queries import iter_story_titles
from utils.cli import cli_main
from utils.io import EXPORT_FORMATS, write_records


def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Выгрузка заголовков Story из БД в файл (txt/csv/jsonl)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--out", required=True, help="Путь к выходному файлу (например, samples/titles.txt)")
    p.add_argument("--format", choices=EXPORT_FORMATS, default="txt", help="Формат выхода (по умолчанию txt)")
    p.add_argument("--limit", type=int, default=None, help="Ограничение числа записей")
    p.add_argument("--keep-deleted", action="store_true", help="Не фильтровать deleted/dead")
    p.add_argument("--with-techs-only", action="store_true",
                   help="Только истории, связанные хотя бы с одной технологией (после classify_tech)")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    with session_scope(args.db) as session:
        rows = iter_story_titles(session, keep_deleted=args.keep_deleted, limit=args.limit,
                                 with_techs_only=args.with_techs_only)
        write_records(args.out, args.format, ["id", "title"], rows, txt=lambda r: r[1])
    print(f"Готово: экспорт заголовков в {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
