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
if not defined VENV_DIR set "VENV_DIR=venv"
if not defined COMMENTS_LEM set "COMMENTS_LEM=artifacts\tech"
if not defined TITLES_MODEL set "TITLES_MODEL=artifacts\embeddings\words\titles\w2v_titles_300d.model"
if not defined CONTEXT_MODEL set "CONTEXT_MODEL=artifacts\embeddings\words\context\w2v_context_300d.model"
if not defined CORPUS_OUT set "CORPUS_OUT=artifacts\corpus3.csv"

REM Активируем виртуальное окружение
set "VENV_ACT=%VENV_DIR%\Scripts\activate.bat"
if not exist "%VENV_ACT%" (
  echo Виртуальное окружение не найдено: "%VENV_ACT%"
  popd
  exit /b 1
)
call "%VENV_ACT%"

echo 1^) Проводим сентимент-анализ (analytics.embeddings.scripts.calculate_sentiment)...
python -m analytics.embeddings.scripts.calculate_sentiment -d "%COMMENTS_LEM%" --titles-kv "%TITLES_MODEL%" --comments-kv "%CONTEXT_MODEL%" --out-csv "%CORPUS_OUT%" --mode vader
if errorlevel 1 (echo Ошибка расчёта сентимента & popd & exit /b 1)

echo 2^) Рисуем график (visualization.draw_sentiment_plot)...
python -m visualization.draw_sentiment_plot -i "%CORPUS_OUT%" -o "..\plots\sentiment.png"
if errorlevel 1 (echo Ошибка построения графика сентимента & popd & exit /b 1)

echo Pipeline finished successfully.
popd
exit /b 0