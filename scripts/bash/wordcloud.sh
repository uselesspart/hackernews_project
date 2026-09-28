#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

activate_venv

echo "1) Рисуем wordcloud для первого файла из папки tech (visualization.draw_wordcloud)..."
first_file=$(find "$COMMENTS_LEM" -maxdepth 1 -type f -print -quit)
if [ -z "$first_file" ]; then
  echo "Нет файлов в $COMMENTS_LEM"; exit 1
fi
python -m visualization.draw_wordcloud -i "$first_file" -o "$PLOTS_DIR/wc.png"

echo "Pipeline finished successfully."
