@echo off
setlocal

:: Настройки (можно изменить)
set "PYTHON_BIN=python3.11"
set "VENV_DIR=venv"
set "DB_URL=sqlite:///hn.db"
set "START_ID=38000000"
set "END_ID=38010000"
set "WORKERS=8"
set "RAW_OUT=raw_data\hn_data.jsonl.gz"
set "BATCH_SIZE=1000"
set "CTX_OUT=artifacts\sentences\context.txt"
set "CTX_LEM=artifacts\sentences\context_lem.txt"

where %PYTHON_BIN% >nul 2>&1
if errorlevel 1 (
  echo Python not found. Install Python and ensure it's on PATH.
  exit /b 1
)

echo Creating virtualenv...
%PYTHON_BIN% -m venv %VENV_DIR%
call "%VENV_DIR%\Scripts\activate.bat"

echo Upgrading pip and installing requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo Installing spaCy model...
python -m spacy download en_core_web_sm || echo spaCy model install failed (continue if not needed)

echo Creating directories...
if not exist raw_data mkdir raw_data
if not exist artifacts\sentences mkdir artifacts\sentences
if not exist artifacts\embeddings mkdir artifacts\embeddings

echo Retrieving data...
python -m scripts.retrieve -o "%RAW_OUT%" -s %START_ID% -e %END_ID% -w %WORKERS% --progress-every 10000

echo Ingesting into DB...
python -m db.scripts.ingest -d "%DB_URL%" -i "%RAW_OUT%" -b %BATCH_SIZE%

echo Exporting context...
python -m db.scripts.export_context -d "%DB_URL%" -o "%CTX_OUT%" --format txt

echo Lemmatizing...
python -m analytics.embeddings.scripts.lemmatize_file -i "%CTX_OUT%" -o "%CTX_LEM%"

echo Sentences to vectors...
python -m analytics.embeddings.scripts.sentences_to_vectors -i "%CTX_LEM%"

echo Pipeline finished successfully.
endlocal