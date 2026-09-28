@echo off
setlocal EnableDelayedExpansion

REM Sentiment pipeline (Windows .bat equivalent of scripts/bash/sentiment.sh)

call "%~dp0common.bat" || exit /b 1

echo 1. Проводим сентимент-анализ (analytics.embeddings.scripts.calculate_sentiment)...
%PY_CMD% -m analytics.embeddings.scripts.calculate_sentiment -d "%COMMENTS_LEM%" --titles-kv "%TITLES_MODEL%" --comments-kv "%CONTEXT_MODEL%" --out-csv "%CORPUS_OUT%" --mode vader
if errorlevel 1 (
  echo Ошибка при расчёте сентимента
  exit /b 1
)

echo 2. Рисуем график (visualization.draw_sentiment_plot)...
%PY_CMD% -m visualization.draw_sentiment_plot -i "%CORPUS_OUT%" -o "%PLOTS_DIR%\sentiment.png"
if errorlevel 1 (
  echo Ошибка при рисовании графика сентимента
  exit /b 1
)

echo Pipeline finished successfully.
endlocal
