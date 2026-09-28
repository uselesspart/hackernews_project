import argparse

import numpy as np
import pandas as pd
from adjustText import adjust_text
from sklearn.manifold import TSNE

from utils.cli import cli_main
from utils.io import read_nonempty_lines
from visualization._common import plt, save_figure


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


def embed_2d(df: pd.DataFrame, labels: list[str], mtype: str) -> np.ndarray:
    """2D-координаты меток через t-SNE по признакам или по матрице близости/расстояний."""
    if mtype == "features":
        data, params = df.loc[labels].to_numpy(), {"metric": "euclidean", "init": "pca"}
    elif mtype in ("similarity", "distance"):
        m = df.loc[labels, labels].to_numpy()
        data = np.clip(1.0 - m, 0.0, None) if mtype == "similarity" else m
        # Для предвычисленных расстояний sklearn допускает только init='random'
        params = {"metric": "precomputed", "init": "random"}
    else:
        raise ValueError(f"Неизвестный тип матрицы: {mtype}")
    tsne = TSNE(n_components=2, random_state=42, perplexity=pick_perplexity(len(labels)), **params)
    return tsne.fit_transform(data)


@cli_main
def main() -> int:
    args = parse_args()
    df = pd.read_csv(args.matrix, index_col=0)
    mtype = detect_matrix_type(df) if args.matrix_type == "auto" else args.matrix_type

    labels = [w for w in read_nonempty_lines(args.tech) if w in df.index] if args.tech else []
    labels = labels or list(df.index)
    if len(labels) < 3:
        raise ValueError(
            "После фильтрации осталось меньше 3 меток. "
            "Для матрицы групп либо не указывайте -t, либо передайте файл с именами групп."
        )

    emb = embed_2d(df, labels, mtype)

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.scatter(emb[:, 0], emb[:, 1], s=100, alpha=0.6)
    texts = [
        ax.text(x, y, label, fontsize=10, bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.5))
        for (x, y), label in zip(emb, labels, strict=True)
    ]
    adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='->', color='gray', lw=0.5), expand_points=(1.5, 1.5))
    ax.set_title('Relationships Map (t-SNE)', fontsize=16)
    ax.set_xlabel('Dimension 1')
    ax.set_ylabel('Dimension 2')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
