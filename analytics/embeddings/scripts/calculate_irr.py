import argparse
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from gensim.models import Word2Vec

from analytics.embeddings.patterns import COMPILED_PATTERNS
from utils.cli import cli_main
from utils.groups import categories as RAW_CATEGORIES
from utils.groups import normalize_categories
from utils.vectors import cosine

MAX_TECHS_PER_TITLE = 3
MIN_FREQ = 5
TOP_N = 50


def build_group_maps(w2v: Word2Vec, raw_categories: dict):
    """
    Возвращает:
      - group_to_tokens: dict[group -> list[str]] (только токены, присутствующие в модели)
      - token_to_groups: dict[token -> list[group]]
      - group_vecs: dict[group -> np.ndarray] средний вектор группы
    """
    kv = w2v.wv
    group_to_tokens = {
        g: present
        for g, toks in normalize_categories(raw_categories).items()
        if (present := [t for t in toks if t in kv.key_to_index])
    }
    group_vecs = {g: np.stack([kv.get_vector(t) for t in toks]).mean(axis=0)
                  for g, toks in group_to_tokens.items()}
    token_to_groups: dict[str, list[str]] = {}
    for g, toks in group_to_tokens.items():
        for t in toks:
            token_to_groups.setdefault(t, []).append(g)
    return group_to_tokens, token_to_groups, group_vecs


def extract_tech_regex(text: str) -> list[str]:
    """Технологии заголовка в порядке первого упоминания, не более MAX_TECHS_PER_TITLE."""
    if not isinstance(text, str) or not text:
        return []
    # Стабильная сортировка по позиции: при равных позициях сохраняется порядок PATTERNS
    hits = sorted(((m.start(), tech) for tech, pat in COMPILED_PATTERNS.items() if (m := pat.search(text))),
                  key=lambda hit: hit[0])
    return list(dict.fromkeys(tech for _, tech in hits))[:MAX_TECHS_PER_TITLE]


class PairSimilarity:
    """
    min/mean/max косинусной близости между технологиями заголовка.
    Технологий ~100, поэтому близость каждой пары считается один раз и кэшируется,
    а не пересчитывается для каждого из сотен тысяч заголовков.
    """

    def __init__(self, vec_map: dict[str, np.ndarray]):
        self.vec_map = {k: v for k, v in vec_map.items() if np.all(np.isfinite(v))}
        self._cache: dict[tuple[str, str], float] = {}

    def _sim(self, a: str, b: str) -> float:
        key = (a, b)
        if key not in self._cache:
            self._cache[key] = cosine(self.vec_map[a], self.vec_map[b])
        return self._cache[key]

    def stats(self, xs: list[str]) -> tuple[float, float, float]:
        present = [x for x in xs if x in self.vec_map]
        sims = [self._sim(a, b) for i, a in enumerate(present) for b in present[i + 1:]]
        sims = [s for s in sims if np.isfinite(s)]
        if not sims:
            return (0.0, 0.0, 0.0)
        return (float(min(sims)), float(np.mean(sims)), float(max(sims)))


def token_vec_map(w2v: Word2Vec, tokens) -> dict[str, np.ndarray]:
    kv = w2v.wv
    return {t: kv[t] for t in tokens if t in kv}


def indicator_features(tech_lists: pd.Series, top_tech: list[str],
                       top_pairs: list[tuple[str, str]]) -> dict[str, pd.Series]:
    """has_<tech> и has_pair_<a>__<b> одним проходом вместо apply на каждый признак."""
    # Пары могут включать технологии за пределами топа — им тоже нужны индикаторы
    needed = list(dict.fromkeys([*top_tech, *(t for pair in top_pairs for t in pair)]))
    exploded = tech_lists.explode().dropna()
    exploded = exploded[exploded.isin(needed)]
    dummies = pd.crosstab(exploded.index, exploded).clip(upper=1)
    dummies = dummies.reindex(index=tech_lists.index, columns=needed, fill_value=0).astype(np.int8)

    features = {f'has_{t}': dummies[t] for t in top_tech}
    for a, b in top_pairs:
        features[f'has_pair_{a}__{b}'] = (dummies[a] & dummies[b]).astype(np.int8)
    return features


def linearly_dependent_columns(X: pd.DataFrame) -> list[str]:
    """
    Жадно отбирает столбцы слева направо и возвращает те, что линейно выражаются
    через уже отобранные (как NA-коэффициенты в R). Работает по X'X (p x p), так что дёшево.
    """
    xtx = X.T.to_numpy() @ X.to_numpy()
    kept: list[int] = []
    dependent: list[str] = []
    for j, name in enumerate(X.columns):
        idx = [*kept, j]
        if np.linalg.matrix_rank(xtx[np.ix_(idx, idx)]) == len(idx):
            kept.append(j)
        else:
            dependent.append(name)
    return dependent


def fit_count_model(X: pd.DataFrame, y: np.ndarray, family: str):
    """
    GLM для числа комментариев. По умолчанию — отрицательная биномиальная (NB2):
    число комментариев сильно сверхдисперсно, и у Пуассона ошибки занижены.
    """
    X = sm.add_constant(X, has_constant="add")
    dependent = linearly_dependent_columns(X)
    if dependent:
        print(f"Warning: матрица признаков вырождена, исключены линейно зависимые признаки: "
              f"{', '.join(dependent)}")
        X = X.drop(columns=dependent)
    poisson = sm.GLM(y, X, family=sm.families.Poisson())
    if family == "poisson":
        # Робастные (sandwich) ошибки не требуют предположения var = mean
        return poisson.fit(cov_type="HC0"), None

    mu = poisson.fit().mu
    # Оценка alpha по Cameron & Trivedi: ((y - mu)^2 - y) / mu = alpha * mu + e (МНК без константы)
    alpha = max(float(np.sum((y - mu) ** 2 - y) / np.sum(mu ** 2)), 1e-8)
    return sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=alpha)).fit(), alpha


def load_titles(path: str, max_rows: int, sample: int | None) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=['title', 'descendants'])
    print(f"Загружено строк: {len(df)}")
    df = df[df['descendants'] >= 0]
    print(f"С известным числом комментариев: {len(df)}")
    if len(df) > max_rows:
        print(f"Случайная выборка {max_rows} строк из {len(df)} (--max-rows)")
        df = df.sample(n=max_rows, random_state=42)
    if sample:
        df = df.sample(n=min(sample, len(df)), random_state=42)
    # После фильтрации/выборки индекс идёт с пропусками; признаки ниже собираются как
    # по меткам (Series), так и по позиции (списки), поэтому индекс должен быть позиционным.
    return df.reset_index(drop=True)


def to_groups(tech_lists: pd.Series, w2v: Word2Vec):
    """Заменяет технологии их группами из utils.groups; возвращает (списки групп, векторы групп)."""
    _, token_to_groups, group_vecs = build_group_maps(w2v, RAW_CATEGORIES)

    def map_tokens(xs: list[str]) -> list[str]:
        groups = (g for t in xs for g in token_to_groups.get(t, []) if g in group_vecs)
        return list(dict.fromkeys(groups))

    return tech_lists.apply(map_tokens), group_vecs


def top_labels(tech_lists: pd.Series) -> tuple[pd.Series, list[str], list[tuple[str, str]]]:
    labels = [t for xs in tech_lists for t in xs]
    if not labels:
        raise ValueError("Не удалось извлечь ни одной технологии/группы из заголовков.")
    freq = pd.Series(labels).value_counts()  # равные частоты — в порядке первого появления
    top_tech = freq[freq >= MIN_FREQ].index.tolist()[:TOP_N]
    pair_freq = Counter(pair for xs in tech_lists for pair in combinations(sorted(xs), 2))
    top_pairs = [p for p, c in pd.Series(dict(pair_freq), dtype=int).sort_values(ascending=False).items()
                 if c >= MIN_FREQ][:TOP_N]
    return freq, top_tech, top_pairs


def build_features(tech_lists: pd.Series, top_tech, top_pairs, vec_map) -> pd.DataFrame:
    features = indicator_features(tech_lists, top_tech, top_pairs)

    pair_sim = PairSimilarity(vec_map)
    sims = pd.DataFrame([pair_sim.stats(xs) for xs in tech_lists], columns=['sim_min', 'sim_mean', 'sim_max'])
    sims = sims.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    features['sim_min'] = sims['sim_min'].astype(np.float32)
    features['sim_mean'] = sims['sim_mean'].astype(np.float32)

    # Общее число технологий = сумма has_* + технологии вне топа. С has_* в модели
    # полный techs_count был бы (почти) линейно зависим от них и делал бы
    # матрицу вырожденной, поэтому контролируем только технологии вне топа.
    top_set = set(top_tech)
    features['other_techs_count'] = tech_lists.apply(lambda xs: sum(t not in top_set for t in xs)).astype(np.int8)

    columns = ['other_techs_count', 'sim_min', 'sim_mean',
               *(f'has_{t}' for t in top_tech), *(f'has_pair_{a}__{b}' for a, b in top_pairs)]
    X = pd.DataFrame(features)[columns].astype(np.float64)
    return X.replace([np.inf, -np.inf], 0.0).fillna(0.0)


def irr_table(result) -> pd.DataFrame:
    ci = result.conf_int(alpha=0.05)
    coef_df = pd.DataFrame({
        'feature': result.params.index,
        'coef': result.params.values,
        'se': result.bse.values,
        'pval': result.pvalues.values,
        'conf_low': ci[0].values,
        'conf_high': ci[1].values,
    })
    coef_df['IRR'] = np.exp(coef_df['coef'])
    coef_df['IRR_low'] = np.exp(coef_df['conf_low'])
    coef_df['IRR_high'] = np.exp(coef_df['conf_high'])
    return coef_df


def parse_args():
    p = argparse.ArgumentParser(
        prog="calculate_irr",
        description="IRR технологий: во сколько раз упоминание технологии меняет ожидаемое число комментариев"
    )
    p.add_argument("-m", "--model", required=True, help="Путь к модели Word2Vec (.model)")
    p.add_argument("-i", "--input", required=True, help="CSV с метаданными статей (export_stories_meta)")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному CSV с коэффициентами")
    p.add_argument("--sample", type=int, default=None, help="Случайная выборка N строк (для отладки)")
    p.add_argument("--max-rows", type=int, default=500000, help="Максимум строк (по умолчанию 500000)")
    p.add_argument("--family", choices=["negbin", "poisson"], default="negbin",
                   help="Семейство GLM: negbin (по умолчанию) или poisson с робастными ошибками")
    p.add_argument("--groups", action="store_true",
                   help="Агрегировать технологии в группы из utils.groups.categories")
    return p.parse_args()


def compute_irr(df: pd.DataFrame, w2v: Word2Vec, family: str = "negbin", groups: bool = False) -> pd.DataFrame:
    """
    Таблица IRR по DataFrame с колонками title и descendants (индекс — позиционный).
    Базовая категория — статьи без технологий из топа, поэтому на вход нужны все статьи,
    а не только статьи с технологиями.
    """
    print("Извлечение технологий из заголовков...")
    tech_lists = df['title'].apply(extract_tech_regex)
    if groups:
        tech_lists, vec_map = to_groups(tech_lists, w2v)

    freq, top_tech, top_pairs = top_labels(tech_lists)
    print(f"В модели: {len(top_tech)} {'групп' if groups else 'технологий'}, {len(top_pairs)} пар")
    if not groups:
        vec_map = token_vec_map(w2v, freq.index)

    X = build_features(tech_lists, top_tech, top_pairs, vec_map)
    y = df['descendants'].to_numpy(dtype=np.float64)

    # Постоянный признак (например, sim_* когда нет заголовков с 2+ технологиями)
    # неотличим от константы и даёт бессмысленные ошибки
    constant_cols = [c for c in X.columns if X[c].nunique() <= 1]
    if constant_cols:
        print(f"Исключены постоянные признаки: {', '.join(constant_cols)}")
        X = X.drop(columns=constant_cols)

    print(f"Строк: {len(X)}, признаков: {X.shape[1]}; "
          f"комментарии: среднее={y.mean():.2f}, дисперсия={y.var():.2f}")
    result, alpha = fit_count_model(X, y, family)
    if alpha is not None:
        print(f"Оценка сверхдисперсии NB: alpha={alpha:.4f}")
    return irr_table(result)


@cli_main
def main() -> int:
    args = parse_args()
    df = load_titles(args.input, args.max_rows, args.sample)
    coef_df = compute_irr(df, Word2Vec.load(args.model), args.family, args.groups)
    coef_df.to_csv(args.output, index=False, encoding='utf-8', float_format='%.8f')
    print(f"Готово: коэффициенты сохранены в {args.output}")
    print("\nТоп-10 признаков по IRR:")
    top_features = coef_df[coef_df['feature'] != 'const'].nlargest(10, 'IRR')
    print(top_features[['feature', 'IRR', 'pval']].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
