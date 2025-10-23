import os
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_summary_csv(csv_path, output, sort_by="sentiment_index", ascending=True):
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("CSV пустой.")

    df["file"] = df["file"].fillna("").astype(str)
    df["mode"] = df["mode"].fillna("").astype(str)
    df["keyword"] = df.get("keyword", "").fillna("").astype(str)

    df["file_base"] = df["file"].map(os.path.basename)
    df["file_short"] = df["file_base"].str.split("_").str[0]

    df["label"] = (
        df["file_short"] + " (" + df["mode"] +
        np.where(df["keyword"] != "", ", " + df["keyword"], "") +
        ")"
    )
    if sort_by not in df.columns or df[sort_by].isna().all():
        sort_by = "sentiment_index"
    df_sorted = df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)

    sns.set(style="whitegrid")

    width = max(8, 0.45 * len(df_sorted))
    fig, ax = plt.subplots(figsize=(width, 6))
    order = pd.unique(df_sorted["label"]).tolist()
    sns.barplot(
    data=df_sorted,
    x="label", y="sentiment_index",
    hue="mode", dodge=False, palette="Set2", ax=ax,
    order=order, errorbar=None
)
    ax.tick_params(axis="x", rotation=60)
    for tick in ax.get_xticklabels():
        tick.set_horizontalalignment("right")
    ax.axhline(0, color="k", lw=1)
    ax.set_xlabel("Tech (mode)")
    ax.set_ylabel("Sentiment index")
    ax.set_title("Сравнение технологий по sentiment_index")
    ax.tick_params(axis="x", rotation=60)
    plt.tight_layout()
    fig.savefig(output, dpi=300)
    plt.close(fig)

    return {"bar": output}

def parse_args():
    parser = argparse.ArgumentParser(description="Построение графиков сравнения по сводному CSV.")
    parser.add_argument("-i", "--input", type=str, required=True, help="Путь к итоговому CSV (например, corpus_summary.csv).")
    parser.add_argument("-o", "--output", type=str, required=True, default="plots", help="Путь к файлу csv")
    parser.add_argument("--sort-by", type=str, default="sentiment_index",
                        help="Колонка для сортировки (например, sentiment_index, polarity_ratio, mean_score).")
    parser.add_argument("--desc", action="store_true", help="Сортировать по убыванию.")
    return parser.parse_args()

def main():
    args = parse_args()
    try:
        paths = plot_summary_csv(args.input, output=args.output, sort_by=args.sort_by, ascending=(not args.desc))
        print("График сохранен:")
        for k, p in paths.items():
            if p:
                print(f"{k}: {p}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
