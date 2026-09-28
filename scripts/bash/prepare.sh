#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

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
            sudo pacman -S --noconfirm python git
	    git clone https://aur.archlinux.org/python312.git
	    cd python312
	    makepkg -si
	    cd ..
	    rm -rf python312
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
activate_venv

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

echo "8) Классификация технологий(analytics.embeddings.scripts.classify_tech)..."
python -m analytics.embeddings.scripts.classify_tech -d "$DB_URL"

# Истории без технологий остаются в БД: они нужны как база сравнения для IRR.
# Для обучения моделей выгружаются только истории с технологиями.
echo "9) Экспорт контекста и заголовков (db.scripts.export_context & db.scripts.export_titles)..."
python -m db.scripts.export_context -d "$DB_URL" -o "$CTX_OUT" --format txt --with-techs-only
python -m db.scripts.export_titles -d "$DB_URL" -o "$TITLES_OUT" --format txt --with-techs-only

echo "10) Лемматизация (analytics.embeddings.scripts.lemmatize_file)..."
python -m analytics.embeddings.scripts.lemmatize_file -i "$CTX_OUT" -o "$CTX_LEM"
python -m analytics.embeddings.scripts.lemmatize_file -i "$TITLES_OUT" -o "$TITLES_LEM"

echo "11) Преобразование в токены (analytics.embeddings.scripts.sentences_to_vectors)..."
python -m analytics.embeddings.scripts.sentences_to_vectors -i "$CTX_LEM" -o "$CONTEXT_TOKENS"
python -m analytics.embeddings.scripts.sentences_to_vectors -i "$TITLES_LEM" -o "$TITLES_TOKENS"

echo "12) Обучение модели (analytics.embeddings.scripts.train_model)..."
python -m analytics.embeddings.scripts.train_model -p "$CONTEXT_TOKENS" -o "$CONTEXT_MODEL_OUT"
python -m analytics.embeddings.scripts.train_model -p "$TITLES_TOKENS" -o "$TITLES_MODEL_OUT" 

echo "13) Экспорт технологий (db.scripts.export_tech_names) ..."
python -m db.scripts.export_tech_names -d "$DB_URL" -o "$TECH_OUT" --format txt

echo "14) Экспортируем комментарии технологий по отдельности (db.scripts.export_comments_for_techs)..."
python -m db.scripts.export_comments_for_techs -d "$DB_URL" -o "$COMMENTS_OUT" -m 1

echo "15) Лемматизируем комментарии..."
bash scripts/lemmatize.sh "$COMMENTS_OUT" "$COMMENTS_LEM"

echo "Pipeline finished successfully."
