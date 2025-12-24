@echo off
setlocal EnableDelayedExpansion

REM IRR pipeline (Windows .bat equivalent of scripts/bash/irr.sh)

:: Always operate from project root (bin)
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\.." >nul 2>&1
set "ROOT_DIR=%CD%\bin"
popd >nul 2>&1
if not exist "%ROOT_DIR%\scripts\" (
  echo Не удалось найти корень проекта: ожидается папка 'scripts' в %ROOT_DIR%
  exit /b 1
)
cd /d "%ROOT_DIR%"

:: Defaults (can be overridden by environment variables)
if not defined PYTHON_BIN set "PYTHON_BIN=python3.12"
if not defined VENV_DIR set "VENV_DIR=venv"
if not defined DB_URL set "DB_URL=sqlite:///test_sc.db"
if not defined START_ID set "START_ID=38000000"
if not defined END_ID set "END_ID=38010000"
if not defined WORKERS set "WORKERS=32"
if not defined RAW_OUT set "RAW_OUT=raw_data/hn_data_2.jsonl.gz"
if not defined BATCH_SIZE set "BATCH_SIZE=1000"
if not defined CTX_OUT set "CTX_OUT=artifacts/sentences/context.txt"
if not defined TITLES_OUT set "TITLES_OUT=artifacts/sentences/titles.txt"
if not defined CTX_LEM set "CTX_LEM=artifacts/sentences/context_lem.txt"
if not defined TITLES_LEM set "TITLES_LEM=artifacts/sentences/titles_lem.txt"
if not defined TECH_OUT set "TECH_OUT=artifacts/tech_names.txt"
if not defined MATRIX_OUT set "MATRIX_OUT=artifacts/similarity_matrix.csv"
if not defined REL_MAP_OUT set "REL_MAP_OUT=artifacts/plots/rel_map.png"
if not defined TITLES_TOKENS set "TITLES_TOKENS=artifacts/embeddings/words/titles.tokens.jsonl.gz"
if not defined CONTEXT_TOKENS set "CONTEXT_TOKENS=artifacts/embeddings/words/context.tokens.jsonl.gz"
if not defined TITLES_MODEL_OUT set "TITLES_MODEL_OUT=artifacts/embeddings/words/titles"
if not defined CONTEXT_MODEL_OUT set "CONTEXT_MODEL_OUT=artifacts/embeddings/words/context"
if not defined TITLES_MODEL set "TITLES_MODEL=artifacts/embeddings/words/titles/w2v_titles_300d.model"
if not defined CONTEXT_MODEL set "CONTEXT_MODEL=artifacts/embeddings/words/context/w2v_context_300d.model"
if not defined META_OUT set "META_OUT=artifacts/meta.csv"
if not defined COEFS_OUT set "COEFS_OUT=artifacts/coefs.csv"

:: Prefer py -3, fallback to python
set "PY_CMD=py -3"
where py >nul 2>&1 || set "PY_CMD=python"

:: Activate venv if it exists (Windows)
if exist "%VENV_DIR%\Scripts\activate.bat" (
  call "%VENV_DIR%\Scripts\activate.bat"
)
echo 1. Экспортируем метаданные статей (db.scripts.export_stories_meta)...
%PY_CMD% -m db.scripts.export_stories_meta -d "%DB_URL%" -o "%META_OUT%"
if errorlevel 1 (
  echo Ошибка при экспорте метаданных
  exit /b 1
)

echo 2. Рассчитываем IRR (analytics.embeddings.scripts.calculate_irr)...
%PY_CMD% -m analytics.embeddings.scripts.calculate_irr -i "%META_OUT%" -m "%TITLES_MODEL%" -o "%COEFS_OUT%"
if errorlevel 1 (
  echo Ошибка при расчёте IRR
  exit /b 1
)

echo 3. Рисуем график (visualization.draw_irr_plot)...
%PY_CMD% -m visualization.draw_irr_plot -i "%COEFS_OUT%" -o "..\plots\irr.png"
if errorlevel 1 (
  echo Ошибка при рисовании графика
  exit /b 1
)

echo Pipeline finished successfully.
endlocal










