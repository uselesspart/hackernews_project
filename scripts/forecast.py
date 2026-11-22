"""Evaluate mention-share forecasts and optionally publish them to the local API database."""
import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select

from analytics.forecast import run_forecasts
from db import session_scope
from db.models import Tech, TechForecast
from utils.cli import cli_main


@cli_main
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--output-dir', default='artifacts/forecast')
    parser.add_argument('--write-db', action='store_true', help='Replace published forecasts after evaluation')
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with session_scope(args.db) as session:
        weekly, results, predictions = run_forecasts(session)
        weekly.to_csv(output / 'weekly_shares.csv', index=False)
        predictions.to_csv(output / 'backtest.csv', index=False)
        available = [r for r in results.values() if r['status'] == 'available']
        report = {'target': 'share of all live titled stories mentioning a technology',
                  'horizon_weeks': 1, 'selection': 'expanding-window validation MAE only',
                  'intervals': 'not estimated; point forecasts are experimental',
                  'available': len(available),
                  'beats_last_value': sum(r['beats_baseline'] for r in available),
                  'technologies': results}
        (output / 'metrics.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        if args.write_db:
            session.execute(delete(TechForecast))
            for key, tech_id in session.execute(select(Tech.name, Tech.id)):
                payload = results.get(key, {'status': 'insufficient_data', 'weeks': 0, 'mentions': 0})
                session.add(TechForecast(tech_id=tech_id, payload=payload,
                                        computed_at=datetime.now(UTC).replace(tzinfo=None)))
            session.commit()
    print(json.dumps({k: v for k, v in report.items() if k != 'technologies'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
