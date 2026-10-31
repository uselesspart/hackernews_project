"""Titles from the sentiment study, plus an optional random control sample."""

import argparse
import csv
from pathlib import Path
from random import Random

from db import session_scope
from db.queries import iter_story_titles
from utils.cli import cli_main

FIELDS = ["story_id", "hn_url", "title", "sample_source", "gold_techs", "annotation_source", "annotation_notes"]


def sample_titles(session, sentiment_rows: list[dict], random_count: int = 100, seed: int = 42) -> list[dict]:
    if random_count < 0:
        raise ValueError("random_count must be nonnegative")
    wanted = {int(r["story_id"]) for r in sentiment_rows}
    titles = list(iter_story_titles(session))
    available = {sid for sid, _ in titles}
    if missing := wanted - available:
        raise ValueError(f"Stories missing from database: {sorted(missing)}")
    controls = [(sid, title) for sid, title in titles if sid not in wanted]
    sampled = Random(seed).sample(controls, min(random_count, len(controls)))
    selected = {sid: (title, "sentiment") for sid, title in titles if sid in wanted}
    selected.update({sid: (title, "random_control") for sid, title in sampled})
    # No model predictions: annotations must not be copied from the classifier.
    return [{"story_id": sid, "hn_url": f"https://news.ycombinator.com/item?id={sid}", "title": title,
             "sample_source": source, "gold_techs": "", "annotation_source": "", "annotation_notes": ""}
            for sid, (title, source) in sorted(selected.items())]


def parse_args():
    p = argparse.ArgumentParser(description="Export titles for multilabel technology annotation")
    p.add_argument("-d", "--db", required=True)
    p.add_argument("--sentiment-sample", required=True, help="Sentiment CSV containing story_id")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--random-count", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    with open(args.sentiment_sample, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or any(not r.get("story_id") for r in rows):
        raise ValueError("Sentiment sample must contain story_id on every row")
    with session_scope(args.db) as session:
        result = sample_titles(session, rows, args.random_count, args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(result)
    print(f"Exported {len(result)} titles → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
