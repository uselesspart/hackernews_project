"""
Проверка модели Word2Vec на технологиях: осмысленны ли соседи.

Две проверки:
- вырожденность: на малом корпусе все векторы технологий почти сонаправлены (близость около 0.999),
  и порядок соседей — шум;
- проверочные пары: технологии, которые должны быть рядом (Rust — C++, PostgreSQL — MySQL).
  Считается, попадает ли вторая в топ-k соседей первой среди всех технологий словаря.
"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from utils.groups import normalize_token

# Пары из одной ниши: язык — язык, СУБД — СУБД, модель — модель, ОС — ОС
CHECK_PAIRS: list[tuple[str, str]] = [
    ("rust", "cpp"), ("rust", "go"), ("c", "cpp"), ("python", "r"), ("python", "julia"),
    ("java", "kotlin"), ("java", "scala"), ("javascript", "typescript"), ("swift", "kotlin"),
    ("haskell", "elixir"), ("elixir", "erlang"), ("ruby", "php"),
    ("postgresql", "mysql"), ("postgresql", "sqlite"),
    ("gpt", "claude"), ("gpt", "gemini"), ("claude", "llama"),
    ("linux", "windows"), ("windows", "macos"), ("ios", "android"),
]
# Средняя близость между технологиями выше этого порога — модель не различает слова
DEGENERATE_MEAN_SIMILARITY = 0.9


def tech_similarity(kv, keys: list[str]) -> tuple[list[str], np.ndarray]:
    """Технологии из словаря модели и матрица их косинусной близости."""
    present = [k for k in keys if normalize_token(k) in kv.key_to_index]
    if not present:
        return [], np.zeros((0, 0))
    return present, cosine_similarity(np.stack([kv.get_vector(normalize_token(k)) for k in present]))


def quality_report(kv, keys: list[str], pairs=CHECK_PAIRS, k: int = 10) -> dict:
    present, sim = tech_similarity(kv, keys)
    n = len(present)
    mean_sim = float(sim[~np.eye(n, dtype=bool)].mean()) if n >= 2 else float("nan")
    index = {key: i for i, key in enumerate(present)}

    checked = []
    for a, b in pairs:
        if a not in index or b not in index:
            continue
        i, j = index[a], index[b]
        # Ранг b среди соседей a (1 — ближайший), без самой a
        rank = int((sim[i] > sim[i, j]).sum()) - int(sim[i, i] > sim[i, j])
        checked.append({"a": a, "b": b, "similarity": float(sim[i, j]), "rank": rank + 1})

    hits = [p["rank"] <= k for p in checked]
    return {
        "techs": n,
        "mean_similarity": mean_sim,
        "degenerate": n >= 2 and mean_sim > DEGENERATE_MEAN_SIMILARITY,
        "pairs": checked,
        "k": k,
        "hit_rate": float(np.mean(hits)) if hits else None,
        "mrr": float(np.mean([1 / p["rank"] for p in checked])) if checked else None,
    }


def format_report(report: dict) -> str:
    lines = [f"Технологий в словаре: {report['techs']}, средняя близость между ними: "
             f"{report['mean_similarity']:.3f}" + (" — модель вырождена" if report["degenerate"] else "")]
    if report["pairs"]:
        lines.append(f"Проверочные пары: в топ-{report['k']} соседей {report['hit_rate']:.0%}, MRR {report['mrr']:.3f}")
        lines.extend(f"  {p['a']:>12} — {p['b']:<12} близость {p['similarity']:.3f}, место {p['rank']}"
                     for p in report["pairs"])
    else:
        lines.append("Проверочные пары: ни одной пары нет в словаре модели")
    return "\n".join(lines)
