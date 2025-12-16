#!/usr/bin/env bash
set -euo pipefail

if [ ! -t 1 ] && [ -t 2 ]; then
  exec 1>&2
fi


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
REL_MAP_OUT=${REL_MAP_OUT:-artifacts/plots/rel_map.png}
TITLES_TOKENS=${TITLES_TOKENS:-artifacts/embeddings/words/titles.tokens.jsonl.gz}
CONTEXT_TOKENS=${CONTEXT_TOKENS:-artifacts/embeddings/words/context.tokens.jsonl.gz}
TITLES_MODEL_OUT=${TITLES_MODEL:-artifacts/embeddings/words/titles}
CONTEXT_MODEL_OUT=${TITLES_MODEL:-artifacts/embeddings/words/context}
TITLES_MODEL=${TITLES_MODEL:-artifacts/embeddings/words/titles/titles.model}
CONTEXT_MODEL=${CONTEXT_MODEL:-artifacts/embeddings/words/context/context.model}

source "$VENV_DIR/bin/activate"

echo "1) Экспортируем комментарии технологий по отдельности (db.scripts.export_comments_for_techs)..."
python -m db.scripts.export_comments_for_techs -d "$DB_URL" -o "$COMMENTS_OUT" -m 1

echo "2) Лемматизируем комментарии..."
bash scripts/lemmatize.sh artifacts/tech_comments artifacts/tech

echo "3) Рисуем wordcloud для первого файла из папки tech (visualization.draw_wordcloud)..."
first_file=$(find artifacts/tech -maxdepth 1 -type f -print -quit)
if [ -z "$first_file" ]; then
  echo "Нет файлов в artifacts/tech"; exit 1
fi
python -m visualization.draw_wordcloud -i "$first_file" -o artifacts/plots/wc.png

echo "Pipeline finished successfully."