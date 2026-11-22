from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analytics.embeddings.scripts.calculate_irr import adjust_technology_pvalues, calendar_features
from api.config import Settings
from api.main import create_app
from db import session_scope
from db.models import Comment, Story
from scripts.evaluate_supervised_sentiment import validate_splits
from scripts.human_review import import_reviews
from scripts.update_data import update_ids


def test_bh_corrects_only_technology_family():
    result = adjust_technology_pvalues(pd.DataFrame({
        'feature': ['has_rust', 'has_python', 'has_url', 'const', 'has_pair_rust__python'],
        'pval': [.01, .04, .9, .001, .005]}))
    # has_url is the existing naming convention for a control, not a technology.
    assert result.loc[0, 'qval_bh'] == pytest.approx(.02)
    assert np.isnan(result.loc[2, 'qval_bh'])
    assert np.isnan(result.loc[4, 'qval_bh'])


def test_calendar_controls_require_valid_dates():
    with pytest.raises(ValueError, match='time'):
        calendar_features(pd.DataFrame({'title': ['Rust']}))
    with pytest.raises(ValueError, match='valid'):
        calendar_features(pd.DataFrame({'time': ['not a time']}))
    fields = calendar_features(pd.DataFrame({'time': ['2024-01-01 12:00', '2024-02-03 03:00']}))
    assert 'hour_sin' in fields
    assert len(fields['hour_sin']) == 2


def test_supervised_split_rejects_thread_leakage():
    with pytest.raises(ValueError, match='crosses'):
        validate_splits([{'story_id': '1', 'comment_id': '11', 'split': 'train'},
                         {'story_id': '1', 'comment_id': '12', 'split': 'test'}])


def test_human_review_rejects_empty_or_tampered_reviews():
    original = [{'story_id': '1', 'comment_id': '2', 'tech': 'rust', 'text': 'Rust is good',
                 'title': 'Title', 'split': 'test'}]
    assert import_reviews(original, [{**original[0], 'reviewed': ''}]) == []
    reviewed = {**original[0], 'reviewed': '1', 'label_comment': '1', 'label_tech': '',
                'reviewer': 'Reviewer', 'reviewed_at': '2026-11-23'}
    assert import_reviews(original, [reviewed])[0]['label_tech'] == ''
    with pytest.raises(ValueError, match='match'):
        import_reviews(original, [{**reviewed, 'split': 'train'}])
    with pytest.raises(ValueError, match='reviewer'):
        import_reviews(original, [{**reviewed, 'reviewer': ''}])


def test_incremental_refresh_is_bounded_and_not_starved(db_url):
    now = datetime(2026, 11, 23, tzinfo=UTC)
    with session_scope(db_url) as session:
        session.add_all([Story(id=100, title='Rust', time=now.replace(tzinfo=None)),
                         Comment(id=101, parent=100, time=now.replace(tzinfo=None))])
        session.commit()
        ids = update_ids(session, 200, max_items=10, refresh_days=7, now=now)
        assert len(ids) == 10
        assert {100, 101}.issubset(ids)
        assert set(range(102, 110)).issubset(ids)


def test_local_demo_spa_preserves_api_and_asset_404(db_url, tmp_path, monkeypatch):
    (tmp_path / 'index.html').write_text('<html>Demo</html>', encoding='utf-8')
    monkeypatch.setenv('HN_FRONTEND_DIR', str(tmp_path))
    with TestClient(create_app(Settings(db_url=db_url))) as client:
        assert client.get('/tech/rust').text == '<html>Demo</html>'
        assert client.get('/api/not-a-route').status_code == 404
        assert client.get('/assets/missing.js').status_code == 404
        assert client.get('/api/health').status_code == 200
