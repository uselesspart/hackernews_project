import argparse
import csv
from pathlib import Path

from sqlalchemy import func, select

from db import session_scope
from db.models import Story, Tech, story_tech
from utils.cli import cli_main

FIELDS = ["id", "title", "score", "time", "descendants", "techs_count", "tech_names"]


def build_stmt():
    tech_agg = (
        select(
            story_tech.c.story_id.label("story_id"),
            func.count(story_tech.c.tech_id).label("techs_count"),
            # Пара (story_id, tech_id) — первичный ключ, дубликатов нет, DISTINCT не нужен.
            # aggregate_strings работает и в SQLite/MySQL (group_concat), и в Postgres (string_agg).
            func.aggregate_strings(Tech.name, "|").label("tech_names"),
        )
        .select_from(story_tech.join(Tech, Tech.id == story_tech.c.tech_id))
        .group_by(story_tech.c.story_id)
    ).subquery()

    return (
        select(
            Story.id,
            Story.title,
            Story.score,
            Story.time,
            Story.descendants,
            func.coalesce(tech_agg.c.techs_count, 0),
            func.coalesce(tech_agg.c.tech_names, ""),
        )
        .outerjoin(tech_agg, tech_agg.c.story_id == Story.id)
        .order_by(Story.descendants.desc(), Story.id.asc())
    )


def parse_args():
    p = argparse.ArgumentParser(
        prog="export_stories_meta",
        description="Выгрузка метаданных статей (оценка, время, число комментариев, технологии) в CSV"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--output", "--out", dest="output", required=True,
                   help="Путь к выходному CSV (например, artifacts/meta.csv)")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with session_scope(args.db) as session, open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for story_id, title, score, time, descendants, techs_count, tech_names in session.execute(build_stmt()):
            writer.writerow([story_id, title, score, time.isoformat() if time else "",
                             descendants, techs_count, tech_names])

    print(f"Готово: экспорт данных в {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
