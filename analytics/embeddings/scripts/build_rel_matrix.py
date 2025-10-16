import numpy as np
import pandas as pd
import argparse
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

def normalize_token(name: str) -> str:
    return name.strip().lower().replace(" ", "_")

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

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Выгрузка матрицы отношений в файл"
    )
    p.add_argument("-i", "--input", required=True, help="Путь к файлу")
    p.add_argument("-m", "--model", required=True, help="Путь к модели")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному файлу")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    try:
        tech = []
        with open(args.input, 'r') as f:
            for line in f:
                tech.append(line.strip())

        model = Word2Vec.load(args.model)
        kv = model.wv
        names, tokens = collect_tokens(kv, tech)
        embedding_matrix = np.stack([kv.get_vector(w) for w in tokens])
        cosine_matrix = cosine_similarity(embedding_matrix)
        df_sim = pd.DataFrame(cosine_matrix, index=tokens, columns=tokens)
        df_sim.to_csv(args.output , encoding="utf-8")

        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())