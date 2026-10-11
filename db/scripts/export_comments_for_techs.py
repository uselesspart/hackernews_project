import argparse
import json
import re
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from db import session_scope
from db.models import Comment, Story, Tech, story_tech
from db.queries import is_alive
from utils.cli import cli_main


def thread_comments_for_tech(session: Session, tech_id: int, since=None) -> list[tuple[int, str]]:
    """(id, текст) всех комментариев веток к статьям о технологии, по возрастанию id."""
    base_sel = (
        select(
            Comment.id.label("id"),
            Comment.text.label("text"),
            Comment.parent.label("parent"),
            Story.id.label("story_id"),
            Comment.dead.label("dead"),
            Comment.deleted.label("deleted"),
        )
        .join(Story, Comment.parent == Story.id)
        .join(story_tech, story_tech.c.story_id == Story.id)
        .where(story_tech.c.tech_id == tech_id, is_alive(Story))
    )
    if since is not None:
        base_sel = base_sel.where(Story.time >= since)

    thread_cte = base_sel.cte(name="thread_comments", recursive=True)

    replies_sel = (
        select(
            Comment.id,
            Comment.text,
            Comment.parent,
            thread_cte.c.story_id,
            Comment.dead,
            Comment.deleted,
        )
        .join(thread_cte, Comment.parent == thread_cte.c.id)
    )

    thread_cte = thread_cte.union_all(replies_sel)

    # Ответы на dead/deleted комментарии остаются в выборке — отбрасываются только сами помеченные
    stmt = (
        select(thread_cte.c.id, thread_cte.c.text)
        .where(
            thread_cte.c.text.isnot(None),
            thread_cte.c.text != "[dead]",
            or_(thread_cte.c.dead.is_(None), thread_cte.c.dead.is_(False)),
            or_(thread_cte.c.deleted.is_(None), thread_cte.c.deleted.is_(False)),
        )
        .order_by(thread_cte.c.id)
    )
    return [(cid, text) for cid, text in session.execute(stmt).all()]


def all_thread_comments_for_tech(session: Session, tech_id: int, since=None) -> list[str]:
    return [text for _, text in thread_comments_for_tech(session, tech_id, since)]

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_comments_for_techs",
        description="Выгрузка комментариев к статьям о каждой технологии"
    )
    p.add_argument("-d", "--db", required=True, help="Путь к базе данных")
    p.add_argument("-m", "--minimum", type=int, default=100, help="Минимальное число статей для выгрузки")
    p.add_argument("-o", "--output", required=True, help="Путь к выходной папке")
    p.add_argument("-f", "--filetype", choices=["txt", "json"], default="txt", help="Формат выходного файла")
    return p.parse_args()

def techs_with_min_stories(session: Session, minimum: int):
    """(id, name) технологий, у которых не меньше minimum историй, по убыванию числа историй."""
    n_stories = func.count(Story.id)
    stmt = (
        select(Tech.id, Tech.name)
        .select_from(Tech)
        .join(Tech.stories, isouter=True)
        .group_by(Tech.id, Tech.name)
        .having(n_stories >= minimum)
        .order_by(n_stories.desc())
    )
    return session.execute(stmt).all()


@cli_main
def main():
    args = parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    with session_scope(args.db) as session:
        techs = techs_with_min_stories(session, args.minimum)
        if args.filetype == "json":
            result = [
                {"tech_id": tech_id, "tech": name,
                 "comments": [c for c in all_thread_comments_for_tech(session, tech_id) if c]}
                for tech_id, name in techs
            ]
            with (out_dir / "comments.json").open("w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        else:
            for tech_id, name in techs:
                comments = [c.strip() for c in all_thread_comments_for_tech(session, tech_id) if c and c.strip()]
                if comments:
                    safe_name = re.sub(r"[^\w.-]+", "_", name.strip())
                    (out_dir / f"{safe_name}_{tech_id}.txt").write_text(
                        "\n".join(comments) + "\n", encoding="utf-8", newline="\n")
    print(f"Готово: экспорт комментариев в {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
