@echo off
setlocal EnableDelayedExpansion

REM Скрипт: прогнать все файлы из папки через lemmatize_file и сохранить в artifacts\tech
REM Использование:
REM    lemmatize.bat INPUT_DIR [OUTPUT_DIR]

:: Проверка аргументов
if "%~1"=="" (
  echo Usage: %~nx0 INPUT_DIR [OUTPUT_DIR]
  exit /b 1
)

:: Установка переменных входной и выходной папок
set "IN_DIR=%~1"
if "%~2"=="" (
  set "OUT_DIR=artifacts\tech"
) else (
  set "OUT_DIR=%~2"
)

:: Проверка существования входной директории
if not exist "%IN_DIR%\" (
  echo Input dir not found: %IN_DIR%
  exit /b 1
)

:: Создать выходную директорию, если надо
if not exist "%OUT_DIR%\" (
  mkdir "%OUT_DIR%"
)

:: Выбираем команду для запуска Python: предпочитаем "py -3", если нет — "python"
set "PY_CMD=py -3"
where py >nul 2>&1 || set "PY_CMD=python"

echo Input dir: %IN_DIR%
echo Output dir: %OUT_DIR%
echo Running lemmatization...

:: Перебор всех файлов (без рекурсии). Пропускаем каталоги.
for %%F in ("%IN_DIR%\*") do (
  if not exist "%%~fF\" (
    set "bn=%%~nxF"
    set "name=%%~nF"
    set "extRaw=%%~xF"

    if "!extRaw!"=="" (
      set "ext=txt"
    ) else (
      set "ext=!extRaw:~1!"
    )

    set "outfile=%OUT_DIR%\!name!_lem.!ext!"

    echo -> Processing: !bn!
    %PY_CMD% -m analytics.embeddings.scripts.lemmatize_file -i "%%~fF" -o "!outfile!"
    if errorlevel 1 (
      echo Error processing "!bn!"
      exit /b 1
    )

    echo    Saved: !outfile!
  )
)

echo Done.
endlocal