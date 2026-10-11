import argparse

import pandas as pd
from adjustText import adjust_text

from analytics.embeddings.projection import detect_matrix_type, embed_2d
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
