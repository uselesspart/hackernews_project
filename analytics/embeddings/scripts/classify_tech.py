import re
from typing import Dict, List, Iterable, Set
import argparse
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from db import session_scope
from db.models import Story, Tech, story_tech
from analytics.embeddings.patterns import COMPILED_PATTERNS, PATTERNS, compile_patterns

def ensure_techs(session: Session, tech_names: Iterable[str]) -> Dict[str, Tech]:
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


def _compiled(patterns: Dict[str, List[re.Pattern]]) -> Dict[str, re.Pattern]:
    return COMPILED_PATTERNS if patterns is PATTERNS else compile_patterns(patterns)


def match_techs(title: str, patterns: Dict[str, List[re.Pattern]]) -> Set[str]:
    if not title:
        return set()
    return {tech for tech, pat in _compiled(patterns).items() if pat.search(title)}


def classify_stories(session: Session,
                     patterns: Dict[str, List[re.Pattern]] = PATTERNS,
                     batch_size: int = 1000,
                     dry_run: bool = False) -> int:
    tech_id_by_name = {name: t.id for name, t in ensure_techs(session, patterns.keys()).items()}
    compiled = _compiled(patterns)

    existing: Dict[int, Set[int]] = {}
    for story_id, tech_id in session.execute(select(story_tech.c.story_id, story_tech.c.tech_id)):
        existing.setdefault(story_id, set()).add(tech_id)

    updated = 0
    last_id = None
    while True:
        # Постранично по id: не держим открытый курсор чтения, пока пишем в ту же БД
        stmt = select(Story.id, Story.title).order_by(Story.id).limit(batch_size)
        if last_id is not None:
            stmt = stmt.where(Story.id > last_id)
        rows = session.execute(stmt).all()
        if not rows:
            break
        last_id = rows[-1].id

        links = []
        for story_id, title in rows:
            if not title:
                continue
            have = existing.get(story_id, set())
            new_ids = [tech_id_by_name[tech] for tech, pat in compiled.items()
                       if pat.search(title) and tech_id_by_name[tech] not in have]
            if not new_ids:
                continue
            updated += 1
            if dry_run:
                names = [name for name, tid in tech_id_by_name.items() if tid in new_ids]
                print(f"Story {story_id}: +{names}")
                continue
            links.extend({"story_id": story_id, "tech_id": tid} for tid in new_ids)

        if links:
            session.execute(insert(story_tech), links)
            session.commit()

    return updated

def parse_args():
    p = argparse.ArgumentParser(
        prog="classify_tech",
        description="Привязка историй к технологиям по шаблонам из patterns.py"
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
