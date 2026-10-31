import csv
import json
import re

import numpy as np
import pytest

from analytics.embeddings.scripts import calculate_sentiment as cs
from analytics.embeddings.scripts import evaluate_sentiment as es
from analytics.embeddings.scripts import evaluate_tech as et
from analytics.evaluation import split_articles
from db import session_scope
from db.scripts import export_sentiment_sample as ess
from db.scripts import export_tech_sample as ets
from scripts import train_sentiment_models as train


def test_split_is_reproducible_and_keeps_threads_together():
    rows = [{"story_id": str(i // 3), "comment_id": str(i)} for i in range(60)]
    splits = split_articles(rows)
    assert splits == split_articles(rows)
    assert set(splits) == {"train", "validation", "test"}
    for story in {r['story_id'] for r in rows}:
        assert len({s for r, s in zip(rows, splits) if r['story_id'] == story}) == 1
    assert splits != split_articles(rows, seed=1)


def test_split_groups_legacy_duplicates_and_rejects_tiny_samples():
    rows = [{"comment_id": str(i // 2)} for i in range(16)]
    splits = split_articles(rows)
    assert splits[::2] == splits[1::2]
    with pytest.raises(ValueError, match="four"):
        split_articles(rows[:4])


def test_missing_aspect_abstains_and_whole_removes_quotes():
    rows = [{"tech": "rust", "text": "<p>> Rust is terrible.<p>The meeting is wonderful."}]
    scores = es.vader_scores(rows)
    assert scores['vader'][0] > 0
    assert np.isnan(scores['vader_aspect'][0])
    assert es.to_labels(scores['vader_aspect'], 0.12).tolist() == [2]


def test_selection_uses_validation_not_test_labels():
    y = [-1, 0, 1] * 2
    rows = [{"label_comment": label, "label_tech": label} for label in y]
    splits = ['validation'] * 3 + ['test'] * 3
    scores = {'a': np.array([-1., 0., 1., 1., 0., -1.]),
              'b': np.array([1., 0., -1., -1., 0., 1.])}
    result = es.evaluate_holdout(rows, scores, {}, splits)
    assert all(r['method'] == 'a' for r in result if r['selected'])
    assert result[0]['f1'] < result[1]['f1']
    for r in rows[3:]:
        r['label_comment'] *= -1
        r['label_tech'] *= -1
    changed = es.evaluate_holdout(rows, scores, {}, splits)
    assert [(r['method'], r['threshold'], r['selected']) for r in result] == [
        (r['method'], r['threshold'], r['selected']) for r in changed]


def test_holdout_counts_abstention_as_missed_prediction():
    rows = [{"label_comment": label, "label_tech": label} for label in [-1, 0, 1] * 2]
    scores = {'aspect': np.array([-1., 0., 1., np.nan, 0., 1.])}
    result = es.evaluate_holdout(rows, scores, {}, ['validation'] * 3 + ['test'] * 3)
    assert result[0]['n'] == 3
    assert result[0]['coverage'] == pytest.approx(2 / 3)
    assert result[0]['f1'] == pytest.approx(2 / 3)


def test_technology_metrics_include_misses_and_false_positives():
    patterns = {'python': re.compile('Python'), 'rust': re.compile('Rust')}
    rows = [{"story_id": '1', "title": 'Python', "gold_techs": {'python', 'rust'}},
            {"story_id": '2', "title": 'Rust', "gold_techs": set()},
            {"story_id": '3', "title": 'Weather', "gold_techs": set()}]
    result = et.evaluate(rows, patterns)
    assert result['micro']['precision'] == result['micro']['recall'] == 0.5
    assert result['micro']['tp'] == result['micro']['fp'] == result['micro']['fn'] == 1
    assert result['exact_match'] == pytest.approx(1 / 3)
    assert result['per_tech']['rust']['support'] == 1


def _csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.mark.parametrize('gold', ['', '["unknown"]', '"python"'])
def test_unreviewed_or_invalid_technology_gold_is_rejected(tmp_path, gold):
    path = _csv(tmp_path / 'labels.csv', [{"story_id": '1', "title": 'Python', "gold_techs": gold}])
    with pytest.raises(ValueError):
        et.read_labeled(path)


def test_tech_cli_scores_reviewed_empty_titles(run_cli, tmp_path):
    sample = _csv(tmp_path / 'labels.csv', [
        {"story_id": '1', "title": 'Weather', "gold_techs": '[]', "sample_source": 'random_control'},
        {"story_id": '2', "title": 'Python', "gold_techs": '["python"]', "sample_source": 'sentiment'}])
    out = tmp_path / 'results.json'
    assert run_cli(et.main, '-i', sample, '-o', out) == 0
    result = json.loads(out.read_text())
    assert result['exact_match'] == 1
    assert result['by_source']['random_control']['n'] == 1


def test_bootstrap_single_class_or_empty_data_returns_none():
    from tests.test_sentiment import LEX, NO_MODEL
    assert cs.bootstrap_classifier([], NO_MODEL, NO_MODEL, LEX) is None
    assert cs.bootstrap_classifier(['good'] * 100, NO_MODEL, NO_MODEL, LEX) is None


def test_training_overlap_rejected_before_loading_models(run_cli, tmp_path):
    evaluation = _csv(tmp_path / 'evaluation.csv', [
        {"story_id": str(i), "comment_id": str(i), "tech": 'rust', "text": 'Rust exists.',
         "label_comment": 0, "label_tech": 0} for i in range(8)])
    training = _csv(tmp_path / 'training.csv', [{"story_id": '0', "comment_id": '99', "text": 'Rust'}])
    assert run_cli(es.main, '-i', evaluation, '--training-input', training) == 1
    assert run_cli(train.main, '-i', training, '--evaluation-sample', evaluation,
                   '-o', tmp_path / 'models') == 1


def test_export_titles_controls_and_training_exclusion(classified_db):
    with session_scope(classified_db) as session:
        rows = ess.sample_comments(session, ['cpp', 'rust'], 10, 42)
        assert all(r['story_id'] and r['title'] for r in rows)
        excluded = {r['story_id'] for r in rows}
        assert not ess.sample_comments(session, ['cpp', 'rust'], 10, 42, excluded)
        titles = ets.sample_titles(session, rows, random_count=100)
    assert excluded <= {r['story_id'] for r in titles}
    assert len(titles) == len({r['story_id'] for r in titles})
    assert all(r['gold_techs'] == '' for r in titles)
    assert all('predicted_techs' not in r for r in titles)


def test_irr_without_embeddings_or_interactions_has_diagnostics():
    import pandas as pd

    from analytics.embeddings.scripts.calculate_irr import compute_irr
    rng = np.random.default_rng(42)
    df = pd.DataFrame({'title': ['Rust tips', 'Weather'] * 100, 'descendants': rng.poisson(5, 200)})
    result = compute_irr(df, interactions=False)
    assert 'has_rust' in result['feature'].values
    assert not any(f.startswith(('sim_', 'has_pair_')) for f in result['feature'])
    diag = result.attrs['diagnostics']
    assert diag['converged']
    assert diag['stories_without_detected_techs'] == 100
    assert not diag['embeddings'] and not diag['interactions']
