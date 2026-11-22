"""Bounded incremental HN refresh; failed downloads never advance the ingestion checkpoint."""
import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from analytics.embeddings.scripts.classify_tech import classify_stories
from analytics.embeddings.scripts.precompute import precompute
from analytics.forecast import run_forecasts
from db import session_scope
from db.models import Comment, Story, Tech, TechForecast
from hackernews_handler import HNHandler
from hackernews_retriever import HNRetriever
from scripts.retrieve import download_items_streaming
from utils.cli import cli_main


def update_ids(session, latest, max_items, refresh_days, now):
    if max_items < 1 or refresh_days < 0:
        raise ValueError('max_items must be positive; refresh_days cannot be negative')
    last = max(session.scalar(select(func.max(Story.id))) or 0,
               session.scalar(select(func.max(Comment.id))) or 0)
    if not last:
        raise ValueError('An initial dataset is required; refusing to download HN from item 1')
    refresh = set()
    if refresh_days:
        cutoff = now.replace(tzinfo=None) - timedelta(days=refresh_days)
        for model in (Story, Comment):
            refresh.update(session.scalars(select(model.id).where(model.time >= cutoff)))
    # Reserve part of each busy batch for mutable recent items, preventing refresh starvation.
    reserve = min(len(refresh), max_items // 5)
    end = min(latest, last + max_items - reserve)
    new = list(range(last + 1, end + 1))
    remaining = max_items - len(new)
    refresh = sorted(refresh - set(new), reverse=True)[:remaining]
    return new + refresh


@cli_main
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', required=True)
    p.add_argument('--max-items', type=int, default=5000)
    p.add_argument('--refresh-days', type=int, default=7)
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--context-model')
    p.add_argument('--output-dir', default='artifacts/update')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.workers < 1:
        raise ValueError('workers must be positive')
    retriever = HNRetriever()
    latest = retriever.get_maxitem_id()
    with session_scope(args.db) as session:
        ids = update_ids(session, latest, args.max_items, args.refresh_days, datetime.now(UTC))
        print(json.dumps({'requested': len(ids), 'first': min(ids) if ids else None,
                          'last': max(ids) if ids else None, 'hn_latest': latest}))
        if args.dry_run or not ids:
            return 0
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        stats = download_items_streaming(iter(ids), retriever, out / 'items.jsonl.gz', workers=args.workers)
        if stats['errors']:
            raise ValueError(f"{stats['errors']} downloads failed; database unchanged. Retry this batch.")
        HNHandler(session.get_bind()).ingest_from_path(out / 'items.jsonl.gz')
        # Only live titles are classified; deleted/dead links are excluded downstream.
        classify_stories(session)
        session.commit()
        precompute(session, context_model=args.context_model, lemmatize=False)
        _, forecasts, _ = run_forecasts(session)
        for key, tid in session.execute(select(Tech.name, Tech.id)):
            session.merge(TechForecast(tech_id=tid, payload=forecasts.get(key, {
                'status': 'insufficient_data', 'weeks': 0, 'mentions': 0}),
                computed_at=datetime.now(UTC).replace(tzinfo=None)))
        session.commit()
        (out / 'last_success.json').write_text(json.dumps({
            'completed_at': datetime.now(UTC).isoformat(), 'download': stats,
            'note': 'Models are reused; Word2Vec is not retrained during a refresh.'}, default=str, indent=2),
            encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
