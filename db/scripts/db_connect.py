import argparse

from sqlalchemy import func, inspect, select, table

from db.session import get_engine
from utils.cli import cli_main


def parse_args():
    p = argparse.ArgumentParser(
        prog="db_connect",
        description="Проверка подключения к БД: диалект, таблицы, базовые счетчики"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    return p.parse_args()

@cli_main
def main() -> int:
    args = parse_args()
    engine = get_engine(args.db)
    tables = inspect(engine).get_table_names()
    print(f"Подключение OK: {args.db}")
    print(f"Диалект: {engine.dialect.name}")
    print(f"Таблицы: {', '.join(tables) if tables else '(нет)'}")
    with engine.connect() as conn:
        for t in ("story", "comment", "tech", "story_tech"):
            if t in tables:
                count = conn.execute(select(func.count()).select_from(table(t))).scalar_one()
                print(f"- {t}: {count} записей")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
