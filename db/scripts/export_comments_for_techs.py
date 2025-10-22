import re
import json
import argparse
from pathlib import Path
from db.models import Comment, Story, Tech, story_tech
from db import session_scope
from sqlalchemy import select, func

def all_thread_comments_for_tech(session: session_scope, tech_id: int, since=None):
    base_sel = (
        select(
            Comment.id.label("id"),
            Comment.text.label("text"),
            Comment.parent.label("parent"),
            Story.id.label("story_id"),
        )
        .join(Story, Comment.parent == Story.id)
        .join(story_tech, story_tech.c.story_id == Story.id)
        .where(story_tech.c.tech_id == tech_id)
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
        )
        .join(thread_cte, Comment.parent == thread_cte.c.id)
    )

    thread_cte = thread_cte.union_all(replies_sel)

    stmt = (
        select(thread_cte.c.text)
        .where(
            thread_cte.c.text.isnot(None),
            thread_cte.c.text != "[dead]",
        )
    )

    return [t for (t,) in session.execute(stmt).all()]

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Отрисовка карты отношений между словами"
    )
    p.add_argument("-d", "--db", required=True, help="Путь к базе данных")
    p.add_argument("-m", "--minimum", type=int, default=100, help="Минимальное число статей для выгрузки")
    p.add_argument("-o", "--output", required=True, help="Путь к выходной папке")
    p.add_argument("-f", "--filetype", default="txt", help="Формат выходного файла")
    return p.parse_args()

def main():
    try:
        args = parse_args()

        with session_scope(args.db) as session:
            story_filter = []
            min_stories = args.minimum

            stmt = (
                select(Tech.id, Tech.name, func.count(Story.id).label("stories"))
                .select_from(Tech)
                .join(Tech.stories, isouter=True)
                .where(*story_filter)
                .group_by(Tech.id, Tech.name)
                .having(func.count(Story.id) >= min_stories)
                .order_by(func.count(Story.id).desc())
            )

            techs = session.execute(stmt).all()

            if args.filetype == "json":
                out_path = Path(args.output)
                out_path = out_path + "comments.json"
                result = []
                for tech_id, tech_name, _cnt in techs:
                    cmts = all_thread_comments_for_tech(session=session, tech_id=tech_id)
                    cmts = [c for c in cmts if c]
                    result.append({
                        "tech_id": tech_id,
                        "tech": tech_name,
                        "comments": cmts,
                    })
                with out_path.open("w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            elif args.filetype == "txt":
                out_dir = Path(args.output)
                out_dir.mkdir(parents=True, exist_ok=True)

                for tech_id, tech_name, _cnt in techs:
                    cmts = all_thread_comments_for_tech(session=session, tech_id=tech_id)
                    cmts = [c.strip() for c in cmts if c and c.strip()]
                    if not cmts:
                        continue
                    safe_name = re.sub(r"[^\w.-]+", "_", tech_name.strip())
                    file_path = out_dir / f"{safe_name}_{tech_id}.txt"
                    with file_path.open("w", encoding="utf-8") as f:
                        f.write("\n".join(cmts) + ("\n" if cmts else ""))
                print(f'Готово: экспорт комментариев в {out_dir}')
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
