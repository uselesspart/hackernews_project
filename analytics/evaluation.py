"""Deterministic article-level splits for offline annotation studies."""

import hashlib
from random import Random


def stable_hash(word: str) -> int:
    """Process-independent initialization for gensim Word2Vec."""
    return int.from_bytes(hashlib.md5(word.encode()).digest()[:4], "little")


def split_articles(rows: list[dict], seed: int = 42) -> list[str]:
    """50/25/25 train/validation/test; an article never crosses a split.

    Older annotation CSVs without story_id are grouped by comment_id. This
    prevents duplicate comments from leaking, but cannot isolate whole threads.
    """
    groups = []
    for row in rows:
        if row.get("story_id"):
            group = f"story:{row['story_id']}"
        elif row.get("comment_id"):
            group = f"comment:{row['comment_id']}"
        else:
            raise ValueError("Each annotation needs story_id or comment_id")
        groups.append(group)
    unique = sorted(set(groups))
    if len(unique) < 4:
        raise ValueError("At least four independent articles/comments are required for a held-out evaluation")
    Random(seed).shuffle(unique)
    n = max(1, len(unique) // 4)
    assignment = {g: "test" if i < n else "validation" if i < 2 * n else "train"
                  for i, g in enumerate(unique)}
    return [assignment[g] for g in groups]
