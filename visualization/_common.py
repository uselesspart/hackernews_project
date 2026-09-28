"""Общие настройки и сохранение графиков для скриптов visualization.*"""
from pathlib import Path

import matplotlib

# Неинтерактивный backend до первого импорта pyplot: скрипты работают и без дисплея (сервер, CI)
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


def save_figure(fig, path: str | Path, dpi: int = 300) -> Path:
    """Сохраняет фигуру (создавая каталог) и закрывает её, чтобы не копить память."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"График сохранён: {out}")
    return out
