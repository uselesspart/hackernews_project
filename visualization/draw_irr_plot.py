import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Отрисовка графика влияния технологий на число комментариев"
    )
    p.add_argument("-i", "--input", required=True, help="Путь к входному файлу")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному файлу")
    return p.parse_args()

def main() -> int:
    try:
        args = parse_args()
        coef_df = pd.read_csv(args.input, encoding='utf-8')
        coef_df = coef_df[coef_df['feature'] != 'const']
        single = coef_df[coef_df['feature'].str.match(r'^has_[^_]+$')].copy()
        single['sig'] = (single['IRR_low'] > 1) | (single['IRR_high'] < 1)
        plot_df = single.sort_values('IRR', ascending=False).head(20).sort_values('IRR')

        sns.set(style='whitegrid')
        plt.figure(figsize=(8, max(6, 0.35*len(plot_df))))
        ypos = np.arange(len(plot_df))
        plt.hlines(ypos, plot_df['IRR_low'], plot_df['IRR_high'], color='gray')
        plt.scatter(plot_df['IRR'], ypos, c=np.where(plot_df['sig'], 'tab:blue', 'tab:orange'), s=60)
        plt.vlines(1.0, -1, len(plot_df), linestyles='dashed', color='red', alpha=0.6)
        plt.yticks(ypos, plot_df['feature'])
        plt.xlabel('IRR (exp(coef))')
        plt.title('Эффект технологий (IRR, 95% CI)')
        plt.tight_layout()
        plt.savefig(args.output, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {args.output}")

        return 0
    except NotADirectoryError as e:
        print(f"Ошибка: {e}")
        return 1
    
if __name__ == "__main__":
    raise SystemExit(main())
