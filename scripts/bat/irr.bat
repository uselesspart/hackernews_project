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
if not defined DB_URL set "DB_URL=sqlite:///test_sc.db"
if not defined META_OUT set "META_OUT=artifacts\meta.csv"
if not defined COEFS_OUT set "COEFS_OUT=artifacts\coefs.csv"
if not defined TITLES_MODEL set "TITLES_MODEL=artifacts\embeddings\words\titles\w2v_titles_300d.model"

REM Активируем виртуальное окружение
set "VENV_ACT=%VENV_DIR%\Scripts\activate.bat"
if not exist "%VENV_ACT%" (
  echo Виртуальное окружение не найдено: "%VENV_ACT%"
  popd
  exit /b 1
)
call "%VENV_ACT%"

echo 1^) Экспортируем метаданные статей (db.scripts.export_stories_meta)...
python -m db.scripts.export_stories_meta -d "%DB_URL%" -o "%META_OUT%"
if errorlevel 1 (echo Ошибка экспорта метаданных & popd & exit /b 1)

echo 2^) Рассчитываем IRR (analytics.embeddings.scripts.calculate_irr)...
python -m analytics.embeddings.scripts.calculate_irr -i "%META_OUT%" -m "%TITLES_MODEL%" -o "%COEFS_OUT%"
if errorlevel 1 (echo Ошибка расчёта IRR & popd & exit /b 1)

echo 3^) Рисуем график (visualization.draw_irr_plot)...
python -m visualization.draw_irr_plot -i "%COEFS_OUT%" -o "..\plots\irr.png"
if errorlevel 1 (echo Ошибка построения графика IRR & popd & exit /b 1)

echo Готово.
popd
exit /b 0