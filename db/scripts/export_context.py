import argparse
from pathlib import Path
from sqlalchemy import select, func

from db.models import Comment, Story
from db import session_scope
from utils.clean_text import clean_text

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Выгрузка заголовков Story с комментариями Comment из БД в файл (txt/csv/jsonl)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--out", required=True, help="Путь к выходному файлу (например, samples/titles.txt)")
    p.add_argument("--format", choices=["txt", "csv", "jsonl"], default="txt", help="Формат выхода (по умолчанию txt)")
    p.add_argument("--limit", type=int, default=None, help="Ограничение числа записей")
    p.add_argument("--keep-deleted", action="store_true", help="Не фильтровать deleted/dead")
    return p.parse_args()

def main() -> int:

    args = parse_args()
    try:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with session_scope(args.db) as session:
            if args.format == "txt":
                with open(out_path, "w", encoding="utf-8") as f:
                    stmt = (
                    select(
                        Story.id,
                        Story.title,
                        func.coalesce(func.string_agg(Comment.text, ' '), '')
                    )
                    .outerjoin(Comment, Comment.parent == Story.id)
                    .group_by(Story.id, Story.title)
                    .execution_options(stream_results=True)
                )
                    result = session.execute(stmt).tuples()
                    for batch in result.partitions(10_000):
                        lines = [f"{title} {context}\n" for _, title, context in batch]
                        clean_lines = [clean_text(line) + "\n" for line in lines]
                        f.writelines(clean_lines)
                        print(lines)
            elif args.format == "csv":
                pass
            else:
                pass

        print(f"Готово: экспорт заголовков и комментариев в {out_path}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
