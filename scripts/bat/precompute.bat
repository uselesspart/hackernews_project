@echo off
setlocal EnableDelayedExpansion

REM Precompute pipeline (Windows .bat equivalent of scripts/bash/precompute.sh)

call "%~dp0common.bat" || exit /b 1

echo 1. Предрасчёт данных для API (analytics.embeddings.scripts.precompute)...
%PY_CMD% -m analytics.embeddings.scripts.precompute -d "%DB_URL%" --context-model "%CONTEXT_MODEL%" --titles-model "%TITLES_MODEL%"
if errorlevel 1 (
  echo Ошибка при предрасчёте
  exit /b 1
)

echo Pipeline finished successfully.
endlocal
