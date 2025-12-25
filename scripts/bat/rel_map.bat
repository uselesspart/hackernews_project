@echo off
setlocal EnableDelayedExpansion

REM Relationship map pipeline (Windows .bat equivalent of scripts/bash/rel_map.sh)

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
if not defined TECH_OUT set "TECH_OUT=artifacts/tech_names.txt"
if not defined MATRIX_OUT set "MATRIX_OUT=artifacts/similarity_matrix.csv"
if not defined REL_MAP_OUT set "REL_MAP_OUT=..\plots\rel_map.png"
if not defined CONTEXT_MODEL set "CONTEXT_MODEL=artifacts/embeddings/words/context/w2v_context_300d.model"

:: Prefer py -3, fallback to python
set "PY_CMD=py -3"
where py >nul 2>&1 || set "PY_CMD=python"

:: Activate venv if it exists (Windows)
if exist "%VENV_DIR%\Scripts\activate.bat" (
  call "%VENV_DIR%\Scripts\activate.bat"
)

set "PY_CMD=%VENV_DIR%\Scripts\python.exe"

chcp 65001

echo 1. Построение матрицы отношений (analytics.embeddings.scripts.build_rel_matrix)...
%PY_CMD% -m analytics.embeddings.scripts.build_rel_matrix -i "%TECH_OUT%" -m "%CONTEXT_MODEL%" -o "%MATRIX_OUT%"
if errorlevel 1 (
  echo Ошибка при построении матрицы отношений
  exit /b 1
)

echo 2. Визуализация карты близости (visualization.draw_relationship_map)...
%PY_CMD% -m visualization.draw_relationship_map -m "%MATRIX_OUT%" -t "%TECH_OUT%" -o "%REL_MAP_OUT%"
if errorlevel 1 (
  echo Ошибка при визуализации карты близости
  exit /b 1
)

echo Pipeline finished successfully.
endlocal





