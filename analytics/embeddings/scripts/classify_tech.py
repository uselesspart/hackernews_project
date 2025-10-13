from __future__ import annotations
from pathlib import Path
import re
from typing import Dict, List, Iterable, Set
import argparse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db import session_scope
# поправьте импорт моделей под ваш проект
from db.models import Story, Tech
# и импорт заранее собранных паттернов
from analytics.embeddings.patterns import PATTERNS  # Dict[str, List[re.Pattern]]



def ensure_techs(session: Session, tech_names: Iterable[str]) -> Dict[str, Tech]:
    """Создаёт отсутствующие технологии, возвращает name -> Tech."""
    existing: Dict[str, Tech] = {
        t.name: t for t in session.execute(select(Tech)).scalars().all()
    }
    to_create = [Tech(name=name) for name in tech_names if name not in existing]
    if to_create:
        session.add_all(to_create)
        session.commit()
        for t in to_create:
            existing[t.name] = t
    return existing


def match_techs(title: str, patterns: Dict[str, List[re.Pattern]]) -> Set[str]:
    """Возвращает множество имён технологий, найденных в заголовке."""
    if not title:
        return set()
    text = title.lower()
    hits: Set[str] = set()
    for tech, pats in patterns.items():
        for pat in pats:
            if pat.search(text):
                hits.add(tech)
                break
    return hits


def classify_stories(session: Session,
                     patterns: Dict[str, List[re.Pattern]] = PATTERNS,
                     batch_size: int = 1000,
                     dry_run: bool = False) -> int:
    """
    Проставляет связи Story↔Tech по заголовкам. Таблицы и движок — уже существуют.
    Возвращает количество обновлённых историй.
    """
    tech_by_name = ensure_techs(session, patterns.keys())

    updated = 0
    stmt = select(Story).options(selectinload(Story.techs)).execution_options(yield_per=batch_size)

    for story in session.execute(stmt).scalars():
        found = match_techs(story.title or "", patterns)
        if not found:
            continue

        existing_names = {t.name for t in story.techs}
        to_add = [name for name in found if name not in existing_names]
        if not to_add:
            continue

        if dry_run:
            print(f"Story {story.id}: +{to_add}")
            updated += 1
            continue

        for name in to_add:
            story.techs.append(tech_by_name[name])

        updated += 1
        if updated % batch_size == 0:
            session.commit()

    if not dry_run:
        session.commit()

    return updated

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Выгрузка заголовков Story из БД в файл (txt/csv/jsonl)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    try:
        with session_scope(args.db) as session:
            changed = classify_stories(session, dry_run=False)
            print("Обновлено историй:", changed)
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
