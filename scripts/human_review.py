"""Prepare blinded sentiment review sheets and validate completed human annotations."""
import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

from utils.cli import cli_main

IDENTITY = ('story_id', 'comment_id', 'tech', 'text', 'title', 'split')
REVIEW_FIELDS = ['reviewed', 'label_comment', 'label_tech', 'reviewer', 'reviewed_at', 'notes']


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def identity(row):
    return row['comment_id'], row['tech']


def import_reviews(original, reviews):
    source = {identity(r): r for r in original}
    if len(source) != len(original) or len({identity(r) for r in reviews}) != len(reviews):
        raise ValueError('Duplicate comment/technology annotation')
    checked = []
    for review in reviews:
        key = identity(review)
        if key not in source or any(review.get(f, '') != source[key].get(f, '') for f in IDENTITY):
            raise ValueError('Review does not match the source text, technology or split')
        if review.get('reviewed') not in {'', '0', '1'}:
            raise ValueError('reviewed must be blank, 0 or 1')
        if review.get('reviewed') != '1':
            continue
        if not review.get('reviewer', '').strip():
            raise ValueError('A completed review needs a reviewer name')
        reviewed_at = date.fromisoformat(review.get('reviewed_at', ''))
        if review.get('label_comment') not in {'-1', '0', '1'}:
            raise ValueError('Every reviewed row needs a whole-comment label')
        if review.get('label_tech') not in {'', '-1', '0', '1'}:
            raise ValueError('Aspect label must be -1, 0, 1 or blank for no attributable attitude')
        checked.append({**source[key], 'label_comment': review['label_comment'],
                        'label_tech': review['label_tech'],
                        'annotation_source': f"Human-reviewed: {review['reviewer']}, {reviewed_at}",
                        'annotation_notes': review.get('notes', '')})
    return checked


@cli_main
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'import'])
    parser.add_argument('--source', default='evaluation/sentiment.csv')
    parser.add_argument('--reviews')
    parser.add_argument('--output-dir', default='artifacts/human_review')
    args = parser.parse_args()
    original = read_csv(args.source)
    if not original:
        raise ValueError('Source annotation file is empty')
    out = Path(args.output_dir)
    if args.action == 'prepare':
        # AI labels, notes, predictions and model confidence are deliberately absent.
        rows = [{**{k: r.get(k, '') for k in (*IDENTITY, 'hn_url', 'mentions')},
                 **dict.fromkeys(REVIEW_FIELDS, '')} for r in original]
        write_csv(out / 'blinded_sentiment.csv', rows, list(rows[0]))
        manifest = {'source_sha256': hashlib.sha256(Path(args.source).read_bytes()).hexdigest(),
                    'rows': len(rows), 'human_review_complete': False,
                    'instruction': 'Do not inspect AI labels or model predictions before completing this sheet.'}
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    else:
        if not args.reviews:
            raise ValueError('--reviews is required for import')
        checked = import_reviews(original, read_csv(args.reviews))
        if not checked:
            raise ValueError('No completed human reviews; no gold dataset was created')
        write_csv(out / 'human_only.csv', checked, list(original[0]))
        print(f'Imported {len(checked)} human-reviewed rows; unreviewed AI labels excluded')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
