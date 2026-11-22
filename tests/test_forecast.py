from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analytics.forecast import evaluate_series, weekly_shares
from api.config import Settings
from api.main import create_app
from db import session_scope
from db.models import Story, Tech, TechForecast


def series(values):
    return pd.DataFrame({'week': pd.date_range('2024-01-01', periods=len(values), freq='7D'),
                         'share': values, 'stories': 100, 'mentions': 10})


def test_future_test_labels_cannot_change_selected_method():
    a = series(np.linspace(.1, .3, 20))
    b = a.copy()
    b.loc[16:, 'share'] = [.9, .01, .7, .2]
    first, _ = evaluate_series(a)
    second, _ = evaluate_series(b)
    assert first['model'] == second['model']
    assert first['validation_mae'] == second['validation_mae']


def test_rolling_origin_never_reads_current_or_later_labels():
    a = series(np.linspace(.1, .2, 20))
    b = a.copy()
    b.loc[17:, 'share'] = .8
    _, before = evaluate_series(a)
    _, after = evaluate_series(b)
    for original, changed in zip(before, after, strict=True):
        if original['week'] <= '2024-04-29':
            assert original['prediction'] == changed['prediction']


def test_constant_series_baseline_and_missing_data():
    result, _ = evaluate_series(series([.1] * 16))
    assert result['model'] == 'last'
    assert result['share'] == pytest.approx(.1)
    assert result['test_mae'] == 0
    assert result['beats_baseline'] is False
    assert evaluate_series(series([.1] * 15))[0]['status'] == 'insufficient_data'
    frame = series([.1] * 16)
    frame.loc[5, 'share'] = np.nan
    assert evaluate_series(frame)[0]['status'] == 'insufficient_data'


def test_only_complete_weeks_and_denominator_includes_nontech(db_url):
    with session_scope(db_url) as session:
        rust = Tech(name='rust')
        session.add(rust)
        # Dataset starts Wednesday and ends Tuesday: only Jan 8-14 is a full week.
        for sid, day in enumerate([3, 8, 9, 14, 16], 1):
            session.add(Story(id=sid, title='Title', time=datetime(2024, 1, day, 12),
                              techs=[rust] if day == 9 else []))
        session.commit()
        weekly = weekly_shares(session)
    assert len(weekly) == 1
    assert weekly.iloc[0]['stories'] == 3
    assert weekly.iloc[0]['mentions'] == 1
    assert weekly.iloc[0]['share'] == pytest.approx(1 / 3)
    assert weekly.iloc[0]['week'] == pd.Timestamp('2024-01-08')


def test_forecast_api_reports_uncomputed_and_published(db_url):
    with session_scope(db_url) as session:
        tech = Tech(name='rust')
        session.add(tech)
        session.commit()
        tid = tech.id
    with TestClient(create_app(Settings(db_url=db_url))) as client:
        assert client.get('/api/techs/rust/forecast').json()['status'] == 'not_computed'
        assert client.get('/api/techs/unknown/forecast').status_code == 404
        with session_scope(db_url) as session:
            result, _ = evaluate_series(series([.1] * 16))
            session.add(TechForecast(tech_id=tid, payload=result, computed_at=datetime(2026, 11, 23)))
            session.commit()
        data = client.get('/api/techs/RUST/forecast').json()
        assert data['share'] == pytest.approx(.1)
        assert data['experimental'] is True
        assert data['test_weeks'] == 4
