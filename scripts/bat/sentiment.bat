@echo off
setlocal EnableDelayedExpansion

REM Sentiment pipeline (Windows .bat equivalent of scripts/bash/sentiment.sh)


chcp 65001

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

:: Defaults
if not defined PYTHON_BIN set "PYTHON_BIN=python3.12"
if not defined VENV_DIR set "VENV_DIR=venv"
if not defined DB_URL set "DB_URL=sqlite:///test_sc.db"
if not defined COMMENTS_LEM set "COMMENTS_LEM=artifacts/tech_comments"
if not defined TITLES_MODEL set "TITLES_MODEL=artifacts/embeddings/words/titles/w2v_titles_300d.model"
if not defined CONTEXT_MODEL set "CONTEXT_MODEL=artifacts/embeddings/words/context/w2v_context_300d.model"
if not defined CORPUS_OUT set "CORPUS_OUT=artifacts/corpus3.csv"

:: Prefer py -3, fallback to python
set "PY_CMD=py -3"
where py >nul 2>&1 || set "PY_CMD=python"

:: Activate venv if it exists (Windows)
if exist "%VENV_DIR%\Scripts\activate.bat" (
  call "%VENV_DIR%\Scripts\activate.bat"
)

set "PY_CMD=%VENV_DIR%\Scripts\python.exe"

echo 1. Проводим сентимент-анализ (analytics.embeddings.scripts.calculate_sentiment)...
%PY_CMD% -m analytics.embeddings.scripts.calculate_sentiment -d "%COMMENTS_LEM%" --titles-kv "%TITLES_MODEL%" --comments-kv "%CONTEXT_MODEL%" --out-csv "%CORPUS_OUT%" --mode vader
if errorlevel 1 (
  echo Ошибка при расчёте сентимента
  exit /b 1
)

echo 2. Рисуем график (visualization.draw_sentiment_plot)...
%PY_CMD% -m visualization.draw_sentiment_plot -i "%CORPUS_OUT%" -o "..\plots\sentiment.png"
if errorlevel 1 (
  echo Ошибка при рисовании графика сентимента
  exit /b 1
)

echo Pipeline finished successfully.
endlocal





