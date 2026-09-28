import argparse
import csv
import json
from pathlib import Path
from sqlalchemy import and_, select, func

from db.models import Comment, Story
from db import session_scope
from db.queries import is_alive
from utils.clean_text import clean_text

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_context",
        description="Выгрузка заголовков Story с комментариями Comment из БД в файл (txt/csv/jsonl)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--out", required=True, help="Путь к выходному файлу (например, samples/titles.txt)")
    p.add_argument("--format", choices=["txt", "csv", "jsonl"], default="txt", help="Формат выхода (по умолчанию txt)")
    p.add_argument("--limit", type=int, default=None, help="Ограничение числа записей")
    p.add_argument("--keep-deleted", action="store_true", help="Не фильтровать deleted/dead")
    return p.parse_args()

def build_stmt(keep_deleted: bool, limit: int | None):
    join_cond = Comment.parent == Story.id
    if not keep_deleted:
        join_cond = and_(join_cond, is_alive(Comment))

    stmt = (
        select(
            Story.id,
            Story.title,
            # aggregate_strings компилируется в string_agg / group_concat в зависимости от СУБД
            func.coalesce(func.aggregate_strings(Comment.text, " "), ""),
        )
        .outerjoin(Comment, join_cond)
        .where(Story.title.isnot(None), Story.title != "")
        .group_by(Story.id, Story.title)
        .order_by(Story.id)
        .execution_options(stream_results=True)
    )
    if not keep_deleted:
        stmt = stmt.where(is_alive(Story))
    if limit:
        stmt = stmt.limit(limit)
    return stmt

def main() -> int:

    args = parse_args()
    try:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with session_scope(args.db) as session, \
                open(out_path, "w", encoding="utf-8", newline="") as f:
            result = session.execute(build_stmt(args.keep_deleted, args.limit)).tuples()
            writer = csv.writer(f) if args.format == "csv" else None
            if writer:
                writer.writerow(["id", "title", "context"])

            for batch in result.partitions(10_000):
                for story_id, title, context in batch:
                    if args.format == "txt":
                        f.write(clean_text(f"{title} {context}") + "\n")
                    elif args.format == "csv":
                        writer.writerow([story_id, clean_text(title), clean_text(context)])
                    else:
                        f.write(json.dumps(
                            {"id": story_id, "title": clean_text(title), "context": clean_text(context)},
                            ensure_ascii=False,
                        ) + "\n")

        print(f"Готово: экспорт заголовков и комментариев в {out_path}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
