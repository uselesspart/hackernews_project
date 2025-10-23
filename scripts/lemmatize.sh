#!/usr/bin/env bash
set -euo pipefail

# Скрипт: прогнать все файлы из папки через lemmatize_file и сохранить в artifacts/tech
# Использование:
#   ./lemmatize_dir.sh /path/to/input_dir [optional_output_dir]
# Пример:
#   ./lemmatize_dir.sh artifacts/tech_comments artifacts/tech

IN_DIR="${1:-}"
OUT_DIR="${2:-artifacts/tech}"

if [[ -z "$IN_DIR" ]]; then
  echo "Usage: $0 INPUT_DIR [OUTPUT_DIR]"
  exit 1
fi

if [[ ! -d "$IN_DIR" ]]; then
  echo "Input dir not found: $IN_DIR"
  exit 1
fi

mkdir -p "$OUT_DIR"

echo "Input dir: $IN_DIR"
echo "Output dir: $OUT_DIR"
echo "Running lemmatization..."

# Перебор всех обычных файлов в директории (без рекурсии)
# Безопасно для пробелов в именах файлов
find "$IN_DIR" -maxdepth 1 -type f -print0 | while IFS= read -r -d '' infile; do
  bn="$(basename "$infile")"

  # Определяем имя и расширение
  if [[ "$bn" == *.* ]]; then
    name="${bn%.*}"
    ext="${bn##*.}"
  else
    name="$bn"
    ext="txt"
  fi

  outfile="$OUT_DIR/${name}_lem.${ext}"

  echo "-> Processing: $bn"
  python3 -m analytics.embeddings.scripts.lemmatize_file -i "$infile" -o "$outfile"
  echo "   Saved: $outfile"
done

echo "Done."