#!/usr/bin/env bash
set -euo pipefail

if [ ! -t 1 ] && [ -t 2 ]; then
  exec 1>&2
fi

# Всегда работаем из корня
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/../../bin" >/dev/null 2>&1 && pwd)"
if [ ! -d "$ROOT_DIR/scripts" ]; then
  echo "Не удалось найти корень проекта: ожидается папка 'scripts' в $ROOT_DIR"; exit 1
fi
cd "$ROOT_DIR"


PYTHON_BIN=${PYTHON_BIN:-python3.12}
VENV_DIR=${VENV_DIR:-venv}
DB_URL=${DB_URL:-"sqlite:///test_sc.db"}
START_ID=${START_ID:-38000000}
END_ID=${END_ID:-38010000}
WORKERS=${WORKERS:-32}
RAW_OUT=${RAW_OUT:-raw_data/hn_data_2.jsonl.gz}
BATCH_SIZE=${BATCH_SIZE:-1000}
CTX_OUT=${CTX_OUT:-artifacts/sentences/context.txt}
TITLES_OUT=${CTX_OUT:-artifacts/sentences/titles.txt}
CTX_LEM=${CTX_LEM:-artifacts/sentences/context_lem.txt}
TITLES_LEM=${CTX_LEM:-artifacts/sentences/titles_lem.txt}
TECH_OUT=${TECH_OUT:-artifacts/tech_names.txt}
MATRIX_OUT=${MATRIX_OUT:-artifacts/similarity_matrix.csv}
REL_MAP_OUT=${REL_MAP_OUT:-../plots/rel_map.png}
TITLES_TOKENS=${TITLES_TOKENS:-artifacts/embeddings/words/titles.tokens.jsonl.gz}
CONTEXT_TOKENS=${CONTEXT_TOKENS:-artifacts/embeddings/words/context.tokens.jsonl.gz}
TITLES_MODEL_OUT=${TITLES_MODEL:-artifacts/embeddings/words/titles}
CONTEXT_MODEL_OUT=${TITLES_MODEL:-artifacts/embeddings/words/context}
TITLES_MODEL=${TITLES_MODEL:-artifacts/embeddings/words/titles/w2v_titles_300d.model}
CONTEXT_MODEL=${CONTEXT_MODEL:-artifacts/embeddings/words/context/w2v_context_300d.model}
COMMENTS_OUT=${COMMENTS_OUT:-artifacts/tech_comments/}
COMMENTS_LEM=${COMMENTS_LEM:-artifacts/tech}

source "$VENV_DIR/bin/activate"

echo "1) Построение матрицы отношений (analytics.embeddings.scripts.build_rel_matrix)..."
python -m analytics.embeddings.scripts.build_rel_matrix -i "$TECH_OUT" -m "$CONTEXT_MODEL" -o "$MATRIX_OUT"

echo "2) Визуализации карты близости (visualization.draw_relationship_map)..."
python -m visualization.draw_relationship_map -m "$MATRIX_OUT" -t "$TECH_OUT" -o "$REL_MAP_OUT"

echo "Pipeline finished successfully."