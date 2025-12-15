import re
import argparse
import pandas as pd
import numpy as np
from gensim.models import Word2Vec
from itertools import combinations
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')
from db.queries import iter_tech_names
from db.session import session_scope
from analytics.embeddings.patterns import PATTERNS
from utils.groups import categories as RAW_CATEGORIES  # <-- прямой импорт категорий


COMPILED: dict[str, re.Pattern] = {
    canon: re.compile("|".join(p.pattern for p in plist), re.IGNORECASE)
    for canon, plist in PATTERNS.items()
}


def normalize_token(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def normalize_categories_dict(raw: dict) -> dict:
    norm = {}
    for g, arr in raw.items():
        seen = set()
        norm_tokens = []
        for x in arr:
            t = normalize_token(x)
            if t not in seen:
                seen.add(t)
                norm_tokens.append(t)
        norm[str(g)] = norm_tokens
    return norm


def build_group_maps(w2v: Word2Vec, raw_categories: dict):
    """
    Возвращает:
      - group_to_tokens: dict[group -> list[str]] (только токены, присутствующие в модели)
      - token_to_groups: dict[token -> list[group]]
      - group_vecs: dict[group -> np.ndarray] средний вектор группы
    """
    kv = w2v.wv
    cats = normalize_categories_dict(raw_categories)

    group_to_tokens: dict[str, list[str]] = {}
    for g, toks in cats.items():
        present = [t for t in toks if t in kv.key_to_index]
        if present:
            group_to_tokens[g] = present

    # Вектора групп
    group_vecs: dict[str, np.ndarray] = {}
    for g, toks in group_to_tokens.items():
        vecs = np.stack([kv.get_vector(t) for t in toks])
        group_vecs[g] = vecs.mean(axis=0)

    # Обратный маппинг: токен -> группы
    token_to_groups: dict[str, list[str]] = {}
    for g, toks in group_to_tokens.items():
        for t in toks:
            token_to_groups.setdefault(t, []).append(g)

    return group_to_tokens, token_to_groups, group_vecs


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
    """Compute cosine similarity with safety checks"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    sim = np.dot(a, b) / (norm_a * norm_b)
    sim = np.clip(sim, -1.0, 1.0)
    return float(sim)


def title_stats_tokens(xs: list[str], w2v: Word2Vec):
    """Схожесть по токенам через модель"""
    if not xs:
        return (0.0, 0.0, 0.0)
    kv = w2v.wv
    vecs = []
    for x in xs:
        if x in kv:
            try:
                vec = kv[x]
                if not np.any(np.isnan(vec)) and not np.any(np.isinf(vec)):
                    vecs.append(vec)
            except:
                continue
    if len(vecs) <= 1:
        return (0.0, 0.0, 0.0)
    sims = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            sim = cos(vecs[i], vecs[j])
            if not np.isnan(sim) and not np.isinf(sim):
                sims.append(sim)
    if not sims:
        return (0.0, 0.0, 0.0)
    return (float(np.min(sims)), float(np.mean(sims)), float(np.max(sims)))


def title_stats_vecmap(xs: list[str], vec_map: dict[str, np.ndarray]):
    """Схожесть по предвычисленным векторам (для групп)"""
    if not xs:
        return (0.0, 0.0, 0.0)
    vecs = []
    for x in xs:
        v = vec_map.get(x)
        if v is not None and not np.any(np.isnan(v)) and not np.any(np.isinf(v)):
            vecs.append(v)
    if len(vecs) <= 1:
        return (0.0, 0.0, 0.0)
    sims = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            sim = cos(vecs[i], vecs[j])
            if not np.isnan(sim) and not np.isinf(sim):
                sims.append(sim)
    if not sims:
        return (0.0, 0.0, 0.0)
    return (float(np.min(sims)), float(np.mean(sims)), float(np.max(sims)))


def parse_args():
    p = argparse.ArgumentParser(
        prog="calculate_irr",
        description="Calculate IRR coefficients"
    )
    p.add_argument("-m", "--model", required=True, help="Path to model")
    p.add_argument("-i", "--input", required=True, help="Path to input file")
    p.add_argument("-o", "--output", required=True, help="Path to output file")
    p.add_argument("--db", help="Database connection string", default=None)
    p.add_argument("--limit", type=int, help="Limit for tech names", default=None)
    p.add_argument("--sample", type=int, help="Sample N rows (for testing)", default=None)
    p.add_argument("--max-rows", type=int, help="Maximum rows to process", default=500000)

    # Новый флаг групп
    p.add_argument("--groups", action="store_true",
                   help="Агрегировать технологии в группы из utils.groups.categories")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        print("Loading data...")
        df = pd.read_csv(args.input, usecols=['title', 'descendants'])

        print(f"Original data: {len(df)} rows")
        print(f"Descendants range: min={df['descendants'].min()}, max={df['descendants'].max()}")

        # Filter out invalid descendants values
        df = df[df['descendants'] >= 0].copy()
        print(f"After filtering negative descendants: {len(df)} rows")

        # Apply max rows limit to avoid memory issues
        if len(df) > args.max_rows:
            print(f"Sampling {args.max_rows} rows from {len(df)} to avoid memory issues...")
            df = df.sample(n=args.max_rows, random_state=42).copy()

        # Sample if requested
        if args.sample:
            print(f"Sampling {args.sample} rows...")
            df = df.sample(n=min(args.sample, len(df)), random_state=42).copy()

        print(f"Processing {len(df)} rows...")

        print("Loading Word2Vec model...")
        w2v = Word2Vec.load(args.model)

        # (Необязательная) подкачка сидов из БД — как и раньше
        try:
            seed_tech = []
            with session_scope(args.db) as session:
                rows = iter_tech_names(session, limit=args.limit)
                for _, name in rows:
                    seed_tech.append(name)
        except:
            seed_tech = ['python','javascript','react','kubernetes','docker','postgresql',
                'redis','csharp','dotnet','java','go','rust','swift','android']

        print("Extracting technologies from titles...")
        df['tech_list'] = df['title'].apply(extract_tech_regex)
        df.drop(columns=['title'], inplace=True)
        df['n_tech'] = df['tech_list'].str.len()

        # Если включён режим групп — маппим технологии в группы и заменяем списки
        group_vecs = None
        if args.groups:
            print("Grouping technologies into categories...")
            _, token_to_groups, group_vecs = build_group_maps(w2v, RAW_CATEGORIES)

            def map_tokens_to_groups(xs: list[str]) -> list[str]:
                out = []
                for t in xs:
                    gs = token_to_groups.get(t, [])
                    out.extend(gs)
                # дедуп, сохранение порядка
                seen = set()
                dedup = []
                for g in out:
                    if g not in seen and g in group_vecs:
                        seen.add(g)
                        dedup.append(g)
                return dedup

            df['tech_list'] = df['tech_list'].apply(map_tokens_to_groups)
            df['n_tech'] = df['tech_list'].str.len()
            print("Grouping complete.")

        print("Computing technology frequencies...")
        all_labels = [t for xs in df['tech_list'] for t in xs]
        if not all_labels:
            raise ValueError("Не удалось извлечь ни одной технологии/группы из заголовков.")
        tech_freq = pd.Series(all_labels).value_counts()
        del all_labels

        top_tech = tech_freq[tech_freq >= 20].index.tolist()[:50]
        print(f"Found {len(top_tech)} top {'groups' if args.groups else 'technologies'}")

        print("Computing pair frequencies...")
        pair_counts: dict[tuple[str, str], int] = {}
        for xs in df['tech_list']:
            for a, b in combinations(sorted(xs), 2):
                pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1
        pair_df = pd.Series(pair_counts).sort_values(ascending=False)
        top_pairs = [p for p, c in pair_df.items() if c >= 25][:50]
        print(f"Found {len(top_pairs)} top pairs")
        del pair_counts, pair_df

        print("Building feature columns...")
        feature_data: dict[str, pd.Series] = {}

        for t in top_tech:
            feature_data[f'has_{t}'] = df['tech_list'].apply(lambda xs: t in xs).astype(np.int8)

        for a, b in top_pairs:
            feature_data[f'has_pair_{a}__{b}'] = df['tech_list'].apply(
                lambda xs, aa=a, bb=b: (aa in xs and bb in xs)
            ).astype(np.int8)

        print("Computing similarity statistics (this may take a while)...")
        batch_size = 1000
        sim_results = []

        if args.groups:
            # Используем предвычисленные векторы групп
            for i in range(0, len(df), batch_size):
                if i % 50000 == 0:
                    print(f"  Processing batch {i}/{len(df)}...")
                batch = df['tech_list'].iloc[i:i+batch_size]
                batch_results = batch.apply(lambda xs: title_stats_vecmap(xs, group_vecs))
                sim_results.extend(batch_results.tolist())
        else:
            # Как раньше — по токенам из модели
            for i in range(0, len(df), batch_size):
                if i % 50000 == 0:
                    print(f"  Processing batch {i}/{len(df)}...")
                batch = df['tech_list'].iloc[i:i+batch_size]
                batch_results = batch.apply(lambda xs: title_stats_tokens(xs, w2v))
                sim_results.extend(batch_results.tolist())

        sim_df = pd.DataFrame(sim_results, columns=['sim_min', 'sim_mean', 'sim_max'])
        del sim_results

        sim_df = sim_df.fillna(0.0).replace([np.inf, -np.inf], 0.0)

        feature_data['sim_min'] = sim_df['sim_min'].astype(np.float32)
        feature_data['sim_mean'] = sim_df['sim_mean'].astype(np.float32)
        feature_data['sim_max'] = sim_df['sim_max'].astype(np.float32)
        del sim_df

        feature_data['techs_count'] = df['n_tech'].astype(np.int8)

        features_df = pd.DataFrame(feature_data, index=df.index)
        del feature_data

        print("Preparing regression features...")
        feature_cols = ['techs_count', 'sim_min', 'sim_mean'] + \
                       [f'has_{t}' for t in top_tech] + \
                       [f'has_pair_{a}__{b}' for (a, b) in top_pairs]

        X = features_df[feature_cols].values
        y = df['descendants'].values

        # Validation
        print("Validating data...")
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        valid_mask = (y >= 0) & np.isfinite(y)
        if not valid_mask.all():
            print(f"Removing {(~valid_mask).sum()} rows with invalid y values")
            X = X[valid_mask]
            y = y[valid_mask]

        print(f"Final dataset: {len(X)} rows, {X.shape[1]} features")
        print(f"X stats: min={X.min():.4f}, max={X.max():.4f}")
        print(f"y stats: min={y.min():.2f}, max={y.max():.2f}, mean={y.mean():.2f}")

        print("Fitting Poisson regression (sklearn)...")
        model = PoissonRegressor(alpha=0.1, max_iter=300, verbose=1)
        model.fit(X, y)

        print("Computing IRR and confidence intervals...")
        coefs = model.coef_
        intercept = model.intercept_

        all_coefs = np.concatenate([[intercept], coefs])
        feature_names = ['const'] + feature_cols

        predictions = model.predict(X)
        variance = predictions  # For Poisson, variance = mean
        weights = 1.0 / (variance + 1e-10)

        X_with_const = np.column_stack([np.ones(len(X)), X])
        hessian_approx = X_with_const.T @ (weights[:, None] * X_with_const)

        try:
            cov_matrix = np.linalg.inv(hessian_approx)
            se = np.sqrt(np.diag(cov_matrix))
        except:
            print("Warning: Could not compute standard errors, using approximation")
            se = np.abs(all_coefs) * 0.1  # Rough approximation

        z_scores = all_coefs / (se + 1e-10)
        from scipy import stats
        p_values = 2 * (1 - stats.norm.cdf(np.abs(z_scores)))

        conf_low = all_coefs - 1.96 * se
        conf_high = all_coefs + 1.96 * se

        coef_df = pd.DataFrame({
            'feature': feature_names,
            'coef': all_coefs,
            'se': se,
            'pval': p_values,
            'conf_low': conf_low,
            'conf_high': conf_high,
        })
        coef_df['IRR'] = np.exp(coef_df['coef'])
        coef_df['IRR_low'] = np.exp(coef_df['conf_low'])
        coef_df['IRR_high'] = np.exp(coef_df['conf_high'])

        print(f"Saving results to {args.output}...")
        coef_df.to_csv(args.output, index=False, encoding='utf-8', float_format='%.8f')

        print("Done!")
        print(f"\nTop 10 features by IRR:")
        top_features = coef_df[coef_df['feature'] != 'const'].nlargest(10, 'IRR')
        print(top_features[['feature', 'IRR', 'pval']].to_string(index=False))

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())