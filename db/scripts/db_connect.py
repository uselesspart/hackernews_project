import argparse
from sqlalchemy import inspect

from ..session import get_engine

def parse_args():
    p = argparse.ArgumentParser(
        prog="db_connect",
        description="Проверка подключения к БД: диалект, таблицы, базовые счетчики"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    try:
        engine = get_engine(args.db)
        insp = inspect(engine)
        tables = insp.get_table_names()
        print(f"Подключение OK: {args.db}")
        print(f"Диалект: {engine.dialect.name}")
        print(f"Таблицы: {', '.join(tables) if tables else '(нет)'}")

        # Пробуем считать записи в stories/comments, если таблицы существуют
        with engine.connect() as conn:
            for t in ("stories", "comments"):
                if t in tables:
                    count = conn.execute(f"SELECT COUNT(*) FROM {t}").scalar_one()
                    print(f"- {t}: {count} записей")
        return 0
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())