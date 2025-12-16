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

# Функция для определения ОС и пакетного менеджера
detect_os() {
    if command -v apt >/dev/null 2>&1; then
        echo "debian"
    elif command -v yum >/dev/null 2>&1; then
        echo "rhel"
    elif command -v dnf >/dev/null 2>&1; then
        echo "fedora"
    elif command -v pacman >/dev/null 2>&1; then
        echo "arch"
    elif command -v brew >/dev/null 2>&1; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Функция установки Python
install_python() {
    local os_type
    os_type=$(detect_os)
    
    echo "Устанавливаем Python для $os_type..."
    
    case "$os_type" in
        "debian")
            sudo apt update
            sudo apt install -y python3.12 python3.12-venv python3.12-pip
            ;;
        "rhel")
            sudo yum install -y python3.12 python3.12-venv python3.12-pip
            ;;
        "fedora")
            sudo dnf install -y python3.12 python3.12-venv python3.12-pip
            ;;
        "arch")
            sudo pacman -Sy --noconfirm python
            ;;
    esac
}

echo "1) Проверка python..."
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python $PYTHON_BIN не найден. Устанавливаем..."
    install_python
    
    # Проверяем снова после установки
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        # Пробуем альтернативные варианты
        for alt_python in python3.12 python3 python; do
            if command -v "$alt_python" >/dev/null 2>&1; then
                echo "Используем $alt_python вместо $PYTHON_BIN"
                PYTHON_BIN="$alt_python"
                break
            fi
        done
        
        # Финальная проверка
        if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
            echo "Ошибка: Python всё ещё не найден после установки."
            echo "Попробуйте установить вручную или установите переменную PYTHON_BIN."
            exit 1
        fi
    fi
fi

echo "Используем Python: $(command -v "$PYTHON_BIN")"
echo "Версия Python: $("$PYTHON_BIN" --version)"

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

echo "11) Обучение модели (analytics.embeddings.scripts.train_model)..."
python -m analytics.embeddings.scripts.train_model -p artifacts/embeddings/words/titles.tokens5.jsonl.gz

echo "12) Экспорт технологий (db.scripts.export_tech_names) ..."
python -m db.scripts.export_tech_names -d "$DB_URL" -o "$TECH_OUT" --format txt

echo "13) Построение матрицы отношений (analytics.embeddings.scripts.build_rel_matrix)..."
python -m analytics.embeddings.scripts.build_rel_matrix -i "$TECH_OUT" -m "$MODEL_PATH" -o "$MATRIX_OUT"

echo "14) Визуализации карты близости (visualization.draw_relationship_map)..."
python -m visualization.draw_relationship_map -m "$MATRIX_OUT" -t "$TECH_OUT" -o "$REL_MAP_OUT"

echo "15) Экспортируем комментарии технологий по отдельности"

echo "Pipeline finished successfully."