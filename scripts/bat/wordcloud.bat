@echo off
setlocal EnableDelayedExpansion

REM Wordcloud pipeline (Windows .bat equivalent of scripts/bash/wordcloud.sh)

call "%~dp0common.bat" || exit /b 1

echo 1. Рисуем wordcloud для первого файла из папки tech (visualization.draw_wordcloud)...
set "first_file="
for %%F in ("%COMMENTS_LEM%\*") do (
  if not defined first_file set "first_file=%%~fF"
)
if not defined first_file (
  echo Нет файлов в %COMMENTS_LEM%
  exit /b 1
)
%PY_CMD% -m visualization.draw_wordcloud -i "%first_file%" -o "%PLOTS_DIR%\wc.png"
if errorlevel 1 (
  echo Ошибка при построении wordcloud
  exit /b 1
)

echo Pipeline finished successfully.
endlocal
