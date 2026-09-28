#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

activate_venv

echo "1) Построение матрицы отношений (analytics.embeddings.scripts.build_rel_matrix)..."
python -m analytics.embeddings.scripts.build_rel_matrix -i "$TECH_OUT" -m "$CONTEXT_MODEL" -o "$MATRIX_OUT"

echo "2) Визуализации карты близости (visualization.draw_relationship_map)..."
python -m visualization.draw_relationship_map -m "$MATRIX_OUT" -t "$TECH_OUT" -o "$PLOTS_DIR/rel_map.png"

echo "Pipeline finished successfully."
