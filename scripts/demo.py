"""Run the presentation locally: one process serves the API and built React application."""
import argparse
import os
import sqlite3
from pathlib import Path

from utils.cli import cli_main


def check_demo(db, frontend):
    if not db.is_file():
        raise ValueError(f'Database not found: {db}')
    if not (frontend / 'index.html').is_file():
        raise ValueError('Build the frontend first: cd frontend; npm run build')
    with sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True) as conn:
        counts = {t: conn.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
                  for t in ('story', 'comment', 'tech_metrics')}
        if not counts['story'] or not counts['tech_metrics']:
            raise ValueError('The selected database has no stories or precomputed metrics')
        counts['period'] = conn.execute('SELECT min(time), max(time) FROM story').fetchone()
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='tech_forecast'").fetchone()
        counts['forecasts'] = conn.execute('SELECT count(*) FROM tech_forecast').fetchone()[0] if exists else 0
    return counts


@cli_main
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=Path('artifacts/study/hn.db'))
    parser.add_argument('--frontend', type=Path, default=Path('frontend/dist'))
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--check', action='store_true', help='Validate the demo without starting a server')
    args = parser.parse_args()
    db, frontend = args.db.resolve(), args.frontend.resolve()
    if not 1 <= args.port <= 65535:
        raise ValueError('port must be between 1 and 65535')
    counts = check_demo(db, frontend)
    print(f'Database: {db}\nDataset: {counts}\nLocal demo: http://127.0.0.1:{args.port}', flush=True)
    if args.check:
        return 0
    os.environ['HN_DB_URL'] = f'sqlite:///{db.as_posix()}'
    os.environ['HN_FRONTEND_DIR'] = str(frontend)
    import uvicorn
    uvicorn.run('api.main:create_app', factory=True, host='127.0.0.1', port=args.port, log_level='info')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
