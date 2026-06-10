#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -f .env ]; then set -a && source .env && set +a; fi
source .venv/bin/activate
export PYTHONPATH=.
export DISABLE_AUTO_RESUME="${DISABLE_AUTO_RESUME:-true}"
exec uvicorn orchestrator.main:app \
  --host "${ORCHESTRATOR_HOST:-0.0.0.0}" \
  --port "${ORCHESTRATOR_PORT:-8000}" \
  --workers 1 \
  --timeout-keep-alive 30
