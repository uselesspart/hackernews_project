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
CTX_LEM=${CTX_LEM:-artifacts/sentences/context_lem.txt}
TECH_OUT=${TECH_OUT:-artifacts/tech_names.txt}
MODEL_PATH=${MODEL_PATH:-artifacts/embeddings/words/w2v_titles_300d.model}
MATRIX_OUT=${MATRIX_OUT:-artifacts/similarity_matrix.csv}
REL_MAP_OUT=${REL_MAP_OUT:-artifacts/plots/rel_map.png}
COMMENTS_OUT=${COMMENTS_OUT:-artifacts/tech_comments/}

echo "1) Экспортируем комментарии технологий по отдельности (db.scripts.export_comments_for_techs)..."
python -m db.scripts.export_comments_for_techs -d "$DB_URL" -o "$COMMENTS_OUT" -m 10

echo "2) Лемматизируем комментарии..."
./lemmatize_dir.sh artifacts/tech_comments artifacts/tech

echo "3) Рисуем wordcloud для java (visualization.draw_wordcloud)..."
python -m visualization.draw_wordcloud -i artifacts/tech/java_lem.txt -o artifacts/plots/wc.png

echo "Pipeline finished successfully."