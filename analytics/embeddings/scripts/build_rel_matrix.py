import numpy as np
import pandas as pd
import argparse
import importlib.util
from gensim.models import Word2Vec
from utils.groups import categories as RAW_CATEGORIES 
from sklearn.metrics.pairwise import cosine_similarity

def normalize_token(name: str) -> str:
    return name.strip().lower().replace(" ", "_")

def normalize_categories_dict(raw: dict) -> dict:
    norm = {}
    for g, arr in raw.items():
        # нормализуем и удаляем дубликаты, сохраняя порядок
        seen = set()
        norm_tokens = []
        for x in arr:
            t = normalize_token(x)
            if t not in seen:
                seen.add(t)
                norm_tokens.append(t)
        norm[str(g)] = norm_tokens
    return norm

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
            vecs = np.stack([kv.get_vector(t) for t in members])
            gvec = vecs.mean(axis=0)
            group_names.append(gname)
            group_vectors.append(gvec)
            group_members[gname] = members

    if len(group_names) < 2:
        raise ValueError(
            "Недостаточно групп после фильтрации (нужно ≥ 2). "
            "Проверьте входные слова и параметр --min-group-size."
        )

    return group_names, np.stack(group_vectors), group_members


def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Выгрузка матрицы отношений (слов или групп) в файл"
    )
    p.add_argument("-i", "--input", required=True, help="Путь к файлу со словами (по одному в строке)")
    p.add_argument("-m", "--model", required=True, help="Путь к модели gensim Word2Vec (.model)")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному CSV")

    # Режим групп (включить/выключить)
    p.add_argument("--groups", action="store_true",
                   help="Строить матрицу по группам из utils.groups.categories")
    p.add_argument("--min-group-size", type=int, default=1,
                   help="Минимум слов из входа, попавших в группу, чтобы она вошла в матрицу (по умолчанию 1).")

    # Метрика (схожесть или расстояние)
    p.add_argument("--distance", action="store_true",
                   help="Сохранять косинусные расстояния (1 - cosine similarity) вместо схожести.")

    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        tech = []
        with open(args.input, 'r', encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s:
                    tech.append(s)

        model = Word2Vec.load(args.model)
        kv = model.wv

        # Общая подготовка входных токенов
        _, tokens = collect_tokens(kv, tech)

        if args.groups:
            # Нормализуем категории единожды
            CATEGORIES = normalize_categories_dict(RAW_CATEGORIES)

            # Режим агрегации по группам
            group_names, group_vecs, group_members = group_vectors_from_tokens(
                kv, tokens, CATEGORIES, min_group_size=args.min_group_size
            )
            sim = cosine_similarity(group_vecs)
            mat = 1.0 - sim if args.distance else sim
            df = pd.DataFrame(mat, index=group_names, columns=group_names)

            # Для контроля — какие слова вошли в каждую группу
            for g, members in group_members.items():
                print(f"[GROUP] {g}: {', '.join(members)}")

        else:
            # Обычный режим — по словам
            embedding_matrix = np.stack([kv.get_vector(w) for w in tokens])
            sim = cosine_similarity(embedding_matrix)
            mat = 1.0 - sim if args.distance else sim
            df = pd.DataFrame(mat, index=tokens, columns=tokens)

        df.to_csv(args.output, encoding="utf-8")
        return 0

    except Exception as e:
        print(f"Ошибка: {e}")
        return 1



if __name__ == "__main__":
    raise SystemExit(main())