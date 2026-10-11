"""
Выборка комментариев для ручной разметки тональности (PLAN 2.5): по N на технологию,
поровну из реплик с упоминанием технологии и без него. Результат размечается вручную
и подаётся в analytics.embeddings.scripts.evaluate_sentiment.
"""
import argparse
import csv
from pathlib import Path
from random import Random

from sqlalchemy import func, select

from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.sentiment import mention_text, split_comment
from db import session_scope
from db.models import Story, Tech, story_tech
from db.queries import is_alive, iter_tech_thread_comments, story_tech_keys
from utils.cli import cli_main

FIELDS = ["tech", "comment_id", "hn_url", "mentions", "text", "label_comment", "label_tech"]
HN_ITEM_URL = "https://news.ycombinator.com/item?id={}"


def top_techs(session, n: int) -> list[str]:
    n_stories = func.count(Story.id)
    stmt = (select(Tech.name).join(story_tech, story_tech.c.tech_id == Tech.id)
            .join(Story, Story.id == story_tech.c.story_id).where(is_alive(Story))
            .group_by(Tech.name).order_by(n_stories.desc(), Tech.name).limit(n))
    return list(session.scalars(stmt))


def sample_comments(session, techs: list[str], per_tech: int, seed: int) -> list[dict]:
    """По per_tech комментариев на технологию: половина с упоминанием, половина без (если хватает)."""
    wanted = set(techs)
    story_keys = story_tech_keys(session)
    pools: dict[tuple[str, bool], list[tuple[int, str]]] = {(t, m): [] for t in techs for m in (True, False)}
    for cid, raw, story_id in iter_tech_thread_comments(session):
        keys = wanted.intersection(story_keys.get(story_id, ()))
        if not keys:
            continue
        parts = split_comment(raw)
        if not parts.prose:
            continue
        for key in keys:
            pattern = COMPILED_PATTERNS.get(key)
            mentions = pattern is not None and mention_text(parts, pattern) is not None
            pools[(key, mentions)].append((cid, parts.prose))

    rng = Random(seed)
    rows = []
    for tech in techs:
        with_m, without = pools[(tech, True)], pools[(tech, False)]
        # Половина с упоминанием; если реплик без упоминания мало — добираем репликами с ним, и наоборот
        k_with = min(len(with_m), max(per_tech - per_tech // 2, per_tech - len(without)))
        k_without = min(len(without), per_tech - k_with)
        for mentions, pool, k in ((True, with_m, k_with), (False, without, k_without)):
            for cid, text in sorted(rng.sample(pool, k)):
                rows.append({"tech": tech, "comment_id": cid, "hn_url": HN_ITEM_URL.format(cid),
                             "mentions": int(mentions), "text": text, "label_comment": "", "label_tech": ""})
    return rows


def parse_args():
    p = argparse.ArgumentParser(
        prog="export_sentiment_sample",
        description="Выборка комментариев для ручной разметки тональности. Разметчик заполняет "
                    "label_comment (тон всего комментария: -1, 0, 1) и label_tech (отношение к технологии: "
                    "-1, 0, 1; пусто — о технологии ничего не сказано)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--output", required=True, help="Путь к CSV")
    p.add_argument("--techs", help="Технологии через запятую (по умолчанию — самые частые, см. --top)")
    p.add_argument("--top", type=int, default=6, help="Сколько самых частых технологий взять (по умолчанию 6)")
    p.add_argument("--per-tech", type=int, default=50, help="Комментариев на технологию (по умолчанию 50)")
    p.add_argument("--seed", type=int, default=42, help="Сид выборки (по умолчанию 42)")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with session_scope(args.db) as session:
        techs = [t.strip() for t in args.techs.split(",") if t.strip()] if args.techs else top_techs(session, args.top)
        rows = sample_comments(session, techs, args.per_tech, args.seed)
    # utf-8-sig: Excel открывает такой CSV без кракозябр
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Готово: {len(rows)} комментариев по технологиям {', '.join(techs)} → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
