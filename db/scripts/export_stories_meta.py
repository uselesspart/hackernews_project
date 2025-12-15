import argparse
import csv
from pathlib import Path
from sqlalchemy import select, func

from db.models import Story, Tech, story_tech
from db import session_scope

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Выгрузка метаданных статей в файл"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному файлу (например, samples/titles.txt)")
    return p.parse_args()

def main() -> int:

    args = parse_args()
    try:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with session_scope(args.db) as session:
            fieldnames = ["id", "title", "score", "time", "descendants", "techs_count", "tech_names"]
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                tech_agg = (
                select(
                    story_tech.c.story_id.label("story_id"),
                    func.count(func.distinct(story_tech.c.tech_id)).label("techs_count"),
                    func.group_concat(func.distinct(Tech.name)).label("tech_names_csv"),
                )
                .select_from(story_tech.join(Tech, Tech.id == story_tech.c.tech_id))
                .group_by(story_tech.c.story_id)
                ).subquery()

                stmt = (
                select(
                    Story.id,
                    Story.title,
                    Story.score,
                    Story.time,
                    Story.descendants,
                    func.coalesce(tech_agg.c.techs_count, 0).label("techs_count"),
                    tech_agg.c.tech_names_csv.label("tech_names_csv"),
                )
                .outerjoin(tech_agg, tech_agg.c.story_id == Story.id)
                .order_by(Story.descendants.desc(), Story.id.asc())
                )

                rows = session.execute(stmt).mappings().all()
                result = [
                    {
                        **row,
                        "tech_list": row["tech_names_csv"].split(",") if row["tech_names_csv"] else [],
                    }
                    for row in rows
                ]
                writer = csv.writer(f)
                writer.writerow(fieldnames)
                for r in result:
                    time_str = r["time"].isoformat() if r["time"] else ""
                    tech_names_str = "|".join(r["tech_list"])
                    writer.writerow([r["id"], r["title"], r["score"], time_str, r["descendants"], r["techs_count"], tech_names_str])

        print(f"Готово: экспорт данных в {out_path}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())