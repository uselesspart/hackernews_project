import argparse

import numpy as np
import pandas as pd
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

from utils.cli import cli_main
from utils.groups import categories as RAW_CATEGORIES
from utils.groups import normalize_categories, normalize_token
from utils.io import read_nonempty_lines


def collect_tokens(kv, rows):
    names, tokens = [], []
    for name in rows:
        tok = normalize_token(name)
        if tok in kv.key_to_index:
            names.append(name)
            tokens.append(tok)
    if len(tokens) < 2:
        raise ValueError("Недостаточно токенов в словаре модели (нужно ≥ 2).")
    return names, tokens


def group_vectors_from_tokens(kv, tokens, categories: dict, min_group_size: int = 1):
    token_set = set(tokens)
    group_names = []
    group_vectors = []
    group_members = {}

    for gname, g_tokens in categories.items():
        # Оставляем только те слова, которые есть во входе и в модели
        members = [t for t in g_tokens if t in token_set and t in kv.key_to_index]
        if len(members) >= min_group_size:
            group_names.append(gname)
            group_vectors.append(np.stack([kv.get_vector(t) for t in members]).mean(axis=0))
            group_members[gname] = members

    if len(group_names) < 2:
        raise ValueError(
            "Недостаточно групп после фильтрации (нужно ≥ 2). "
            "Проверьте входные слова и параметр --min-group-size."
        )

    return group_names, np.stack(group_vectors), group_members


def parse_args():
    p = argparse.ArgumentParser(
        prog="build_rel_matrix",
        description="Матрица косинусной близости (или расстояния) между технологиями или их группами"
    )
    p.add_argument("-i", "--input", required=True, help="Путь к файлу со словами (по одному в строке)")
    p.add_argument("-m", "--model", required=True, help="Путь к модели gensim Word2Vec (.model)")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному CSV")
    p.add_argument("--groups", action="store_true",
                   help="Строить матрицу по группам из utils.groups.categories")
    p.add_argument("--min-group-size", type=int, default=1,
                   help="Минимум слов из входа, попавших в группу, чтобы она вошла в матрицу (по умолчанию 1).")
    p.add_argument("--distance", action="store_true",
                   help="Сохранять косинусные расстояния (1 - cosine similarity) вместо схожести.")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    kv = Word2Vec.load(args.model).wv
    _, tokens = collect_tokens(kv, read_nonempty_lines(args.input))

    if args.groups:
        names, vectors, group_members = group_vectors_from_tokens(
            kv, tokens, normalize_categories(RAW_CATEGORIES), min_group_size=args.min_group_size
        )
        # Для контроля — какие слова вошли в каждую группу
        for g, members in group_members.items():
            print(f"[GROUP] {g}: {', '.join(members)}")
    else:
        names, vectors = tokens, np.stack([kv.get_vector(w) for w in tokens])

    sim = cosine_similarity(vectors)
    mat = 1.0 - sim if args.distance else sim
    pd.DataFrame(mat, index=names, columns=names).to_csv(args.output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
