import argparse
import csv
import json
from itertools import groupby
from pathlib import Path
from sqlalchemy import and_, select

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
    """
    Строки (story_id, title, comment_text), упорядоченные по истории и комментарию.
    Склейка в Python, а не через string_agg/group_concat: порядок внутри агрегата
    в SQL не гарантирован и менялся от плана запроса, а clean_text на склеенной строке
    мог вырезать "<...>" через границу двух комментариев.
    """
    stories = select(Story.id, Story.title).where(Story.title.isnot(None), Story.title != "")
    if not keep_deleted:
        stories = stories.where(is_alive(Story))
    if limit:
        stories = stories.order_by(Story.id).limit(limit)
    stories = stories.subquery()

    join_cond = Comment.parent == stories.c.id
    if not keep_deleted:
        join_cond = and_(join_cond, is_alive(Comment))

    return (
        select(stories.c.id, stories.c.title, Comment.text)
        .outerjoin(Comment, join_cond)
        .order_by(stories.c.id, Comment.id)
        .execution_options(stream_results=True, yield_per=10_000)
    )


def iter_contexts(rows):
    """Группирует упорядоченные строки по истории: (story_id, title, [очищенные комментарии])."""
    for (story_id, title), group in groupby(rows, key=lambda r: (r[0], r[1])):
        comments = [c for c in (clean_text(text) for _, _, text in group) if c]
        yield story_id, clean_text(title), comments

def main() -> int:

    args = parse_args()
    try:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with session_scope(args.db) as session, \
                open(out_path, "w", encoding="utf-8", newline="") as f:
            rows = session.execute(build_stmt(args.keep_deleted, args.limit)).tuples()
            writer = csv.writer(f) if args.format == "csv" else None
            if writer:
                writer.writerow(["id", "title", "context"])

            for story_id, title, comments in iter_contexts(rows):
                context = " ".join(comments)
                if args.format == "txt":
                    f.write(" ".join(p for p in (title, *comments) if p) + "\n")
                elif args.format == "csv":
                    writer.writerow([story_id, title, context])
                else:
                    f.write(json.dumps({"id": story_id, "title": title, "context": context},
                                       ensure_ascii=False) + "\n")

        print(f"Готово: экспорт заголовков и комментариев в {out_path}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
