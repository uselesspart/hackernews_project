"""Train reproducible Word2Vec baselines on a separate unlabelled comment sample."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from gensim.models import Word2Vec

from analytics.embeddings.patterns import COMPILED_PATTERNS
from analytics.embeddings.w2v_quality import quality_report
from analytics.evaluation import stable_hash
from utils.cli import cli_main
from utils.lemmatize import tokenize_and_lemmatize


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", required=True, help="Unlabelled CSV from export_sentiment_sample")
    p.add_argument("--evaluation-sample", required=True, help="CSV whose articles must be excluded from training")
    p.add_argument("-o", "--output-dir", required=True)
    p.add_argument("--vector-size", type=int, default=50)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    with open(args.evaluation_sample, encoding="utf-8-sig", newline="") as f:
        evaluation = list(csv.DictReader(f))
    if not rows or any(not r.get("story_id") for r in [*rows, *evaluation]):
        raise ValueError("Both CSVs require story_id")
    if {r['story_id'] for r in rows} & {r['story_id'] for r in evaluation}:
        raise ValueError("Training and evaluation articles overlap")
    comments = {r['comment_id']: r['text'] for r in rows}
    titles = {r['story_id']: r['title'] for r in rows}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    metadata = {"seed": args.seed, "workers": 1, "vector_size": args.vector_size, "epochs": args.epochs,
                "window": 5, "min_count": 2, "sg": 1, "lemmatization": False,
                "input_sha256": hashlib.sha256(Path(args.input).read_bytes()).hexdigest(), "models": {}}
    for name, texts in (("titles", titles.values()), ("context", comments.values())):
        sentences = [tokenize_and_lemmatize(text, lemmatize_en=False) for text in texts]
        model = Word2Vec(sentences, vector_size=args.vector_size, min_count=2, window=5,
                         sg=1, epochs=args.epochs, workers=1, seed=args.seed,
                         hashfxn=stable_hash)
        model.save(str(out / f"{name}.model"))
        metadata["models"][name] = {"documents": len(sentences), "vocabulary": len(model.wv),
                                    "quality": quality_report(model.wv, list(COMPILED_PATTERNS))}
        print(f"{name}: {len(sentences)} documents, {len(model.wv)} words")
    (out / "training.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
