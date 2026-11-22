"""Diagnose pseudo-label balance and document-vector coverage without using test labels."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
from gensim.models import Word2Vec

from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.embeddings.scripts import calculate_sentiment as cs
from analytics.embeddings.w2v_quality import quality_report
from utils.cli import cli_main


def read_rows(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


@cli_main
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training', required=True)
    parser.add_argument('--evaluation', default='evaluation/sentiment.csv')
    parser.add_argument('--titles-model', required=True)
    parser.add_argument('--context-model', required=True)
    parser.add_argument('--output', default='artifacts/bootstrap_audit.json')
    args = parser.parse_args()
    training, evaluation = read_rows(args.training), read_rows(args.evaluation)
    if not training or any(not r.get('story_id') for r in training + evaluation):
        raise ValueError('Nonempty training and article identifiers are required')
    if {r['story_id'] for r in training}.intersection(r['story_id'] for r in evaluation):
        raise ValueError('Bootstrap training articles overlap with evaluation')
    titles, context = Word2Vec.load(args.titles_model).wv, Word2Vec.load(args.context_model).wv
    if any(quality_report(kv, list(COMPILED_PATTERNS))['degenerate'] for kv in (titles, context)):
        raise ValueError('Degenerate embeddings cannot support the bootstrap experiment')
    lex = cs.expand_lexicon(cs.SEED_POS, cs.SEED_NEG, context, topn=100, sim_thr=.62)
    scores = np.array([cs.aspect_sentiment_score(r['text'], context, lex,
                                               attention=cs.AspectAttention(context, None)) for r in training])
    labels = np.array([cs.label_from_score(s) for s in scores])
    cutoff = float(np.percentile(np.abs(scores), 80))
    chosen = np.abs(scores) >= cutoff
    vectors = [cs.combined_doc_vec(r['text'], titles, context) for r in training]
    report = {'training_rows': len(training), 'article_overlap': 0, 'confidence_cutoff': cutoff,
              'all_pseudo_labels': dict(Counter(map(int, labels))),
              'selected_rows': int(chosen.sum()), 'selected_pseudo_labels': dict(Counter(map(int, labels[chosen]))),
              'zero_vectors': sum(not np.any(v) for v in vectors),
              'note': 'Pseudo-label diagnostics only; no evaluation labels used; no estimate of human accuracy.'}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
