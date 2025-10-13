import json
import gzip
import sys
import argparse
import os
from pathlib import Path
from gensim.models import Word2Vec

class JsonlGzCorpus:
    """Ре-итерируемый корпус: каждая строка JSONL.GZ — список токенов."""
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def __iter__(self):
        with gzip.open(self.path, "rt", encoding="utf-8") as f:
            for line in f:
                tokens = json.loads(line)
                # Ожидаем список строк; игнорируем пустые
                if isinstance(tokens, list) and tokens:
                    yield tokens

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
    return p.parse_args()

def main() -> int:
    args = parse_args()
    src = Path(args.path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sentences = JsonlGzCorpus(src)
    model = Word2Vec(
        sentences=sentences,          # ре-итерируемый корпус
        vector_size=args.vector_size,
        window=args.window,
        min_count=args.min_count,
        workers=args.workers,
        sg=args.sg,
        epochs=args.epochs
    )

    # Базовое имя для артефактов: input без .jsonl.gz
    suffixes = "".join(src.suffixes)
    base = src.name.replace(suffixes, "") if suffixes else src.stem

    model_path = out_dir / f"w2v_{base}_{args.vector_size}d.model"
    txt_path = out_dir / f"w2v_{base}_{args.vector_size}d.txt"

    model.save(model_path.as_posix())
    model.wv.save_word2vec_format(txt_path.as_posix())

    print(f"Сохранено: {model_path} и {txt_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())