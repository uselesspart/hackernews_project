import argparse
import os

import numpy as np
import pandas as pd
import seaborn as sns

from utils.cli import cli_main
from visualization._common import plt, save_figure


def plot_summary_csv(csv_path, output, sort_by="sentiment_index", ascending=True):
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("CSV пустой.")

    for col in ("file", "mode", "keyword"):
        df[col] = df[col].fillna("").astype(str) if col in df else ""

    # "rust_5.txt" -> "rust"
    tech = df["file"].map(os.path.basename).str.split("_").str[0]
    df["label"] = tech + " (" + df["mode"] + np.where(df["keyword"] != "", ", " + df["keyword"], "") + ")"

    if sort_by not in df.columns or df[sort_by].isna().all():
        sort_by = "sentiment_index"
    df_sorted = df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)

    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(max(8, 0.45 * len(df_sorted)), 6))
    sns.barplot(
        data=df_sorted, x="label", y="sentiment_index", hue="mode", dodge=False, palette="Set2",
        ax=ax, order=pd.unique(df_sorted["label"]).tolist(), errorbar=None,
    )
    ax.tick_params(axis="x", rotation=60)
    for tick in ax.get_xticklabels():
        tick.set_horizontalalignment("right")
    ax.axhline(0, color="k", lw=1)
    ax.set_xlabel("Tech (mode)")
    ax.set_ylabel("Sentiment index")
    ax.set_title("Сравнение технологий по sentiment_index")
    fig.tight_layout()
    save_figure(fig, output)
    return {"bar": output}


def parse_args():
    parser = argparse.ArgumentParser(prog="draw_sentiment_plot",
                                     description="Построение графиков сравнения по сводному CSV.")
    parser.add_argument("-i", "--input", required=True, help="Путь к итоговому CSV (например, corpus_summary.csv).")
    parser.add_argument("-o", "--output", required=True, help="Путь к выходному изображению")
    parser.add_argument("--sort-by", default="sentiment_index",
                        help="Колонка для сортировки (например, sentiment_index, polarity_ratio, mean_score).")
    parser.add_argument("--desc", action="store_true", help="Сортировать по убыванию.")
    return parser.parse_args()


@cli_main
def main():
    args = parse_args()
    plot_summary_csv(args.input, output=args.output, sort_by=args.sort_by, ascending=not args.desc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
