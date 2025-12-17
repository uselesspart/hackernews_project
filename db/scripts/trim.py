import argparse
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from db import session_scope
from db.models import Story

def delete_stories_without_techs(session: Session, dry_run: bool = False) -> int:
    # Посчитать количество историй без технологий
    count_stmt = select(func.count(Story.id)).where(~Story.techs.any())
    total = session.execute(count_stmt).scalar_one()

    if dry_run:
        print(f"Нашлось историй без технологий: {total}. Ничего не удалено (dry-run).")
        return 0

    # Массовое удаление
    del_stmt = delete(Story).where(~Story.techs.any())
    result = session.execute(del_stmt)

    # Количество удаленных строк (может быть None в некоторых драйверах)
    deleted = result.rowcount or 0
    session.commit()

    print(f"Удалено историй: {deleted}")
    return deleted

def parse_args():
    p = argparse.ArgumentParser(
        prog="delete_stories_without_techs",
        description="Удаление всех Story без связанных Tech из БД"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("--dry-run", action="store_true", help="Только показать количество, без удаления")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    try:
        with session_scope(args.db) as session:
            delete_stories_without_techs(session, dry_run=args.dry_run)
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
