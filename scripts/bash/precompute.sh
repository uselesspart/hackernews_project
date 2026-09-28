#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

activate_venv

echo "1) Предрасчёт данных для API (analytics.embeddings.scripts.precompute)..."
python -m analytics.embeddings.scripts.precompute -d "$DB_URL" --context-model "$CONTEXT_MODEL" --titles-model "$TITLES_MODEL"

echo "Pipeline finished successfully."
