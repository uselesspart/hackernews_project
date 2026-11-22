"""Compare adjusted IRR across periods, frequency cutoffs and model specifications."""
import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sqlalchemy import select

from analytics.embeddings.scripts.calculate_irr import compute_irr
from db import session_scope
from db.models import Story
from db.queries import is_alive
from utils.cli import cli_main

matplotlib.use('Agg')
from matplotlib import pyplot as plt  # noqa: E402


def run_stability(df, min_freq=30):
    df = df.sort_values(['time', 'id']).reset_index(drop=True)
    midpoint = df.time.iloc[len(df) // 2]
    variants = [('full', df, 'negbin', True, min_freq),
                ('early', df[df.time < midpoint], 'negbin', True, min_freq),
                ('late', df[df.time >= midpoint], 'negbin', True, min_freq),
                ('min60', df, 'negbin', True, 60), ('min100', df, 'negbin', True, 100),
                ('no_controls', df, 'negbin', False, min_freq),
                ('calendar', df, 'negbin', True, min_freq),
                ('poisson_robust', df, 'poisson', True, min_freq)]
    rows, diagnostics = [], {}
    for name, data, family, controls, cutoff in variants:
        print(f'Fitting {name}: {len(data)} stories', flush=True)
        try:
            table = compute_irr(data, family=family, controls=controls, top_n=None,
                                min_freq=cutoff, interactions=False, calendar=name == 'calendar')
            diag = table.attrs['diagnostics']
            diagnostics[name] = diag | dict(period_start=str(data.time.min()), period_end=str(data.time.max()))
            if not diag['converged']:
                diagnostics[name]['error'] = 'Model did not converge'
                continue
            for r in table.itertuples():
                key = r.feature.removeprefix('has_')
                if key not in diag['tech_frequencies']:
                    continue
                if not np.isfinite([r.IRR, r.IRR_low, r.IRR_high, r.pval]).all():
                    continue
                if not 0 < r.IRR_low <= r.IRR <= r.IRR_high or not 0 <= r.pval <= 1:
                    continue
                rows.append(dict(variant=name, tech=key, irr=r.IRR, low=r.IRR_low, high=r.IRR_high,
                                 pval=r.pval, qval_bh=r.qval_bh, n=diag['tech_frequencies'][key]))
        except (ValueError, np.linalg.LinAlgError) as exc:
            diagnostics[name] = dict(error=str(exc))
    return pd.DataFrame(rows), diagnostics


def forest_plot(results, destination, limit=15, periods=None):
    full = results[results.variant == 'full'].nlargest(limit, 'n')
    techs = list(full.tech)[::-1]
    fig, ax = plt.subplots(figsize=(11, max(5, len(techs) * .42)))
    variants = [('full', 0, '#2563eb'), ('early', -.22, '#d97706'), ('late', .22, '#059669')]
    for variant, offset, color in variants:
        subset = results[(results.variant == variant) & results.tech.isin(techs)]
        positions = np.array([techs.index(key) for key in subset.tech]) + offset
        label = variant
        if periods and variant in periods:
            info = periods[variant]
            label += f": {info['period_start'][:10]} to {info['period_end'][:10]}"
        ax.errorbar(subset.irr, positions, xerr=[subset.irr - subset.low, subset.high - subset.irr],
                    fmt='o', markersize=4, capsize=2, label=label, color=color)
    ax.axvline(1, color='#6b7280', linestyle='--')
    ax.set_xscale('log')
    ax.set_yticks(range(len(techs)), techs)
    ax.set_xlabel('Adjusted IRR with 95% Wald confidence intervals (log scale)')
    fig.suptitle('Hacker News: full period and chronological halves', y=.98, fontsize=14)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, .94), ncol=3, fontsize=8)
    ax.grid(axis='x', alpha=.2)
    fig.text(.02, .015, 'Observational associations; intervals conditional on dispersion. '
             'BH-adjusted p-values are provided in the companion CSV; intervals are not simultaneous.',
             fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, .88))
    for suffix in ('png', 'svg'):
        fig.savefig(destination.with_suffix('.' + suffix), dpi=180)
    plt.close(fig)


@cli_main
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', required=True)
    p.add_argument('--output-dir', required=True)
    args = p.parse_args()
    with session_scope(args.db) as session:
        data = session.execute(select(Story.id, Story.title, Story.descendants, Story.url, Story.time).where(
            is_alive(Story), Story.title.isnot(None), Story.time.isnot(None), Story.descendants >= 0)).all()
    results, diagnostics = run_stability(pd.DataFrame(data, columns=['id', 'title', 'descendants', 'url', 'time']))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results.to_csv(out / 'irr_stability.csv', index=False)
    (out / 'diagnostics.json').write_text(json.dumps(diagnostics, indent=2, allow_nan=False), encoding='utf-8')
    if not results.empty:
        forest_plot(results, out / 'irr_periods', periods=diagnostics)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
