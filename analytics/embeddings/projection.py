"""2D-проекция технологий (t-SNE) для карты отношений: общая для графика и предрасчёта API."""
import numpy as np
import pandas as pd
from sklearn.manifold import TSNE


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
