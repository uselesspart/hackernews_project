"""One-week mention-share forecasts with expanding-window, chronological evaluation."""
from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select

from db.models import Story, Tech, story_tech
from db.queries import is_alive

METHODS = ("last", "mean4", "lag4", "ridge0.1", "ridge1", "ridge10", "ridge100")
MIN_TRAIN = 8
MIN_WEEKS = 16


def weekly_shares(session, coverage_start=None, coverage_end=None):
    """Use only complete Monday-Sunday UTC weeks; denominator includes non-tech stories.

    Bounds describe data coverage, not the first/last mention. Empty interior weeks
    are retained and disqualify a series rather than masquerading as zero interest.
    """
    stories = pd.DataFrame(session.execute(select(Story.id, Story.time).where(
        is_alive(Story), Story.title.isnot(None), Story.time.isnot(None))).all(), columns=["id", "time"])
    columns = ["week", "tech", "mentions", "stories", "share"]
    if stories.empty:
        return pd.DataFrame(columns=columns)
    times = pd.to_datetime(stories.time, utc=True).dt.tz_localize(None)
    first = pd.Timestamp(coverage_start) if coverage_start else times.min()
    last = pd.Timestamp(coverage_end) if coverage_end else times.max()
    first = first.tz_localize(None) if first.tzinfo else first
    last = last.tz_localize(None) if last.tzinfo else last
    monday = first.normalize() - pd.Timedelta(days=first.weekday())
    start = monday if first == monday else monday + pd.Timedelta(days=7)
    stop = last.normalize() - pd.Timedelta(days=last.weekday())
    weeks = pd.date_range(start, stop, freq="7D", inclusive="left")
    if weeks.empty:
        return pd.DataFrame(columns=columns)
    stories["week"] = times.dt.normalize() - pd.to_timedelta(times.dt.weekday, unit="D")
    stories = stories[stories.week.isin(weeks)]
    totals = stories.groupby("week").size().reindex(weeks, fill_value=0)
    links = pd.DataFrame(session.execute(select(story_tech.c.story_id, Tech.name).join(
        Tech, Tech.id == story_tech.c.tech_id)).all(), columns=["id", "tech"])
    links = links.merge(stories[["id", "week"]], on="id").drop_duplicates(["id", "tech"])
    counts = links.groupby(["week", "tech"]).size()
    keys = list(session.scalars(select(Tech.name).order_by(Tech.name)))
    rows = []
    for key in keys:
        for week in weeks:
            n = int(counts.get((week, key), 0))
            total = int(totals.loc[week])
            rows.append((week, key, n, total, n / total if total else np.nan))
    return pd.DataFrame(rows, columns=columns)


def features(history):
    h = np.asarray(history, dtype=float)
    return [h[-1], h[-2], h[-4], h[-4:].mean(), h[-1] - h[-4]]


def predict(history, method):
    """Fit preprocessing and estimator afresh using only observations before the origin."""
    h = np.asarray(history, dtype=float)
    if len(h) < MIN_TRAIN or not np.isfinite(h).all() or ((h < 0) | (h > 1)).any():
        raise ValueError("Expected at least eight finite weekly shares between zero and one")
    if method == "last":
        value = h[-1]
    elif method == "mean4":
        value = h[-4:].mean()
    elif method == "lag4":
        value = h[-4]
    elif method.startswith("ridge") and method in METHODS:
        x = [features(h[:i]) for i in range(4, len(h))]
        model = make_pipeline(StandardScaler(), Ridge(alpha=float(method[5:])))
        model.fit(x, h[4:])
        value = model.predict([features(h)])[0]
    else:
        raise ValueError(f"Unknown forecast method: {method}")
    return float(np.clip(value, 0, 1))


def evaluate_series(frame, min_mentions=30):
    """Freeze method after validation; test origins update history, never the selection."""
    frame = frame.sort_values("week").reset_index(drop=True)
    y = frame.share.to_numpy(dtype=float)
    result = {"status": "insufficient_data", "weeks": len(y), "mentions": int(frame.mentions.sum())}
    if len(y) < MIN_WEEKS or not np.isfinite(y).all():
        return result, []
    n_test = max(4, len(y) // 5)
    n_validation = max(3, len(y) // 5)
    validation_start, test_start = len(y) - n_test - n_validation, len(y) - n_test
    result['training_mentions'] = int(frame.mentions.iloc[:validation_start].sum())
    if validation_start < MIN_TRAIN or result['training_mentions'] < min_mentions:
        return result, []
    scores, rows = {}, []
    for method in METHODS:
        for origin in range(validation_start, len(y)):
            prediction = predict(y[:origin], method)
            rows.append({"week": str(frame.week.iloc[origin].date()), "method": method,
                         "split": "validation" if origin < test_start else "test",
                         "actual": float(y[origin]), "prediction": prediction,
                         "train_end": str(frame.week.iloc[origin - 1].date())})
        validation = [r for r in rows if r["method"] == method and r["split"] == "validation"]
        scores[method] = float(np.mean([abs(r["actual"] - r["prediction"]) for r in validation]))
    chosen = min(METHODS, key=lambda m: scores[m])
    test = [r for r in rows if r["method"] == chosen and r["split"] == "test"]
    baseline = [r for r in rows if r["method"] == "last" and r["split"] == "test"]
    mae = float(np.mean([abs(r["actual"] - r["prediction"]) for r in test]))
    baseline_mae = float(np.mean([abs(r["actual"] - r["prediction"]) for r in baseline]))
    week = frame.week.iloc[-1]
    result.update(status="available", model=chosen, share=predict(y, chosen),
                  last_share=float(y[-1]), target_week=str((week + timedelta(days=7)).date()),
                  data_through=str((week + timedelta(days=6)).date()),
                  validation_mae=scores[chosen], test_mae=mae, baseline_mae=baseline_mae,
                  test_weeks=n_test, validation_weeks=n_validation,
                  beats_baseline=mae < baseline_mae,
                  test_start=str(frame.week.iloc[test_start].date()),
                  validation_start=str(frame.week.iloc[validation_start].date()))
    return result, rows


def run_forecasts(session):
    weekly = weekly_shares(session)
    results, predictions = {}, []
    for key, frame in weekly.groupby("tech", sort=True):
        result, rows = evaluate_series(frame)
        results[key] = result
        predictions.extend({"tech": key, **row} for row in rows)
    return weekly, results, pd.DataFrame(predictions)
