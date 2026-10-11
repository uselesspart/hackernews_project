"""
Подбор параметров Word2Vec (PLAN 2.6): обучает модели по сетке и сравнивает их на проверочных
парах технологий (analytics.embeddings.w2v_quality). Модели не сохраняются — лучший набор
параметров затем передаётся в train_model.
"""
import argparse
import csv
import itertools
import os
import time

from gensim.models import Word2Vec

from analytics.embeddings.patterns import PATTERNS
from analytics.embeddings.scripts.train_model import JsonlGzCorpus
from analytics.embeddings.w2v_quality import quality_report
from utils.cli import cli_main


def _ints(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x.strip()]


def grid(vector_sizes, min_counts, epochs, windows) -> list[dict]:
    return [{"vector_size": v, "min_count": m, "epochs": e, "window": w}
            for v, m, e, w in itertools.product(vector_sizes, min_counts, epochs, windows)]


def tune(corpus, configs: list[dict], *, sg: int = 1, workers: int = 1, seed: int = 1, k: int = 10) -> list[dict]:
    """Строка на конфигурацию: параметры, размер словаря, доля пар в топ-k, MRR, вырожденность."""
    keys = list(PATTERNS)
    results = []
    for cfg in configs:
        started = time.perf_counter()
        model = Word2Vec(sentences=corpus, sg=sg, workers=workers, seed=seed, **cfg)
        report = quality_report(model.wv, keys, k=k)
        results.append({**cfg, "vocab": len(model.wv), "techs": report["techs"],
                        "pairs": len(report["pairs"]), "hit_rate": report["hit_rate"], "mrr": report["mrr"],
                        "mean_similarity": report["mean_similarity"], "degenerate": report["degenerate"],
                        "seconds": round(time.perf_counter() - started, 1)})
    return results


def rank(results: list[dict]) -> list[dict]:
    """Невырожденные — выше; дальше по MRR, при равенстве — меньшая размерность (дешевле и меньше переобучается)."""
    return sorted(results, key=lambda r: (r["degenerate"], -(r["mrr"] or 0), r["vector_size"]))


def parse_args():
    p = argparse.ArgumentParser(
        prog="tune_model",
        description="Подбор параметров Word2Vec по проверочным парам технологий"
    )
    p.add_argument("-p", "--path", required=True, help="JSONL.GZ с токенами (как для train_model)")
    p.add_argument("--vector-sizes", default="100,300", help="Размерности через запятую (по умолчанию 100,300)")
    p.add_argument("--min-counts", default="2,5", help="Значения min_count (по умолчанию 2,5)")
    p.add_argument("--epochs", default="5,10", help="Числа эпох (по умолчанию 5,10)")
    p.add_argument("--windows", default="5", help="Окна контекста (по умолчанию 5)")
    p.add_argument("--sg", type=int, choices=[0, 1], default=1, help="0=CBOW, 1=Skip-gram")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 4, help="Число потоков")
    p.add_argument("-k", type=int, default=10, help="Пара засчитывается, если сосед в топ-k (по умолчанию 10)")
    p.add_argument("--out-csv", help="Сохранить таблицу в CSV")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    configs = grid(_ints(args.vector_sizes), _ints(args.min_counts), _ints(args.epochs), _ints(args.windows))
    print(f"Конфигураций: {len(configs)}")
    results = rank(tune(JsonlGzCorpus(args.path), configs, sg=args.sg, workers=args.workers, k=args.k))

    for r in results:
        quality = (f"пары в топ-{args.k} {r['hit_rate']:.0%}, MRR {r['mrr']:.3f}" if r["pairs"]
                   else "проверочных пар нет в словаре")
        print(f"{r['vector_size']:>4}d min_count={r['min_count']:<2} epochs={r['epochs']:<3} window={r['window']:<2} "
              f"словарь {r['vocab']:>7}, технологий {r['techs']:>3}: {quality}, "
              f"средняя близость {r['mean_similarity']:.3f}{' — вырождена' if r['degenerate'] else ''} "
              f"({r['seconds']} с)")
    best = results[0]
    print(f"\nЛучшее: --vector-size {best['vector_size']} --min-count {best['min_count']} "
          f"--epochs {best['epochs']} --window {best['window']}")
    if best["degenerate"]:
        print("Все модели вырождены: корпус слишком мал, соседи и карта будут шумом (см. PLAN 2.1)")
    if args.out_csv:
        with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(best))
            writer.writeheader()
            writer.writerows(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
