@echo off
:: Общие настройки для scripts\bat\*.bat. Вызывается из них через:  call "%~dp0common.bat" || exit /b 1
:: Своего setlocal нет намеренно: переменные и текущая папка должны остаться у вызывающего скрипта.
:: Любую переменную можно задать заранее в окружении, например:
::   set "DB_URL=sqlite:///D:/hackernews_data/hn.db" && scripts\bat\irr.bat

chcp 65001 >nul

:: Всегда работаем из корня проекта: в релизной раскладке код лежит в bin\, в репозитории — в корне
pushd "%~dp0..\.." >nul 2>&1
set "ROOT_DIR=%CD%\bin"
if not exist "%ROOT_DIR%\scripts\" set "ROOT_DIR=%CD%"
popd >nul 2>&1
if not exist "%ROOT_DIR%\scripts\" (
  echo Не удалось найти корень проекта: ожидается папка 'scripts' в %ROOT_DIR%
  exit /b 1
)
cd /d "%ROOT_DIR%"

if not defined PYTHON_BIN set "PYTHON_BIN=python3.12"
if not defined VENV_DIR set "VENV_DIR=venv"
if not defined DB_URL set "DB_URL=sqlite:///test_sc.db"

:: Загрузка и импорт
if not defined START_ID set "START_ID=38000000"
if not defined END_ID set "END_ID=38010000"
if not defined WORKERS set "WORKERS=32"
if not defined RAW_OUT set "RAW_OUT=raw_data/hn_data_2.jsonl.gz"
if not defined BATCH_SIZE set "BATCH_SIZE=1000"

:: Тексты и токены
if not defined CTX_OUT set "CTX_OUT=artifacts/sentences/context.txt"
if not defined TITLES_OUT set "TITLES_OUT=artifacts/sentences/titles.txt"
if not defined CTX_LEM set "CTX_LEM=artifacts/sentences/context_lem.txt"
if not defined TITLES_LEM set "TITLES_LEM=artifacts/sentences/titles_lem.txt"
if not defined TITLES_TOKENS set "TITLES_TOKENS=artifacts/embeddings/words/titles.tokens.jsonl.gz"
if not defined CONTEXT_TOKENS set "CONTEXT_TOKENS=artifacts/embeddings/words/context.tokens.jsonl.gz"

:: Модели
if not defined TITLES_MODEL_OUT set "TITLES_MODEL_OUT=artifacts/embeddings/words/titles"
if not defined CONTEXT_MODEL_OUT set "CONTEXT_MODEL_OUT=artifacts/embeddings/words/context"
if not defined TITLES_MODEL set "TITLES_MODEL=artifacts/embeddings/words/titles/w2v_titles_300d.model"
if not defined CONTEXT_MODEL set "CONTEXT_MODEL=artifacts/embeddings/words/context/w2v_context_300d.model"

:: Результаты анализа
if not defined TECH_OUT set "TECH_OUT=artifacts/tech_names.txt"
if not defined MATRIX_OUT set "MATRIX_OUT=artifacts/similarity_matrix.csv"
if not defined COMMENTS_OUT set "COMMENTS_OUT=artifacts/tech_comments/"
if not defined COMMENTS_LEM set "COMMENTS_LEM=artifacts/tech"
if not defined META_OUT set "META_OUT=artifacts/meta.csv"
if not defined COEFS_OUT set "COEFS_OUT=artifacts/coefs.csv"
if not defined CORPUS_OUT set "CORPUS_OUT=artifacts/corpus3.csv"
if not defined PLOTS_DIR set "PLOTS_DIR=..\plots"

:: Python из venv, если он уже создан; иначе системный (py -3 или python)
if exist "%VENV_DIR%\Scripts\python.exe" (
  set "PY_CMD=%VENV_DIR%\Scripts\python.exe"
) else (
  set "PY_CMD=py -3"
  where py >nul 2>&1 || set "PY_CMD=python"
)
exit /b 0
