"""Evaluate a technology dictionary against independently annotated titles."""

import argparse
import csv
import json
from pathlib import Path

from analytics.embeddings.patterns import COMPILED_PATTERNS
from utils.cli import cli_main


def read_labeled(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    seen = set()
    for row in rows:
        if not row.get("story_id") or row["story_id"] in seen:
            raise ValueError("Every title needs a unique story_id")
        seen.add(row["story_id"])
        raw = row.get("gold_techs", "").strip()
        if not raw:
            raise ValueError(f"Story {row['story_id']}: use [] for a checked title with no technologies")
        gold = json.loads(raw)
        if not isinstance(gold, list) or any(not isinstance(t, str) for t in gold):
            raise ValueError("gold_techs must be a JSON array of canonical technology keys")
        if unknown := set(gold) - COMPILED_PATTERNS.keys():
            raise ValueError(f"Unknown technology keys: {sorted(unknown)}")
        row["gold_techs"] = set(gold)
    if not rows:
        raise ValueError("No labelled titles")
    return rows


def metrics(tp: int, fp: int, fn: int) -> dict:
    return {"tp": tp, "fp": fp, "fn": fn, "support": tp + fn,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}


def evaluate(rows: list[dict], patterns=None) -> dict:
    patterns = COMPILED_PATTERNS if patterns is None else patterns
    counts = {key: [0, 0, 0] for key in patterns}
    errors, exact = [], 0
    for row in rows:
        gold = row["gold_techs"]
        predicted = {key for key, pattern in patterns.items() if pattern.search(row["title"])}
        exact += predicted == gold
        for key in predicted | gold:
            counts.setdefault(key, [0, 0, 0])
            counts[key][0 if key in predicted & gold else 1 if key in predicted else 2] += 1
        if predicted != gold:
            errors.append({"story_id": row["story_id"], "title": row["title"],
                           "false_positive": sorted(predicted - gold), "false_negative": sorted(gold - predicted)})
    per_tech = {key: metrics(*count) for key, count in counts.items() if any(count)}
    total = [sum(c[i] for c in counts.values()) for i in range(3)]
    return {"n": len(rows), "micro": metrics(*total), "exact_match": exact / len(rows) if rows else 0.0,
            "per_tech": per_tech, "errors": errors}


def parse_args():
    p = argparse.ArgumentParser(description="Precision/recall/F1 of the title technology dictionary")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-o", "--output", required=True, help="JSON with metrics and individual errors")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    rows = read_labeled(args.input)
    result = evaluate(rows)
    # Keep the technology-enriched sentiment sample separate from random controls.
    result["by_source"] = {source: evaluate([r for r in rows if r.get("sample_source") == source])
                           for source in sorted({r.get("sample_source", "") for r in rows})}
    result["annotation_sources"] = sorted({r.get("annotation_source", "unspecified") for r in rows})
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"n": result["n"], **result["micro"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
