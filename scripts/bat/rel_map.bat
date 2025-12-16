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
if not defined TECH_OUT set "TECH_OUT=artifacts\tech_names.txt"
if not defined CONTEXT_MODEL set "CONTEXT_MODEL=artifacts\embeddings\words\context\w2v_context_300d.model"
if not defined MATRIX_OUT set "MATRIX_OUT=artifacts\similarity_matrix.csv"
if not defined REL_MAP_OUT set "REL_MAP_OUT=..\plots\rel_map.png"

REM Активируем виртуальное окружение
set "VENV_ACT=%VENV_DIR%\Scripts\activate.bat"
if not exist "%VENV_ACT%" (
  echo Виртуальное окружение не найдено: "%VENV_ACT%"
  popd
  exit /b 1
)
call "%VENV_ACT%"

echo 1^) Построение матрицы отношений (analytics.embeddings.scripts.build_rel_matrix)...
python -m analytics.embeddings.scripts.build_rel_matrix -i "%TECH_OUT%" -m "%CONTEXT_MODEL%" -o "%MATRIX_OUT%"
if errorlevel 1 (echo Ошибка построения матрицы & popd & exit /b 1)

echo 2^) Визуализация карты близости (visualization.draw_relationship_map)...
python -m visualization.draw_relationship_map -m "%MATRIX_OUT%" -t "%TECH_OUT%" -o "%REL_MAP_OUT%"
if errorlevel 1 (echo Ошибка визуализации карты близости & popd & exit /b 1)

echo Pipeline finished successfully.
popd
exit /b 0