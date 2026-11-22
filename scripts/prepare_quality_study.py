"""Export blinded title holdout and an additional, article-independent sentiment sample."""
import argparse
import csv
import json
from pathlib import Path
from random import Random

from sqlalchemy import select

from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.embeddings.scripts.evaluate_tech import dictionary_version
from analytics.evaluation import split_articles
from analytics.sentiment import mention_text, split_comment
from db import session_scope
from db.models import Story
from db.queries import is_alive, iter_tech_thread_comments, story_tech_keys
from db.scripts.export_sentiment_sample import FIELDS as SENTIMENT_FIELDS
from db.scripts.export_tech_sample import FIELDS as TITLE_FIELDS
from utils.cli import cli_main


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@cli_main
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', required=True)
    p.add_argument('--exclude', action='append', default=[], help='Prior evaluation/training CSV with story_id')
    p.add_argument('--output-dir', required=True)
    p.add_argument('--seed', type=int, default=20261110)
    p.add_argument('--titles', type=int, default=600)
    p.add_argument('--mention-count', type=int, default=40)
    p.add_argument('--nonmention-count', type=int, default=20)
    p.add_argument('--max-chars', type=int, default=650)
    p.add_argument('--min-chars', type=int, default=60)
    args = p.parse_args()
    if not 0 <= args.min_chars <= args.max_chars:
        raise ValueError('Expected 0 <= min-chars <= max-chars')
    rng = Random(args.seed)
    excluded = set()
    for path in args.exclude:
        with open(path, encoding='utf-8-sig', newline='') as f:
            excluded.update(int(r['story_id']) for r in csv.DictReader(f))
    keys = ['linux', 'gpt', 'python', 'rust', 'javascript', 'windows']
    with session_scope(args.db) as session:
        titles = dict(session.execute(select(Story.id, Story.title).where(is_alive(Story))).all())
        selected = rng.sample(sorted(set(titles) - excluded), args.titles)
        title_rows = [dict(story_id=sid, hn_url=f'https://news.ycombinator.com/item?id={sid}',
                           title=titles[sid], sample_source='development' if i < args.titles // 3 else 'holdout',
                           gold_techs='', annotation_source='', annotation_notes='')
                      for i, sid in enumerate(selected)]
        forbidden = excluded | set(selected)
        pools = {(key, mentions): [] for key in keys for mentions in (True, False)}
        story_keys = story_tech_keys(session)
        for cid, raw, sid in iter_tech_thread_comments(session):
            if sid in forbidden:
                continue
            parts = split_comment(raw)
            if not args.min_chars <= len(parts.prose) <= args.max_chars:
                continue
            for key in set(keys).intersection(story_keys.get(sid, ())):
                mentions = mention_text(parts, COMPILED_PATTERNS[key]) is not None
                pools[key, mentions].append((cid, sid, parts.prose))
        rows, used_comments = [], set()
        for key in keys:
            for mentions, count in ((True, args.mention_count), (False, args.nonmention_count)):
                pool = sorted(pools[key, mentions])
                rng.shuffle(pool)
                picked = [item for item in pool if item[0] not in used_comments][:count]
                for cid, sid, text in picked:
                    used_comments.add(cid)
                    rows.append(dict(tech=key, comment_id=cid, story_id=sid, title=titles[sid],
                                     hn_url=f'https://news.ycombinator.com/item?id={cid}', mentions=int(mentions),
                                     text=text, label_comment='', label_tech='', annotation_source='',
                                     annotation_notes=''))
    out = Path(args.output_dir)
    splits = split_articles(rows, seed=args.seed) if rows else []
    for row, split in zip(rows, splits, strict=True):
        row['split'] = split
    write_csv(out / 'dictionary.csv', title_rows, TITLE_FIELDS)
    write_csv(out / 'sentiment.csv', rows, [*SENTIMENT_FIELDS, 'split'])
    manifest = dict(seed=args.seed, excluded_articles=len(excluded), title_count=len(title_rows),
                    sentiment_count=len(rows), sentiment_articles=len({r['story_id'] for r in rows}),
                    requested_per_tech=dict(mentions=args.mention_count, nonmentions=args.nonmention_count),
                    actual_per_tech={key: sum(r['tech'] == key for r in rows) for key in keys},
                    selection=f'Six technology strata; up to the requested counts if available; '
                              f'prose length {args.min_chars}..{args.max_chars} characters; not representative.',
                    annotation='Blank export for independent review; never copy classifier predictions.',
                    dictionary_sha256=dictionary_version())
    (out / 'sampling.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
