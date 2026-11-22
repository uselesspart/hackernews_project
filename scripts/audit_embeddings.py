"""Inspect every catalog technology, rare-token coverage and category consistency of neighbors."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from gensim.models import Word2Vec

from analytics.catalog import tech_info
from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.embeddings.w2v_quality import quality_report, tech_similarity
from utils.cli import cli_main
from utils.groups import normalize_token


def audit(kv):
    keys, sim = tech_similarity(kv, list(COMPILED_PATTERNS))
    rows = []
    for i, key in enumerate(keys):
        count = int(kv.get_vecattr(normalize_token(key), 'count'))
        neighbors = [int(j) for j in np.argsort(-sim[i], kind='stable') if int(j) != i][:10]
        categories = set(tech_info(key).categories)
        for rank, j in enumerate(neighbors, 1):
            other = keys[j]
            rows.append({'tech': key, 'token_count': count, 'rare': count < 20,
                         'neighbor': other, 'rank': rank, 'similarity': float(sim[i, j]),
                         'shared_category': bool(categories.intersection(tech_info(other).categories)),
                         'human_relevant': '', 'reviewer': '', 'notes': ''})
    report = quality_report(kv, list(COMPILED_PATTERNS))
    report['missing'] = sorted(set(COMPILED_PATTERNS) - set(keys))
    report['diagnostic_only'] = 'Category agreement is a proxy, not semantic relevance ground truth'
    report['groups'] = {}
    for group, selected in (('all', rows), ('rare', [r for r in rows if r['rare']]),
                            ('frequent', [r for r in rows if not r['rare']])):
        report['groups'][group] = {'technologies': len({r['tech'] for r in selected}),
                                    'category_agreement_at10': float(np.mean(
                                        [r['shared_category'] for r in selected])) if selected else None}
    return report, rows


@cli_main
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    report, rows = audit(Word2Vec.load(args.model).wv)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'metrics.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    if rows:
        with (output / 'neighbors_review.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({'technologies': report['techs'], 'missing': report['missing'], 'groups': report['groups']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
