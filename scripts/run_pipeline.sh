set -euo pipefail

PYTHON_BIN=${PYTHON_BIN:-python3.11}
VENV_DIR=${VENV_DIR:-venv}
DB_URL=${DB_URL:-"sqlite:///hn.db"}
START_ID=${START_ID:-38000000}
END_ID=${END_ID:-38010000}
WORKERS=${WORKERS:-8}
RAW_OUT=${RAW_OUT:-raw_data/hn_data.jsonl.gz}
BATCH_SIZE=${BATCH_SIZE:-1000}
CTX_OUT=${CTX_OUT:-artifacts/sentences/context.txt}
CTX_LEM=${CTX_LEM:-artifacts/sentences/context_lem.txt}

echo "1) Проверка python..."
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found. Install Python or set PYTHON_BIN to point to interpreter."
  exit 1
fi

echo "2) Создаём виртуальное окружение..."
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "3) Обновляем pip и устанавливаем зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

echo "4) Устанавливаем модель spaCy (если требуется)..."
python -m spacy download en_core_web_sm || echo "spaCy model install failed (continue if not needed)"

echo "5) Создаём директории..."
mkdir -p raw_data artifacts/sentences artifacts/embeddings

echo "6) Скачиваем данные (scripts.retrieve)..."
python -m scripts.retrieve -o "$RAW_OUT" -s "$START_ID" -e "$END_ID" -w "$WORKERS" --progress-every 10000

echo "7) Импорт в БД (db.scripts.ingest)..."
python -m db.scripts.ingest -d "$DB_URL" -i "$RAW_OUT" -b "$BATCH_SIZE"

echo "8) Экспорт контекста (db.scripts.export_context)..."
python -m db.scripts.export_context -d "$DB_URL" -o "$CTX_OUT" --format txt

echo "9) Лемматизация (analytics.embeddings.scripts.lemmatize_file)..."
python -m analytics.embeddings.scripts.lemmatize_file -i "$CTX_OUT" -o "$CTX_LEM"

echo "10) Преобразование в токены (analytics.embeddings.scripts.sentences_to_vectors)..."
python -m analytics.embeddings.scripts.sentences_to_vectors -i "$CTX_LEM"

echo "Pipeline finished successfully."