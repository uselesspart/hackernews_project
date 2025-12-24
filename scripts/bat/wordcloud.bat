@echo off
setlocal EnableDelayedExpansion

REM Wordcloud pipeline (Windows .bat equivalent of scripts/bash/wordcloud.sh)

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
if not defined VENV_DIR set "VENV_DIR=venv"
if not defined COMMENTS_LEM set "COMMENTS_LEM=artifacts/tech"

:: Prefer py -3, fallback to python
set "PY_CMD=py -3"
where py >nul 2>&1 || set "PY_CMD=python"

:: Activate venv if it exists (Windows)
if exist "%VENV_DIR%\Scripts\activate.bat" (
  call "%VENV_DIR%\Scripts\activate.bat"
)

echo 1. Рисуем wordcloud для первого файла из папки tech (visualization.draw_wordcloud)...
set "first_file="
for %%F in ("%COMMENTS_LEM%\*") do (
  if not defined first_file set "first_file=%%~fF"
)
if not defined first_file (
  echo Нет файлов в %COMMENTS_LEM%
  exit /b 1
)
%PY_CMD% -m visualization.draw_wordcloud -i "%first_file%" -o "..\plots\wc.png"
if errorlevel 1 (
  echo Ошибка при построении wordcloud
  exit /b 1
)

echo Pipeline finished successfully.
endlocal
















