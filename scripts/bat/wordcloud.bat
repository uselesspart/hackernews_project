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
if not defined COMMENTS_LEM set "COMMENTS_LEM=artifacts\tech"

REM Активируем виртуальное окружение
set "VENV_ACT=%VENV_DIR%\Scripts\activate.bat"
if not exist "%VENV_ACT%" (
  echo Виртуальное окружение не найдено: "%VENV_ACT%"
  popd
  exit /b 1
)
call "%VENV_ACT%"

echo 1^) Рисуем wordcloud для первого файла из папки tech (visualization.draw_wordcloud)...
set "first_file="
for /f "delims=" %%F in ('dir /b /a-d "%COMMENTS_LEM%"') do (
  set "first_file=%COMMENTS_LEM%\%%F"
  goto gotFile
)
:gotFile
if not defined first_file (
  echo Нет файлов в "%COMMENTS_LEM%"
  popd
  exit /b 1
)
python -m visualization.draw_wordcloud -i "%first_file%" -o "..\plots\wc.png"
if errorlevel 1 (echo Ошибка построения wordcloud & popd & exit /b 1)

echo Pipeline finished successfully.
popd
exit /b 0