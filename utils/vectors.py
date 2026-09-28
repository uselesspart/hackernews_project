import numpy as np


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Косинусная близость; 0.0 для нулевого вектора, результат обрезан до [-1, 1]."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.clip(np.dot(a, b) / (norm_a * norm_b), -1.0, 1.0))
