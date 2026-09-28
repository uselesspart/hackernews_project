import argparse
import gzip
import itertools
import json
import os
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from time import perf_counter

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from hackernews_retriever import HNRetriever
from utils.cli import cli_main


def make_session(workers: int) -> requests.Session:
    """
    Пул соединений по числу потоков (по умолчанию в requests он 10, и при 32 потоках
    лишние соединения закрываются после каждого запроса) и повтор при сбоях/429/5xx.
    """
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",))
    adapter = HTTPAdapter(pool_connections=1, pool_maxsize=workers, max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def iter_hn_ids(start_id=None, end_id=None, session=None, retriever=None):
    """ID от start_id до end_id включительно (в любую сторону); по умолчанию — от maxitem до 1."""
    if start_id is None or end_id is None:
        max_id = (retriever or HNRetriever()).get_maxitem_id(session)
        start_id = start_id or max_id
        end_id = end_id or 1
    step = 1 if start_id <= end_id else -1
    yield from range(start_id, end_id + step, step)


def download_items_streaming(id_iter,
                             retriever,
                             out_path="raw_data/hn_data.jsonl.gz",
                             workers=16,
                             compress=True,
                             progress_every=10000):
    start = perf_counter()
    saved = 0
    errors = 0
    total_seen = 0
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if compress else open

    with (
        opener(out_path, "wt", encoding="utf-8") as f,
        make_session(workers) as session,
        ThreadPoolExecutor(max_workers=workers) as ex,
    ):
        # Держим в работе ~2 задачи на поток, чтобы потоки не простаивали между выдачами
        pending = {ex.submit(retriever.retrieve_item, item_id, session)
                   for item_id in itertools.islice(id_iter, workers * 2)}

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for fut in done:
                total_seen += 1
                try:
                    item = fut.result()
                    if item:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
                        saved += 1
                except Exception:
                    errors += 1

                next_id = next(id_iter, None)
                if next_id is not None:
                    pending.add(ex.submit(retriever.retrieve_item, next_id, session))

                if progress_every and (total_seen % progress_every == 0):
                    elapsed = perf_counter() - start
                    rate = saved / elapsed if elapsed > 0 else 0.0
                    print(f"[seen={total_seen}] saved={saved} errors={errors} "
                          f"elapsed={elapsed:.1f}s rate={rate:.1f} items/s")

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

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="retrieve",
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


@cli_main
def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("workers должен быть >= 1")

    retriever = HNRetriever()
    stats = download_items_streaming(
        iter_hn_ids(args.start_id, args.end_id, retriever=retriever),
        retriever,
        out_path=args.out,
        workers=args.workers,
        compress=args.compress,
        progress_every=args.progress_every,
    )
    print(
        f"Готово: сохранено={stats['saved']} просмотрено={stats['seen']} ошибок={stats['errors']} "
        f"время={stats['elapsed']:.1f}s размер={stats['size_bytes']}B файл={stats['out_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
