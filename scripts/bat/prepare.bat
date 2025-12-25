@echo off
setlocal EnableDelayedExpansion

REM Prepare pipeline (Windows .bat equivalent of scripts/bash/prepare.sh)


chcp 65001

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

:: Defaults (can be overridden by environment variables)
if not defined PYTHON_BIN set "PYTHON_BIN=python3"
if not defined VENV_DIR set "VENV_DIR=venv"
if not defined DB_URL set "DB_URL=sqlite:///test_sc.db"
if not defined START_ID set "START_ID=38000000"
if not defined END_ID set "END_ID=38010000"
if not defined WORKERS set "WORKERS=32"
if not defined RAW_OUT set "RAW_OUT=raw_data/hn_data_2.jsonl.gz"
if not defined BATCH_SIZE set "BATCH_SIZE=1000"
if not defined CTX_OUT set "CTX_OUT=artifacts/sentences/context.txt"
if not defined TITLES_OUT set "TITLES_OUT=artifacts/sentences/titles.txt"
if not defined CTX_LEM set "CTX_LEM=artifacts/sentences/context_lem.txt"
if not defined TITLES_LEM set "TITLES_LEM=artifacts/sentences/titles_lem.txt"
if not defined TECH_OUT set "TECH_OUT=artifacts/tech_names.txt"
if not defined MATRIX_OUT set "MATRIX_OUT=artifacts/similarity_matrix.csv"
if not defined REL_MAP_OUT set "REL_MAP_OUT=artifacts/plots/rel_map.png"
if not defined TITLES_TOKENS set "TITLES_TOKENS=artifacts/embeddings/words/titles.tokens.jsonl.gz"
if not defined CONTEXT_TOKENS set "CONTEXT_TOKENS=artifacts/embeddings/words/context.tokens.jsonl.gz"
if not defined TITLES_MODEL_OUT set "TITLES_MODEL_OUT=artifacts/embeddings/words/titles"
if not defined CONTEXT_MODEL_OUT set "CONTEXT_MODEL_OUT=artifacts/embeddings/words/context"
if not defined TITLES_MODEL set "TITLES_MODEL=artifacts/embeddings/words/titles/w2v_titles_300d.model"
if not defined CONTEXT_MODEL set "CONTEXT_MODEL=artifacts/embeddings/words/context/w2v_context_300d.model"
if not defined COMMENTS_OUT set "COMMENTS_OUT=artifacts/tech_comments/"
if not defined COMMENTS_LEM set "COMMENTS_LEM=artifacts/tech"

:: 1. Проверка/установка Python 3.12
call :ensure_python312
if errorlevel 1 (
  echo Ошибка: не удалось найти или установить Python 3.12
  exit /b 1
)
echo Используется Python: %PY_CMD%

echo 2. Создаём виртуальное окружение...
%PY_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 (
  echo Ошибка при создании venv
  exit /b 1
)

set "PY_CMD=%VENV_DIR%\Scripts\python.exe"


:: Activate venv if activation script exists
if exist "%VENV_DIR%\Scripts\activate.bat" (
  call "%VENV_DIR%\Scripts\activate.bat"
)

echo 3. Обновляем pip и устанавливаем зависимости...
%PY_CMD% -m pip install --upgrade pip 
if errorlevel 1 (
  echo pip upgrade failed
  exit /b 1
)
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
  echo pip install failed
  exit /b 1
)

echo 4. Устанавливаем модель spaCy (если требуется)...
%PY_CMD% -m spacy download en_core_web_sm || echo "spaCy model install failed (continue if not needed)"

echo 5. Создаём директории...
if not exist raw_data mkdir raw_data
if not exist artifacts\sentences mkdir artifacts\sentences
if not exist artifacts\embeddings mkdir artifacts\embeddings

echo 6. Скачиваем данные (scripts.retrieve)...
%PY_CMD% -m scripts.retrieve -o "%RAW_OUT%" -s "%START_ID%" -e "%END_ID%" -w "%WORKERS%" --progress-every 10000
if errorlevel 1 (
  echo Ошибка при скачивании данных
  exit /b 1
)

echo 7. Импорт в БД (db.scripts.ingest)...
%PY_CMD% -m db.scripts.ingest -d "%DB_URL%" -i "%RAW_OUT%" -b "%BATCH_SIZE%"
if errorlevel 1 (
  echo Ошибка при импорте в БД
  exit /b 1
)

echo 8. Классификация технологий(analytics.embeddings.scripts.classify_tech)...
%PY_CMD% -m analytics.embeddings.scripts.classify_tech -d "%DB_URL%"
if errorlevel 1 (
  echo Ошибка при классификации технологий
  exit /b 1
)

echo 9. Удаляем из БД истории без упоминания технологий...
%PY_CMD% -m db.scripts.trim -d "%DB_URL%"
if errorlevel 1 (
  echo Ошибка при очистке БД
  exit /b 1
)

echo 10. Экспорт контекста и заголовков(db.scripts.export_context и db.scripts.export_titles)...
%PY_CMD% -m db.scripts.export_context -d "%DB_URL%" -o "%CTX_OUT%" --format txt
if errorlevel 1 (
  echo Ошибка при экспорте контекста
  exit /b 1
)
%PY_CMD% -m db.scripts.export_titles -d "%DB_URL%" -o "%TITLES_OUT%" --format txt
if errorlevel 1 (
  echo Ошибка при экспорте заголовков
  exit /b 1
)

echo 11. Лемматизация (analytics.embeddings.scripts.lemmatize_file)...
%PY_CMD% -m analytics.embeddings.scripts.lemmatize_file -i "%CTX_OUT%" -o "%CTX_LEM%"
if errorlevel 1 (
  echo Ошибка лемматизации контекста
  exit /b 1
)
%PY_CMD% -m analytics.embeddings.scripts.lemmatize_file -i "%TITLES_OUT%" -o "%TITLES_LEM%"
if errorlevel 1 (
  echo Ошибка лемматизации заголовков
  exit /b 1
)

echo 12. Преобразование в токены (analytics.embeddings.scripts.sentences_to_vectors)...
%PY_CMD% -m analytics.embeddings.scripts.sentences_to_vectors -i "%CTX_LEM%" -o "%CONTEXT_TOKENS%"
if errorlevel 1 (
  echo Ошибка при векторизации контекста
  exit /b 1
)
%PY_CMD% -m analytics.embeddings.scripts.sentences_to_vectors -i "%TITLES_LEM%" -o "%TITLES_TOKENS%"
if errorlevel 1 (
  echo Ошибка при векторизации заголовков
  exit /b 1
)

echo 13. Обучение модели (analytics.embeddings.scripts.train_model)...
%PY_CMD% -m analytics.embeddings.scripts.train_model -p "%CONTEXT_TOKENS%" -o "%CONTEXT_MODEL_OUT%"
if errorlevel 1 (
  echo Ошибка при обучении модели контекста
  exit /b 1
)
%PY_CMD% -m analytics.embeddings.scripts.train_model -p "%TITLES_TOKENS%" -o "%TITLES_MODEL_OUT%"
if errorlevel 1 (
  echo Ошибка при обучении модели заголовков
  exit /b 1
)

echo 14. Экспорт технологий (db.scripts.export_tech_names) ...
%PY_CMD% -m db.scripts.export_tech_names -d "%DB_URL%" -o "%TECH_OUT%" --format txt
if errorlevel 1 (
  echo Ошибка при экспорте названий технологий
  exit /b 1
)

echo 15. Экспортируем комментарии технологий по отдельности (db.scripts.export_comments_for_techs)...
%PY_CMD% -m db.scripts.export_comments_for_techs -d "%DB_URL%" -o "%COMMENTS_OUT%" -m 1
if errorlevel 1 (
  echo Ошибка при экспорте комментариев
  exit /b 1
)

echo 16. Лемматизируем комментарии...
call scripts\bat\lemmatize.bat "%COMMENTS_OUT%" "%COMMENTS_LEM%"
if errorlevel 1 (
  echo Ошибка при лемматизации комментариев
  exit /b 1
)

echo Pipeline finished successfully.
endlocal
exit /b 0

:: ---------- ФУНКЦИИ ----------

:ensure_python312
  echo 1. Проверка Python 3.12...

  set "PY_CMD="

  REM 1) Если явно задан PYTHON_BIN — проверяем, что это 3.12
  if defined PYTHON_BIN (
    "%PYTHON_BIN%" -c "import sys; assert sys.version_info[:2]==(3,12)" >nul 2>&1
    if not errorlevel 1 (
      set "PY_CMD=%PYTHON_BIN%"
      goto :eof
    )
  )

  REM 2) Пытаемся py -3.12
  py -3.12 -c "print(1)" >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=py -3.12"
    goto :eof
  )

  REM 3) Пытаемся python3.12 в PATH
  where python3.12 >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=python3.12"
    goto :eof
  )

  echo Python 3.12 не найден. Пытаемся установить...

  call :install_python312
  if errorlevel 1 (
    echo Не удалось установить Python 3.12 автоматически.
    exit /b 1
  )

  REM Повторная проверка после установки
  py -3.12 -c "print(1)" >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=py -3.12"
    goto :eof
  )
  where python3.12 >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=python3.12"
    goto :eof
  )

  echo Python 3.12 установлен, но не найден в PATH/Launcher. Перезапустите терминал и попробуйте снова.
  exit /b 1
goto :eof

:install_python312
  REM Попытка 1: winget
  where winget >nul 2>&1
  if %errorlevel%==0 (
    echo Установка Python 3.12 через winget...
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
    if not errorlevel 1 (
      goto :install_done
    ) else (
      echo winget не смог установить Python 3.12.
    )
  ) else (
    echo winget не найден.
  )

  REM Попытка 2: choco
  where choco >nul 2>&1
  if %errorlevel%==0 (
    echo Установка Python 3.12 через Chocolatey...
    choco install -y python312
    if not errorlevel 1 (
      goto :install_done
    ) else (
      echo Chocolatey не смог установить Python 3.12.
    )
  ) else (
    echo Chocolatey не найден.
  )

  REM Попытка 3: прямая загрузка официального установщика
  set "PY_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
  set "PY_TMP=%TEMP%\python312_installer.exe"

  echo Скачивание установщика Python 3.12 с python.org...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_TMP%' -UseBasicParsing } catch { exit 1 }"
  if errorlevel 1 (
    echo Не удалось скачать установщик по адресу: %PY_URL%
    exit /b 1
  )

  echo Тихая установка Python 3.12 (потребуется подтверждение UAC)...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PY_TMP%' -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1 Shortcuts=1' -Verb RunAs -Wait; exit $LASTEXITCODE"
  set "INSTALL_RC=%ERRORLEVEL%"

  del /q "%PY_TMP%" >nul 2>&1

  if not "%INSTALL_RC%"=="0" (
    echo Установщик Python вернул код %INSTALL_RC%.
    exit /b 1
  )

:install_done
  echo Установка Python 3.12 завершена.
  exit /b 0