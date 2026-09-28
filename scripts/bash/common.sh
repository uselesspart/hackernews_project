# Общие настройки для scripts/bash/*.sh. Подключается через source, а не запускается.
# Любую переменную можно переопределить в окружении перед запуском, например:
#   DB_URL=sqlite:///D:/hackernews_data/hn.db bash scripts/bash/irr.sh

# Прогресс печатаем в stderr, если stdout перенаправлен, а stderr — терминал
if [ ! -t 1 ] && [ -t 2 ]; then
  exec 1>&2
fi

# Всегда работаем из корня проекта: в релизной раскладке код лежит в bin/, в репозитории — в корне
COMMON_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
if [ -d "$COMMON_DIR/../../bin/scripts" ]; then
  ROOT_DIR="$(cd -- "$COMMON_DIR/../../bin" >/dev/null 2>&1 && pwd)"
else
  ROOT_DIR="$(cd -- "$COMMON_DIR/../.." >/dev/null 2>&1 && pwd)"
fi
if [ ! -d "$ROOT_DIR/scripts" ]; then
  echo "Не удалось найти корень проекта: ожидается папка 'scripts' в $ROOT_DIR"; exit 1
fi
cd "$ROOT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python3.12}
VENV_DIR=${VENV_DIR:-venv}
DB_URL=${DB_URL:-"sqlite:///test_sc.db"}

# Загрузка и импорт
START_ID=${START_ID:-38000000}
END_ID=${END_ID:-38010000}
WORKERS=${WORKERS:-32}
RAW_OUT=${RAW_OUT:-raw_data/hn_data_2.jsonl.gz}
BATCH_SIZE=${BATCH_SIZE:-1000}

# Тексты и токены
CTX_OUT=${CTX_OUT:-artifacts/sentences/context.txt}
TITLES_OUT=${TITLES_OUT:-artifacts/sentences/titles.txt}
CTX_LEM=${CTX_LEM:-artifacts/sentences/context_lem.txt}
TITLES_LEM=${TITLES_LEM:-artifacts/sentences/titles_lem.txt}
TITLES_TOKENS=${TITLES_TOKENS:-artifacts/embeddings/words/titles.tokens.jsonl.gz}
CONTEXT_TOKENS=${CONTEXT_TOKENS:-artifacts/embeddings/words/context.tokens.jsonl.gz}

# Модели
TITLES_MODEL_OUT=${TITLES_MODEL_OUT:-artifacts/embeddings/words/titles}
CONTEXT_MODEL_OUT=${CONTEXT_MODEL_OUT:-artifacts/embeddings/words/context}
TITLES_MODEL=${TITLES_MODEL:-artifacts/embeddings/words/titles/w2v_titles_300d.model}
CONTEXT_MODEL=${CONTEXT_MODEL:-artifacts/embeddings/words/context/w2v_context_300d.model}

# Результаты анализа
TECH_OUT=${TECH_OUT:-artifacts/tech_names.txt}
MATRIX_OUT=${MATRIX_OUT:-artifacts/similarity_matrix.csv}
COMMENTS_OUT=${COMMENTS_OUT:-artifacts/tech_comments/}
COMMENTS_LEM=${COMMENTS_LEM:-artifacts/tech}
META_OUT=${META_OUT:-artifacts/meta.csv}
COEFS_OUT=${COEFS_OUT:-artifacts/coefs.csv}
CORPUS_OUT=${CORPUS_OUT:-artifacts/corpus3.csv}
PLOTS_DIR=${PLOTS_DIR:-../plots}

activate_venv() {
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}
