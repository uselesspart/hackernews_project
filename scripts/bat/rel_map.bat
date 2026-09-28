@echo off
setlocal EnableDelayedExpansion

REM Relationship map pipeline (Windows .bat equivalent of scripts/bash/rel_map.sh)

call "%~dp0common.bat" || exit /b 1

echo 1. Построение матрицы отношений (analytics.embeddings.scripts.build_rel_matrix)...
%PY_CMD% -m analytics.embeddings.scripts.build_rel_matrix -i "%TECH_OUT%" -m "%CONTEXT_MODEL%" -o "%MATRIX_OUT%"
if errorlevel 1 (
  echo Ошибка при построении матрицы отношений
  exit /b 1
)

echo 2. Визуализация карты близости (visualization.draw_relationship_map)...
%PY_CMD% -m visualization.draw_relationship_map -m "%MATRIX_OUT%" -t "%TECH_OUT%" -o "%PLOTS_DIR%\rel_map.png"
if errorlevel 1 (
  echo Ошибка при визуализации карты близости
  exit /b 1
)

echo Pipeline finished successfully.
endlocal
