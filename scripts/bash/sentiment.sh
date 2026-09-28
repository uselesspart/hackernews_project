#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

activate_venv

echo "1) Проводим сентимент-анализ (analytics.embeddings.scripts.calculate_sentiment)..."
python -m analytics.embeddings.scripts.calculate_sentiment -d "$COMMENTS_LEM" --titles-kv "$TITLES_MODEL" --comments-kv "$CONTEXT_MODEL" --out-csv "$CORPUS_OUT" --mode vader

echo "2) Рисуем график (visualization.draw_sentiment_plot)..."
python -m visualization.draw_sentiment_plot -i "$CORPUS_OUT" -o "$PLOTS_DIR/sentiment.png"

echo "Pipeline finished successfully."
