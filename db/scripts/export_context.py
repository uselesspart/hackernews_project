import argparse
from itertools import groupby

from sqlalchemy import and_, select

from db import session_scope
from db.models import Comment, Story
from db.queries import has_techs, is_alive
from utils.clean_text import clean_text
from utils.cli import cli_main
from utils.io import EXPORT_FORMATS, write_records


def parse_args():
    p = argparse.ArgumentParser(
        prog="export_context",
        description="Выгрузка заголовков Story с комментариями Comment из БД в файл (txt/csv/jsonl)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--out", required=True, help="Путь к выходному файлу (например, samples/titles.txt)")
    p.add_argument("--format", choices=EXPORT_FORMATS, default="txt", help="Формат выхода (по умолчанию txt)")
    p.add_argument("--limit", type=int, default=None, help="Ограничение числа записей")
    p.add_argument("--keep-deleted", action="store_true", help="Не фильтровать deleted/dead")
    p.add_argument("--with-techs-only", action="store_true",
                   help="Только истории, связанные хотя бы с одной технологией (после classify_tech)")
    return p.parse_args()


def build_stmt(keep_deleted: bool, limit: int | None, with_techs_only: bool = False):
    """
    Строки (story_id, title, comment_text), упорядоченные по истории и комментарию.
    Склейка в Python, а не через string_agg/group_concat: порядок внутри агрегата
    в SQL не гарантирован и менялся от плана запроса, а clean_text на склеенной строке
    мог вырезать "<...>" через границу двух комментариев.
    """
    stories = select(Story.id, Story.title).where(Story.title.isnot(None), Story.title != "")
    if not keep_deleted:
        stories = stories.where(is_alive(Story))
    if with_techs_only:
        stories = stories.where(has_techs())
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

@cli_main
def main() -> int:
    args = parse_args()
    with session_scope(args.db) as session:
        rows = session.execute(build_stmt(args.keep_deleted, args.limit, args.with_techs_only)).tuples()
        records = ((story_id, title, " ".join(comments)) for story_id, title, comments in iter_contexts(rows))
        write_records(args.out, args.format, ["id", "title", "context"], records,
                      txt=lambda r: " ".join(p for p in (r[1], r[2]) if p))
    print(f"Готово: экспорт заголовков и комментариев в {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
