#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

activate_venv

echo "1) Экспортируем метаданные статей (db.scripts.export_stories_meta)..."
python -m db.scripts.export_stories_meta -d "$DB_URL" -o "$META_OUT"

echo "2) Рассчитавыем IRR (analytics.embeddings.scripts.calculate_irr)..."
python -m analytics.embeddings.scripts.calculate_irr -i "$META_OUT" -m "$TITLES_MODEL" -o "$COEFS_OUT"

echo "3) Рисуем график (visualization.draw_irr_plot)..."
python -m visualization.draw_irr_plot -i "$COEFS_OUT" -o "$PLOTS_DIR/irr.png"
