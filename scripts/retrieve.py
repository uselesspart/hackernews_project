import sys
import requests
import json
import argparse
import gzip
import os
import itertools
from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hackernews_retriever import HNRetriever

def iter_hn_ids(start_id=None, end_id=None, session=None):
    sess = session or requests
    if start_id is None or end_id is None:
        r = sess.get("https://hacker-news.firebaseio.com/v0/maxitem.json", timeout=10)
        r.raise_for_status()
        max_id = r.json()
        start_id = start_id or max_id
        end_id = end_id or 1
    step = 1 if start_id <= end_id else -1
    for i in range(start_id, end_id + step, step):
        yield i

def download_items_streaming(id_iter,
                             retriever,
                             out_path="raw_data/hn_data.jsonl.gz",
                             workers=16,
                             compress=True,
                             progress_every=10000):
    opener = gzip.open if compress else open
    mode = "wt" if compress else "w"

    start = perf_counter()
    saved = 0
    errors = 0
    total_seen = 0

    with opener(out_path, mode, encoding="utf-8") as f, requests.Session() as session:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            pending = {}
            for item_id in itertools.islice(id_iter, workers):
                pending[ex.submit(retriever.retrieve_item, item_id, session)] = item_id

            while pending:
                for fut in as_completed(list(pending.keys()), timeout=None):
                    item_id = pending.pop(fut)
                    total_seen += 1
                    try:
                        item = fut.result()
                        if item:
                            f.write(json.dumps(item, ensure_ascii=False) + "\n")
                            saved += 1
                    except Exception:
                        errors += 1

                    try:
                        next_id = next(id_iter)
                    except StopIteration:
                        next_id = None
                    if next_id is not None:
                        pending[ex.submit(retriever.retrieve_item, next_id, session)] = next_id

                    if progress_every and (total_seen % progress_every == 0):
                        elapsed = perf_counter() - start
                        rate = saved / elapsed if elapsed > 0 else 0.0
                        print(f"[seen={total_seen}] saved={saved} errors={errors} "
                              f"elapsed={elapsed:.1f}s rate={rate:.1f} items/s")
                    break

    elapsed = perf_counter() - start
    size_bytes = os.path.getsize(out_path)
    return {
        "saved": saved,
        "seen": total_seen,
        "errors": errors,
        "elapsed": elapsed,
        "size_bytes": size_bytes,
        "out_path": out_path,
    }

def retrieve(path, ids):
    retriever = HNRetriever()
    stats = download_items_streaming(ids, retriever, out_path=path, workers=32, compress=True)
    print(stats)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="hn_retrieve",
        description="Загрузка элементов Hacker News (items) в JSONL(.gz) файл"
    )
    parser.add_argument(
        "-o", "--out",
        default="raw_data/hn_data.jsonl.gz",
        help="Путь к выходному файлу (по умолчанию raw_data/hn_data.jsonl.gz)"
    )
    parser.add_argument(
        "-s", "--start-id",
        type=int,
        default=None,
        help="Начальный ID (если не задан, будет взят maxitem с API)"
    )
    parser.add_argument(
        "-e", "--end-id",
        type=int,
        default=None,
        help="Конечный ID (если не задан, будет 1 при автоматическом выборе maxitem)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=32,
        help="Количество потоков для загрузки (по умолчанию 32)"
    )
    parser.add_argument(
        "--no-compress",
        action="store_false",
        dest="compress",
        help="Сохранить без gzip (по умолчанию включена компрессия)"
    )
    parser.add_argument(
        "-p", "--progress-every",
        type=int,
        default=10000,
        help="Как часто печатать прогресс (в элементах, по умолчанию 10000)"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.workers < 1:
        print("workers должен быть >= 1", file=sys.stderr)
        return 2

    try:
        retriever = HNRetriever()
        ids = iter_hn_ids(args.start_id, args.end_id)
        stats = download_items_streaming(
            ids,
            retriever,
            out_path=args.out,
            workers=args.workers,
            compress=args.compress,
            progress_every=args.progress_every,
        )
        print(
            f"Done: saved={stats['saved']} seen={stats['seen']} errors={stats['errors']} "
            f"elapsed={stats['elapsed']:.1f}s size={stats['size_bytes']}B out={stats['out_path']}"
        )
        return 0
    except KeyboardInterrupt:
        print("Остановлено пользователем (Ctrl+C)", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())