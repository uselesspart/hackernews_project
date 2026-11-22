import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from analytics.embeddings.scripts import precompute as pc
from analytics.sentiment import TechSentiment, split_comment
from api.config import Settings
from api.routers.techs import _irr_brief
from db import session_scope
from db.models import Story, Tech, TechMetrics


def test_separate_aspect_threshold_applies_to_summary_and_examples():
    sentiment = TechSentiment(2, .1, aspect_threshold=.5)
    sentiment.add(10, split_comment('Rust is somewhat useful.'), .3, .3, None)
    assert sentiment.summary('whole')['pos_share'] == 1
    assert sentiment.summary('aspect')['neu_share'] == 1
    assert sentiment.examples()[0]['mentions'] is False


@pytest.mark.parametrize('status, low, high, n, reliable, significant', [
    ('available', 1.2, 2.5, 100, True, True),
    ('available', .8, 2.5, 100, True, False),
    ('available', 1.2, 2.5, 10, False, False),
    ('available', 2.1, 2.5, 100, False, False),
    ('available', 1.2, float('inf'), 100, False, False),
    ('model_failed', 1.2, 2.5, 100, False, False),
])
def test_api_irr_validates_interval_count_and_model(status, low, high, n, reliable, significant):
    metrics = TechMetrics(irr=2., irr_low=low, irr_high=high, irr_pval=.02, irr_status=status, irr_stories=n)
    result = _irr_brief(metrics, 500, Settings())
    assert result.reliable is reliable
    assert result.significant is significant
    assert result.n == n
    assert result.high is None or np.isfinite(result.high)


def test_failed_fit_is_distinguishable_from_sparse_data(classified_db, monkeypatch):
    def failed(*args, **kwargs):
        raise ValueError('Deliberate model failure')
    monkeypatch.setattr(pc, 'compute_irr', failed)
    with session_scope(classified_db) as session:
        rows = pc.irr_by_tech(session, min_stories=1)
    assert rows['rust']['irr_status'] == 'model_failed'
    assert rows['postgresql']['irr_status'] == 'insufficient_data'
    assert 'irr' not in rows['rust']


def test_nonconverged_fit_is_not_saved(classified_db, monkeypatch):
    table = pd.DataFrame([dict(feature='has_rust', IRR=2., IRR_low=1.5, IRR_high=3., pval=.01)])
    table.attrs['diagnostics'] = {'converged': False}
    monkeypatch.setattr(pc, 'compute_irr', lambda *a, **k: table)
    with session_scope(classified_db) as session:
        rows = pc.irr_by_tech(session, min_stories=1)
    assert rows['rust']['irr_status'] == 'model_failed'
    assert 'irr' not in rows['rust']


def test_default_precompute_fits_irr_without_embeddings(db_url):
    rng = np.random.default_rng(3)
    with session_scope(db_url) as session:
        session.add_all([Tech(name='rust'), Tech(name='python')])
        for i in range(450):
            title = ['Rust internals', 'Python internals', 'General discussion'][i % 3]
            session.add(Story(id=i + 1, title=title, descendants=int(rng.poisson(30 if i % 3 == 0 else 10))))
        session.commit()
        pc.precompute(session, lemmatize=False)
        row = session.scalar(select(TechMetrics).join(Tech).where(Tech.name == 'rust'))
        assert row.irr_status == 'available'
        assert row.irr_stories == 150
        assert row.irr == pytest.approx(3, rel=.15)
