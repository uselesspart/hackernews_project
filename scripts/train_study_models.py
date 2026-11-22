"""Train reproducible title/context models excluding every evaluation article."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from gensim.models import Word2Vec
from sqlalchemy import select

from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.embeddings.w2v_quality import quality_report
from analytics.evaluation import stable_hash
from analytics.sentiment import split_comment
from db import session_scope
from db.models import Story
from db.queries import is_alive, iter_tech_thread_comments
from utils.cli import cli_main
from utils.lemmatize import tokenize_and_lemmatize


@cli_main
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', required=True)
    p.add_argument('--exclude', action='append', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--epochs', type=int, default=20)
    p.add_argument('--seed', type=int, default=42)
    args = p.parse_args()
    excluded, sources = set(), {}
    for path in args.exclude:
        sources[Path(path).name] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        with open(path, encoding='utf-8-sig', newline='') as f:
            excluded.update(int(r['story_id']) for r in csv.DictReader(f))
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metadata = dict(seed=args.seed, workers=1, vector_size=50, epochs=args.epochs,
                    window=5, min_count=2, sg=1, lemmatization=False,
                    negative=5, sample=.001, hs=0, shrink_windows=True,
                    exclusions=sources, excluded_articles=len(excluded), models={},
                    excluded_story_ids_sha256=hashlib.sha256(
                        json.dumps(sorted(excluded)).encode()).hexdigest())
    with session_scope(args.db) as session:
        titles = [tokenize_and_lemmatize(text, lemmatize_en=False) for sid, text in session.execute(
            select(Story.id, Story.title).where(is_alive(Story)).order_by(Story.id))
                  if sid not in excluded and text]
        comments = [tokenize_and_lemmatize(parts.prose, lemmatize_en=False)
                    for _, raw, sid in iter_tech_thread_comments(session)
                    if sid not in excluded and (parts := split_comment(raw)).prose]
    for name, sentences in (('titles', titles), ('context', comments)):
        print(f'Training {name}: {len(sentences)} documents', flush=True)
        model = Word2Vec(sentences, vector_size=50, min_count=2, window=5, sg=1,
                         epochs=args.epochs, workers=1, seed=args.seed, hashfxn=stable_hash)
        model.save(str(output / f'{name}.model'))
        metadata['models'][name] = dict(documents=len(sentences), vocabulary=len(model.wv),
                                        quality=quality_report(model.wv, list(COMPILED_PATTERNS)))
        (output / 'training.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(json.dumps(metadata['models'][name]), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
