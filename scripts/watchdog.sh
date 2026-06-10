#!/usr/bin/env bash
# Restart API if health check fails. Started by start-all.sh.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${ORCHESTRATOR_PORT:-8000}"
API_LOG="/tmp/ideaforge-api.log"
LOG="/tmp/ideaforge-watchdog.log"

cd "$ROOT"
if [ -f .env ]; then set -a && source .env && set +a; fi

start_api() {
  source .venv/bin/activate
  export PYTHONPATH=.
  export DISABLE_AUTO_RESUME="${DISABLE_AUTO_RESUME:-true}"
  bash "$ROOT/scripts/daemon.sh" "$API_LOG" \
    uvicorn orchestrator.main:app \
    --host "${ORCHESTRATOR_HOST:-0.0.0.0}" \
    --port "$API_PORT" \
    --workers 1 \
    --timeout-keep-alive 30 \
    >/dev/null
  echo "$(date -Iseconds) restarted API pid=$!" >> "$LOG"
}

echo "$(date -Iseconds) watchdog started" >> "$LOG"
while true; do
  sleep 10
  if ! curl -sf "http://localhost:${API_PORT}/health" >/dev/null 2>&1; then
    echo "$(date -Iseconds) API down — restarting" >> "$LOG"
    pids=$(lsof -t -i:"$API_PORT" 2>/dev/null || true)
    [ -n "$pids" ] && kill $pids 2>/dev/null || true
    sleep 1
    start_api
    sleep 3
  fi
done
