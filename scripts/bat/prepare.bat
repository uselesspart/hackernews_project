@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Всегда работаем из корня
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\bin") do set "ROOT_DIR=%%~fI"
if not exist "%ROOT_DIR%\scripts" (
  echo Не удалось найти корень проекта: ожидается папка "scripts" в "%ROOT_DIR%"
  exit /b 1
)
pushd "%ROOT_DIR%"

REM Переменные с дефолтами
if not defined PYTHON_BIN set "PYTHON_BIN=python3.12"
if not defined VENV_DIR set "VENV_DIR=venv"
if not defined DB_URL set "DB_URL=sqlite:///test_sc.db"
if not defined START_ID set "START_ID=38000000"
if not defined END_ID set "END_ID=38010000"
if not defined WORKERS set "WORKERS=32"
if not defined RAW_OUT set "RAW_OUT=raw_data\hn_data_2.jsonl.gz"
if not defined BATCH_SIZE set "BATCH_SIZE=1000"
if not defined CTX_OUT set "CTX_OUT=artifacts\sentences\context.txt"
REM В оригинале TITLES_OUT по умолчанию = CTX_OUT
if not defined TITLES_OUT set "TITLES_OUT=%CTX_OUT%"
if not defined CTX_LEM set "CTX_LEM=artifacts\sentences\context_lem.txt"
REM В оригинале TITLES_LEM по умолчанию = CTX_LEM
if not defined TITLES_LEM set "TITLES_LEM=%CTX_LEM%"
if not defined TECH_OUT set "TECH_OUT=artifacts\tech_names.txt"
if not defined TITLES_TOKENS set "TITLES_TOKENS=artifacts\embeddings\words\titles.tokens.jsonl.gz"
if not defined CONTEXT_TOKENS set "CONTEXT_TOKENS=artifacts\embeddings\words\context.tokens.jsonl.gz"
REM В оригинале OUT директории зависят от TITLES_MODEL, но по умолчанию берут каталоги:
if not defined TITLES_MODEL_OUT set "TITLES_MODEL_OUT=artifacts\embeddings\words\titles"
if not defined CONTEXT_MODEL_OUT set "CONTEXT_MODEL_OUT=artifacts\embeddings\words\context"
if not defined TITLES_MODEL set "TITLES_MODEL=artifacts\embeddings\words\titles\w2v_titles_300d.model"
if not defined CONTEXT_MODEL set "CONTEXT_MODEL=artifacts\embeddings\words\context\w2v_context_300d.model"
if not defined COMMENTS_OUT set "COMMENTS_OUT=artifacts\tech_comments"
if not defined COMMENTS_LEM set "COMMENTS_LEM=artifacts\tech"

echo 1^) Проверка Python...
set "PYTHON_CMD="
call :tryPython "%PYTHON_BIN%" && set "PYTHON_CMD=%PYTHON_BIN%"
if not defined PYTHON_CMD call :tryPython python3.12 && set "PYTHON_CMD=python3.12"
if not defined PYTHON_CMD call :tryPython python3 && set "PYTHON_CMD=python3"
if not defined PYTHON_CMD call :tryPython python && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  for %%V in (3.12 3.11 3.10 3) do (
    py -%%V --version >nul 2>&1 && set "PYTHON_CMD=py -%%V" && goto gotPy
  )
  echo Ошибка: Python не найден. Установите Python (например, через winget: ^"winget install --id Python.Python.3.12 -e^") или Chocolatey (^"choco install python --version=3.12^").
  popd
  exit /b 1
)
:gotPy
echo Используем Python: %PYTHON_CMD%
%PYTHON_CMD% --version

echo 2^) Создаём виртуальное окружение...
%PYTHON_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 (echo Ошибка создания venv & popd & exit /b 1)

set "VENV_ACT=%VENV_DIR%\Scripts\activate.bat"
if not exist "%VENV_ACT%" (
  echo Виртуальное окружение не найдено: "%VENV_ACT%"
  popd
  exit /b 1
)
call "%VENV_ACT%"

echo 3^) Обновляем pip и устанавливаем зависимости...
python -m pip install --upgrade pip
if errorlevel 1 (echo Ошибка обновления pip & popd & exit /b 1)
python -m pip install -r requirements.txt
if errorlevel 1 (echo Ошибка установки зависимостей & popd & exit /b 1)

echo 4^) Устанавливаем модель spaCy (если требуется)...
python -m spacy download en_core_web_sm
if errorlevel 1 echo spaCy model install failed ^(continue if not needed^)

echo 5^) Создаём директории...
if not exist "raw_data" mkdir "raw_data"
if not exist "artifacts" mkdir "artifacts"
if not exist "artifacts\sentences" mkdir "artifacts\sentences"
if not exist "artifacts\embeddings" mkdir "artifacts\embeddings"
if not exist "artifacts\embeddings\words" mkdir "artifacts\embeddings\words"
if not exist "%COMMENTS_OUT%" mkdir "%COMMENTS_OUT%"
if not exist "%COMMENTS_LEM%" mkdir "%COMMENTS_LEM%"

echo 6^) Скачиваем данные (scripts.retrieve)...
python -m scripts.retrieve -o "%RAW_OUT%" -s "%START_ID%" -e "%END_ID%" -w "%WORKERS%" --progress-every 10000
if errorlevel 1 (echo Ошибка скачивания данных & popd & exit /b 1)

echo 7^) Импорт в БД (db.scripts.ingest)...
python -m db.scripts.ingest -d "%DB_URL%" -i "%RAW_OUT%" -b "%BATCH_SIZE%"
if errorlevel 1 (echo Ошибка импорта в БД & popd & exit /b 1)

echo 7.5^) Классификация технологий (analytics.embeddings.scripts.classify_tech)...
python -m analytics.embeddings.scripts.classify_tech -d "%DB_URL%"
if errorlevel 1 (echo Ошибка классификации технологий & popd & exit /b 1)

echo 8^) Экспорт контекста и заголовков (db.scripts.export_context & db.scripts.export_titles)...
python -m db.scripts.export_context -d "%DB_URL%" -o "%CTX_OUT%" --format txt
if errorlevel 1 (echo Ошибка экспорта контекста & popd & exit /b 1)
python -m db.scripts.export_titles -d "%DB_URL%" -o "%TITLES_OUT%" --format txt
if errorlevel 1 (echo Ошибка экспорта заголовков & popd & exit /b 1)

echo 9^) Лемматизация (analytics.embeddings.scripts.lemmatize_file)...
python -m analytics.embeddings.scripts.lemmatize_file -i "%CTX_OUT%" -o "%CTX_LEM%"
if errorlevel 1 (echo Ошибка лемматизации контекста & popd & exit /b 1)
python -m analytics.embeddings.scripts.lemmatize_file -i "%TITLES_OUT%" -o "%TITLES_LEM%"
if errorlevel 1 (echo Ошибка лемматизации заголовков & popd & exit /b 1)

echo 10^) Преобразование в токены (analytics.embeddings.scripts.sentences_to_vectors)...
python -m analytics.embeddings.scripts.sentences_to_vectors -i "%CTX_LEM%" -o "%CONTEXT_TOKENS%"
if errorlevel 1 (echo Ошибка токенизации контекста & popd & exit /b 1)
python -m analytics.embeddings.scripts.sentences_to_vectors -i "%TITLES_LEM%" -o "%TITLES_TOKENS%"
if errorlevel 1 (echo Ошибка токенизации заголовков & popd & exit /b 1)

echo 11^) Обучение модели (analytics.embeddings.scripts.train_model)...
python -m analytics.embeddings.scripts.train_model -p "%CONTEXT_TOKENS%" -o "%CONTEXT_MODEL_OUT%"
if errorlevel 1 (echo Ошибка обучения модели контекста & popd & exit /b 1)
python -m analytics.embeddings.scripts.train_model -p "%TITLES_TOKENS%" -o "%TITLES_MODEL_OUT%"
if errorlevel 1 (echo Ошибка обучения модели заголовков & popd & exit /b 1)

echo 12^) Экспорт технологий (db.scripts.export_tech_names)...
python -m db.scripts.export_tech_names -d "%DB_URL%" -o "%TECH_OUT%" --format txt
if errorlevel 1 (echo Ошибка экспорта технологий & popd & exit /b 1)

echo 13^) Экспортируем комментарии технологий по отдельности (db.scripts.export_comments_for_techs)...
python -m db.scripts.export_comments_for_techs -d "%DB_URL%" -o "%COMMENTS_OUT%" -m 1
if errorlevel 1 (echo Ошибка экспорта комментариев технологий & popd & exit /b 1)

echo 14^) Лемматизируем комментарии...
REM Эквивалент bash-скрипта: лемматизируем все файлы в %COMMENTS_OUT% в %COMMENTS_LEM%
if not exist "%COMMENTS_LEM%" mkdir "%COMMENTS_LEM%"
for /f "delims=" %%F in ('dir /b /a-d "%COMMENTS_OUT%"') do (
  echo Лемматизация "%%F"
  python -m analytics.embeddings.scripts.lemmatize_file -i "%COMMENTS_OUT%\%%F" -o "%COMMENTS_LEM%\%%F"
  if errorlevel 1 (
    echo Ошибка лемматизации файла "%COMMENTS_OUT%\%%F"
    popd
    exit /b 1
  )
)

echo Pipeline finished successfully.
popd
exit /b 0

:tryPython
REM Проверка, что команда Python запускается
set "CMD=%~1"
%CMD% --version >nul 2>&1
if errorlevel 1 (exit /b 1) else (exit /b 0)