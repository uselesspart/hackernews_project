import re
import argparse
import pandas as pd
import numpy as np
from gensim.models import Word2Vec
from itertools import combinations
from statsmodels.genmod.families import NegativeBinomial
import statsmodels.api as sm
import seaborn as sns
from db.queries import iter_tech_names
from db.session import session_scope
from analytics.embeddings.patterns import PATTERNS

COMPILED: dict[str, re.Pattern] = {
    canon: re.compile("|".join(p.pattern for p in plist), re.IGNORECASE)
    for canon, plist in PATTERNS.items()
}

def extract_tech_regex(text: str) -> list[str]:
    if not isinstance(text, str) or not text:
        return []
    hits = []
    for canon, pat in COMPILED.items():
        m = pat.search(text)
        if m:
            hits.append((canon, m.start()))
    hits_sorted = [canon for canon, _ in sorted(hits, key=lambda x: x[1])]
    return list(dict.fromkeys(hits_sorted))[:3]

def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        
def title_stats(xs, w2v):
    vecs = [w2v.wv[x] for x in xs if x in w2v.wv]
    if len(vecs) <= 1:
        return (0.0, 0.0, 0.0)
    sims = []
    for i in range(len(vecs)):
        for j in range(i+1, len(vecs)):
            sims.append(cos(vecs[i], vecs[j]))
    return (float(np.min(sims)), float(np.mean(sims)), float(np.max(sims)))

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Выгрузка матрицы коэффициентов в файл"
    )
    p.add_argument("-m", "--model", required=True, help="Путь к модели")
    p.add_argument("-i", "--input", required=True, help="Путь к входному файлу")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному файлу")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    try:
        df = pd.read_csv(args.input)
        df['title_clean'] = df['title'].str.lower()
        w2v = Word2Vec.load(args.model)

        try:
            seed_tech = []
            with session_scope(args.db) as session:
                rows = iter_tech_names(session, limit=args.limit)

                for _, name in rows:
                    seed_tech.append(name)
        except:
            seed_tech = ['python','javascript','react','kubernetes','docker','postgresql',
                'redis','csharp','dotnet','java','go','rust','swift','android']

        df['tech_list'] = df['title'].apply(extract_tech_regex)
        df['n_tech'] = df['tech_list'].str.len()

        tech_freq = pd.Series(np.concatenate(df['tech_list'])).value_counts()
        top_tech = tech_freq[tech_freq >= 20].index.tolist()[:50]

        pair_counts = {}
        for xs in df['tech_list']:
            for a, b in combinations(sorted(xs), 2):
                pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1
        pair_df = pd.Series(pair_counts).sort_values(ascending=False)
        top_pairs = [p for p, c in pair_df.items() if c >= 25][:50]

        for t in top_tech:
            df[f'has_{t}'] = df['tech_list'].map(lambda xs: int(t in xs))
        for a, b in top_pairs:
            df[f'has_pair_{a}__{b}'] = df['tech_list'].map(lambda xs: int(a in xs and b in xs))

        df[['sim_min','sim_mean','sim_max']] = pd.DataFrame(
    df['tech_list'].apply(lambda xs: title_stats(xs, w2v)).tolist()
)

        feature_cols = ['techs_count', 'sim_min','sim_mean'] + \
               [f'has_{t}' for t in top_tech] + \
               [f'has_pair_{a}__{b}' for (a,b) in top_pairs]

        X = sm.add_constant(df[feature_cols])
        y = df['descendants']

        model = sm.GLM(y, X, family=NegativeBinomial(alpha=1.0))
        res = model.fit()

        irr = np.exp(res.params)

        sns.set(style='whitegrid')
        params = res.params
        conf = res.conf_int()
        irr = np.exp(params)
        irr_low = np.exp(conf[0])
        irr_high = np.exp(conf[1])
        pvals = res.pvalues

        coef_df = pd.DataFrame({
            'feature': params.index,
            'coef': params.values,
            'IRR': irr.values,
            'IRR_low': irr_low.values,
            'IRR_high': irr_high.values,
            'pval': pvals.values
        })
        conf = res.conf_int()
        coef_df = pd.DataFrame({
            'feature': res.params.index,
            'coef': res.params.values,
            'se': res.bse.values,
            'pval': res.pvalues.values,
            'conf_low': conf[0].values,
            'conf_high': conf[1].values,
        })
        coef_df['IRR'] = np.exp(coef_df['coef'])
        coef_df['IRR_low'] = np.exp(coef_df['conf_low'])
        coef_df['IRR_high'] = np.exp(coef_df['conf_high'])
        coef_df.to_csv(args.output, index=False, encoding='utf-8', float_format='%.8f')

        return 0
    except NotADirectoryError as e:
        print(f"Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
