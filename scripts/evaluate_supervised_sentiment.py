"""Compare trainable TF-IDF sentiment models with validation-calibrated VADER."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.svm import LinearSVC

from analytics.embeddings.scripts.evaluate_sentiment import read_labeled, vader_scores
from analytics.sentiment import split_comment
from utils.cli import cli_main

LABELS = [-1, 0, 1]


def validate_splits(rows):
    articles, comments = {}, {}
    for row in rows:
        split = row.get('split')
        if split not in {'train', 'validation', 'test'} or not row.get('story_id'):
            raise ValueError('Every row needs story_id and an explicit train/validation/test split')
        for assignments, key in ((articles, row['story_id']), (comments, row['comment_id'])):
            if key in assignments and assignments[key] != split:
                raise ValueError('Article or comment crosses evaluation splits')
            assignments[key] = split


def model_for(c):
    # Each vectorizer is fitted exclusively on training text, including its vocabulary and IDF.
    features = FeatureUnion([
        ('words', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=20000)),
        ('chars', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5),
                                 sublinear_tf=True, max_features=30000)),
    ])
    return make_pipeline(features, LinearSVC(C=c, class_weight='balanced', random_state=42, max_iter=10000))


def text_for(row, target):
    text = split_comment(row['text']).prose
    if target == 'label_tech':
        return f"Technology: {row['tech']}. Title: {row.get('title', '')}. Comment: {text}"
    return text


def evaluate(rows):
    validate_splits(rows)
    report, predictions = {}, []
    for target in ('label_comment', 'label_tech'):
        labeled = [r for r in rows if r[target] is not None]
        parts = {s: [r for r in labeled if r['split'] == s] for s in ('train', 'validation', 'test')}
        if not all(parts.values()) or len({r[target] for r in parts['train']}) < 2:
            report[target] = {'status': 'insufficient_data'}
            continue
        labels = {s: [r[target] for r in subset] for s, subset in parts.items()}
        texts = {s: [text_for(r, target) for r in subset] for s, subset in parts.items()}
        candidates = []
        for c in (0.1, 1.0, 10.0):
            model = model_for(c)
            model.fit(texts['train'], labels['train'])
            score = f1_score(labels['validation'], model.predict(texts['validation']),
                             labels=LABELS, average='macro', zero_division=0)
            candidates.append((float(score), c, model))
        _, selected_c, selected = max(candidates, key=lambda x: (x[0], -x[1]))
        vader = vader_scores(parts['validation'])['vader']
        thresholds = (0.05, 0.1, 0.12, 0.2, 0.3, 0.4, 0.5)
        threshold = max(thresholds, key=lambda t: f1_score(
            labels['validation'], np.where(vader > t, 1, np.where(vader < -t, -1, 0)),
            labels=LABELS, average='macro', zero_division=0))
        test_vader = vader_scores(parts['test'])['vader']
        outputs = {'tfidf_svm': selected.predict(texts['test']),
                   'vader': np.where(test_vader > threshold, 1, np.where(test_vader < -threshold, -1, 0))}
        result = {'status': 'available', 'C': selected_c, 'vader_threshold': threshold,
                  'validation_candidates': [{'C': c, 'macro_f1': f} for f, c, _ in candidates],
                  'counts': {s: len(part) for s, part in parts.items()}, 'test': {}}
        for method, predicted in outputs.items():
            result['test'][method] = {
                'macro_f1': float(f1_score(labels['test'], predicted, labels=LABELS,
                                           average='macro', zero_division=0)),
                'confusion_matrix': confusion_matrix(labels['test'], predicted, labels=LABELS).tolist(),
                'predicted_labels': dict(Counter(map(int, predicted))),
            }
            for row, pred in zip(parts['test'], predicted, strict=True):
                predictions.append({'target': target, 'method': method, 'story_id': row['story_id'],
                                    'comment_id': row['comment_id'], 'tech': row['tech'],
                                    'gold': row[target], 'prediction': int(pred),
                                    'correct': int(pred) == row[target]})
        report[target] = result
    report['annotation_sources'] = sorted({r.get('annotation_source', 'unspecified') for r in rows})
    report['human_gold'] = all(r.get('annotation_source', '').startswith('Human-reviewed:') for r in rows)
    report['selection'] = 'C and VADER threshold selected on validation only; test not used for deployment selection'
    return report, predictions


@cli_main
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='evaluation/sentiment.csv')
    parser.add_argument('--output-dir', default='artifacts/supervised_sentiment')
    args = parser.parse_args()
    report, predictions = evaluate(read_labeled(args.input))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'metrics.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    if predictions:
        with (out / 'test_predictions.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(predictions[0]))
            writer.writeheader()
            writer.writerows(predictions)
    print(json.dumps(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
