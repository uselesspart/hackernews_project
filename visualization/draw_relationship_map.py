import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from adjustText import adjust_text


def parse_args():
    p = argparse.ArgumentParser(
        prog="draw_relationship_map",
        description="Отрисовка карты отношений между объектами"
    )
    p.add_argument("-m", "--matrix", required=True, help="Путь к CSV с матрицей (схожести/расстояний или фич)")
    p.add_argument("-t", "--tech", help="Путь к файлу со списком меток (опционально)")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному изображению")

    p.add_argument("--matrix-type", choices=["auto", "features", "similarity", "distance"],
                   default="auto", help="Тип входной матрицы (по умолчанию auto)")
    return p.parse_args()


def pick_perplexity(n: int) -> float:
    # t-SNE требует 0 < perplexity < n_samples
    if n < 3:
        raise ValueError("Нужно минимум 3 объекта для t-SNE.")
    # Всегда строго меньше n
    return float(min(30, n - 1))


def detect_matrix_type(df: pd.DataFrame) -> str:
    if df.shape[0] == df.shape[1] and list(df.index) == list(df.columns):
        m = df.to_numpy()
        d = np.diag(m)
        if np.allclose(d, 1.0, atol=1e-3):
            return "similarity"
        if np.allclose(d, 0.0, atol=1e-3):
            return "distance"
        if np.nanmin(m) >= -1.0 and np.nanmax(m) <= 1.5 and np.nanmax(d) >= 0.9:
            return "similarity"
        return "distance"
    return "features"


def main() -> int:
    args = parse_args()
    try:
        df = pd.read_csv(args.matrix, index_col=0)

        mtype = args.matrix_type
        if mtype == "auto":
            mtype = detect_matrix_type(df)

        labels = None
        if args.tech:
            with open(args.tech, "r", encoding="utf-8") as f:
                file_labels = [line.strip() for line in f if line.strip()]
            labels = [w for w in file_labels if w in df.index]

        if not labels:
            labels = list(df.index)

        if len(labels) < 3:
            raise ValueError(
                "После фильтрации осталось меньше 3 меток. "
                "Для матрицы групп либо не указывайте -t, либо передайте файл с именами групп."
            )

        if mtype == "features":
            X = df.loc[labels].to_numpy()
            tsne = TSNE(
                n_components=2,
                random_state=42,
                perplexity=pick_perplexity(len(labels)),
                metric="euclidean",
                init="pca"  # допустимо для признаков
            )
            emb = tsne.fit_transform(X)

        else:
            M = df.loc[labels, labels].to_numpy()
            if mtype == "similarity":
                D = 1.0 - M
                D = np.clip(D, 0.0, None)
            elif mtype == "distance":
                D = M
            else:
                raise ValueError(f"Неизвестный тип матрицы: {mtype}")

            # ВАЖНО: для предвычисленных расстояний init должен быть 'random'
            tsne = TSNE(
                n_components=2,
                random_state=42,
                perplexity=pick_perplexity(len(labels)),
                metric="precomputed",
                init="random"  # <-- фикс ошибки init='pca' с metric='precomputed'
            )
            emb = tsne.fit_transform(D)

        plt.figure(figsize=(12, 8))
        plt.scatter(emb[:, 0], emb[:, 1], s=100, alpha=0.6)

        texts = []
        for i, label in enumerate(labels):
            txt = plt.text(
                emb[i, 0], emb[i, 1], label,
                fontsize=10, bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.5)
            )
            texts.append(txt)

        adjust_text(
            texts,
            arrowprops=dict(arrowstyle='->', color='gray', lw=0.5),
            expand_points=(1.5, 1.5)
        )

        plt.title('Relationships Map (t-SNE)', fontsize=16)
        plt.xlabel('Dimension 1')
        plt.ylabel('Dimension 2')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # Создаем директории, если их нет
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {out_path}")
        return 0

    except Exception as e:
        print(f"Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())