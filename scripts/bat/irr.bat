@echo off
setlocal EnableDelayedExpansion

REM IRR pipeline (Windows .bat equivalent of scripts/bash/irr.sh)

call "%~dp0common.bat" || exit /b 1

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
%PY_CMD% -m visualization.draw_irr_plot -i "%COEFS_OUT%" -o "%PLOTS_DIR%\irr.png"
if errorlevel 1 (
  echo Ошибка при рисовании графика
  exit /b 1
)

echo Pipeline finished successfully.
endlocal
