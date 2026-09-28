import argparse

import numpy as np
import pandas as pd
import seaborn as sns

from utils.cli import cli_main
from visualization._common import plt, save_figure

TOP_N = 20


def single_tech_effects(coef_df: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    """Строки has_<tech> (без пар), топ-N по IRR, в порядке возрастания для горизонтального графика."""
    feature = coef_df['feature'].fillna("")
    single = coef_df[feature.str.startswith('has_') & ~feature.str.startswith('has_pair_')].copy()
    single['sig'] = (single['IRR_low'] > 1) | (single['IRR_high'] < 1)
    return single.sort_values('IRR', ascending=False).head(top_n).sort_values('IRR')


def parse_args():
    p = argparse.ArgumentParser(
        prog="draw_irr_plot",
        description="Отрисовка графика влияния технологий на число комментариев"
    )
    p.add_argument("-i", "--input", required=True, help="CSV с коэффициентами (calculate_irr)")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному изображению")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    plot_df = single_tech_effects(pd.read_csv(args.input, encoding='utf-8'))

    sns.set(style='whitegrid')
    fig, ax = plt.subplots(figsize=(8, max(6, 0.35 * len(plot_df))))
    ypos = np.arange(len(plot_df))
    ax.hlines(ypos, plot_df['IRR_low'], plot_df['IRR_high'], color='gray')
    ax.scatter(plot_df['IRR'], ypos, c=np.where(plot_df['sig'], 'tab:blue', 'tab:orange'), s=60)
    ax.vlines(1.0, -1, len(plot_df), linestyles='dashed', color='red', alpha=0.6)
    ax.set_yticks(ypos, plot_df['feature'])
    ax.set_xlabel('IRR (exp(coef))')
    ax.set_title('Эффект технологий (IRR, 95% CI)')
    fig.tight_layout()
    save_figure(fig, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
