#!/usr/bin/env bash
# Start IdeaForge API + web in detached screen sessions. Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${ORCHESTRATOR_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
API_LOG="/tmp/ideaforge-api.log"
WEB_LOG="/tmp/ideaforge-web.log"
TUNNEL_LOG="/tmp/ideaforge-tunnel.log"
PID_DIR="/tmp/ideaforge-pids"
mkdir -p "$PID_DIR"

if [ -f .env ]; then set -a && source .env && set +a; fi

stop_port() {
  local port=$1
  local pids
  pids=$(lsof -t -i:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(lsof -t -i:"$port" 2>/dev/null || true)
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
  fi
}

wait_healthy() {
  local url=$1
  local label=$2
  local tries=${3:-20}
  for ((i = 1; i <= tries; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "  ✓ $label"
      return 0
    fi
    sleep 1
  done
  echo "  ✗ $label failed — check $API_LOG / $WEB_LOG"
  return 1
}

screen_stop() {
  local name=$1
  if screen -ls | grep -q "[0-9]*\.${name}[[:space:]]"; then
    screen -S "$name" -X quit 2>/dev/null || true
  fi
}

screen_start() {
  local name=$1
  shift
  screen_stop "$name"
  screen -dmS "$name" "$@"
}

chmod +x "$ROOT/scripts/run-api.sh" "$ROOT/scripts/run-web.sh" "$ROOT/scripts/daemon.sh" 2>/dev/null || true

echo "→ Stopping existing services…"
if [ "$(uname -s)" = "Darwin" ]; then
  launchctl bootout "gui/$(id -u)/com.ideaforge.api" 2>/dev/null || true
  launchctl bootout "gui/$(id -u)/com.ideaforge.web" 2>/dev/null || true
fi
screen_stop ideaforge-api
screen_stop ideaforge-web
screen_stop ideaforge-tunnel
stop_port "$API_PORT"
stop_port "$WEB_PORT"
sleep 1

if ! command -v screen >/dev/null 2>&1; then
  echo "✗ GNU screen is required. Install: brew install screen"
  exit 1
fi

echo "→ Starting API (screen: ideaforge-api)…"
screen_start ideaforge-api "$ROOT/scripts/run-api.sh"

echo "→ Starting web (screen: ideaforge-web)…"
screen_start ideaforge-web "$ROOT/scripts/run-web.sh"

wait_healthy "http://localhost:${API_PORT}/health" "API http://localhost:${API_PORT}"
wait_healthy "http://localhost:${WEB_PORT}" "Web http://localhost:${WEB_PORT}"

if command -v cloudflared >/dev/null 2>&1; then
  echo "→ Starting Cloudflare tunnel (screen: ideaforge-tunnel)…"
  screen_start ideaforge-tunnel cloudflared tunnel --url "http://localhost:${API_PORT}"
  TUNNEL_URL=""
  for ((i = 1; i <= 20; i++)); do
    sleep 1
    TUNNEL_URL=$(screen -S ideaforge-tunnel -X hardcopy /tmp/ideaforge-tunnel-cap.txt 2>/dev/null && grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/ideaforge-tunnel-cap.txt 2>/dev/null | head -1) || TUNNEL_URL=""
    [ -n "$TUNNEL_URL" ] && break
  done
  if [ -n "$TUNNEL_URL" ] && curl -sf "${TUNNEL_URL}/health" >/dev/null 2>&1; then
    echo "  ✓ Tunnel $TUNNEL_URL"
    echo "$TUNNEL_URL" > "$PID_DIR/tunnel.url"
  else
    echo "  ⚠ Tunnel starting — localhost works without it"
  fi
fi

echo "→ Stability check (5 polls)…"
ok=0
for i in 1 2 3 4 5; do
  curl -sf "http://localhost:${API_PORT}/health" >/dev/null &&
    curl -sf "http://localhost:${API_PORT}/sessions" >/dev/null &&
    curl -sf "http://localhost:${API_PORT}/session/b87c6b0e-a998-49d8-adee-51dacc582c93" >/dev/null &&
    curl -sf "http://localhost:${WEB_PORT}" >/dev/null && ok=$((ok + 1)) || true
  sleep 2
done
if [ "$ok" -lt 5 ]; then
  echo "  ⚠ Partial stability ($ok/5)"
  exit 1
fi
echo "  ✓ All stable ($ok/5)"

echo ""
echo "Ready:"
echo "  Web:  http://localhost:${WEB_PORT}/?fresh=1"
echo "  API:  http://localhost:${API_PORT}/health"
echo "  Logs: screen -r ideaforge-api | screen -r ideaforge-web"
if [ -f "$PID_DIR/tunnel.url" ]; then
  echo "  Tunnel: $(cat "$PID_DIR/tunnel.url")"
fi
