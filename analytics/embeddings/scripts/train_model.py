import json
import gzip
import argparse
import os
from pathlib import Path
from typing import Dict, List, Pattern
import numpy as np
import pandas as pd
from gensim.models import Word2Vec

class JsonlGzCorpus:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def __iter__(self):
        with gzip.open(self.path, "rt", encoding="utf-8") as f:
            for line in f:
                tokens = json.loads(line)
                # Ожидаем список строк; игнорируем пустые
                if isinstance(tokens, list) and tokens:
                    yield tokens

def load_patterns():
    try:
        from analytics.embeddings.patterns import PATTERNS
        return PATTERNS
    except ImportError:
        print("Warning: patterns.py not found. Synonym aggregation disabled.")
        return None

def aggregate_synonyms(model: Word2Vec, patterns_dict: Dict[str, List[Pattern]]) -> pd.DataFrame:
    vocab = set(model.wv.index_to_key)
    aggregated_vectors = []
    canonical_names = []
    stats = []
    
    for canonical_name, patterns in patterns_dict.items():
        matching_words = []
        for word in vocab:
            for pattern in patterns:
                if pattern.search(word):
                    matching_words.append(word)
                    break
        
        if matching_words:
            word_counts = [model.wv.get_vecattr(word, "count") for word in matching_words]
            
            vectors = np.array([model.wv[word] for word in matching_words])
            weights = np.array(word_counts, dtype=float)
            weights = weights / weights.sum()
            
            avg_vector = np.average(vectors, axis=0, weights=weights)
            
            aggregated_vectors.append(avg_vector)
            canonical_names.append(canonical_name)
            
            total_count = sum(word_counts)
            stats.append({
                'canonical': canonical_name,
                'matches': len(matching_words),
                'total_count': total_count,
                'examples': matching_words[:5]
            })
    
    print(f"\n=== Synonym Aggregation Stats ===")
    for stat in sorted(stats, key=lambda x: x['total_count'], reverse=True)[:20]:
        print(f"{stat['canonical']:20s}: {stat['matches']:3d} words, "
              f"count={stat['total_count']:6d}, examples={stat['examples']}")
    
    df = pd.DataFrame(aggregated_vectors, index=canonical_names)
    return df

def save_aggregated_embeddings(df: pd.DataFrame, output_path: Path):
    csv_path = output_path.with_suffix('.aggregated.csv')
    df.to_csv(csv_path)
    print(f"Saved aggregated embeddings (CSV): {csv_path}")
    
    txt_path = output_path.with_suffix('.aggregated.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"{len(df)} {df.shape[1]}\n")
        for word, vector in df.iterrows():
            vector_str = ' '.join(map(str, vector.values))
            f.write(f"{word} {vector_str}\n")
    print(f"Saved aggregated embeddings (TXT): {txt_path}")

def parse_args():
    p = argparse.ArgumentParser(
        prog="train_w2v",
        description="Тренировка Word2Vec по токенам из JSONL.GZ (одна строка = список токенов)"
    )
    p.add_argument("-p", "--path", required=True, help="Путь к файлу JSONL.GZ с токенами")
    p.add_argument("-o", "--out-dir", default="artifacts/embeddings/words", help="Директория для сохранения модели/векторов")
    p.add_argument("--vector-size", type=int, default=300, help="Размерность эмбеддингов")
    p.add_argument("--window", type=int, default=5, help="Окно контекста")
    p.add_argument("--min-count", type=int, default=2, help="Минимальная частота токена")
    p.add_argument("--sg", type=int, choices=[0, 1], default=1, help="0=CBOW, 1=Skip-gram")
    p.add_argument("--epochs", type=int, default=5, help="Число эпох обучения")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 4, help="Число потоков")
    p.add_argument("--aggregate-synonyms", action="store_true", 
                   help="Агрегировать синонимы из patterns.py после обучения")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    src = Path(args.path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Обучение модели
    print(f"Training Word2Vec on {src}...")
    sentences = JsonlGzCorpus(src)
    model = Word2Vec(
        sentences=sentences,
        vector_size=args.vector_size,
        window=args.window,
        min_count=args.min_count,
        workers=args.workers,
        sg=args.sg,
        epochs=args.epochs
    )

    # Генерация базового имени файла
    suffixes = "".join(src.suffixes)
    base = src.name.replace(suffixes, "") if suffixes else src.stem

    # Сохранение оригинальной модели
    model_path = out_dir / f"w2v_{base}_{args.vector_size}d.model"
    txt_path = out_dir / f"w2v_{base}_{args.vector_size}d.txt"
    csv_path = out_dir / f"w2v_{base}_{args.vector_size}d.csv"

    model.save(model_path.as_posix())
    model.wv.save_word2vec_format(txt_path.as_posix())
    
    # Сохранение в CSV для удобства
    df_all = pd.DataFrame(
        [model.wv[word] for word in model.wv.index_to_key],
        index=model.wv.index_to_key
    )
    df_all.to_csv(csv_path)

    print(f"Saved original model: {model_path}")
    print(f"Saved original vectors: {txt_path}")
    print(f"Saved original vectors (CSV): {csv_path}")
    print(f"Vocabulary size: {len(model.wv)}")

    # Агрегация синонимов (опционально)
    if args.aggregate_synonyms:
        patterns_dict = load_patterns()
        if patterns_dict:
            print("\nAggregating synonyms based on patterns.py...")
            df_aggregated = aggregate_synonyms(model, patterns_dict)
            
            aggregated_base_path = out_dir / f"w2v_{base}_{args.vector_size}d"
            save_aggregated_embeddings(df_aggregated, aggregated_base_path)
            
            print(f"Aggregated vocabulary size: {len(df_aggregated)}")
        else:
            print("Skipping synonym aggregation (patterns.py not available)")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())