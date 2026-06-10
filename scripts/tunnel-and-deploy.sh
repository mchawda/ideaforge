#!/usr/bin/env bash
# Start stable tunnel, update .env, redeploy Vercel panel (fixes ERR_CERT_COMMON_NAME_INVALID).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p /tmp/ideaforge-pids

if [ -f .env ]; then set -a && source .env && set +a; fi

curl -sf http://127.0.0.1:8000/health >/dev/null || {
  echo "→ API down — starting services…"
  bash "$ROOT/scripts/start-all.sh"
}

pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 1
: > /tmp/ideaforge-tunnel.log
nohup cloudflared tunnel --url http://127.0.0.1:8000 >> /tmp/ideaforge-tunnel.log 2>&1 &
echo $! > /tmp/ideaforge-pids/tunnel.pid
disown $! 2>/dev/null || true

echo "→ Waiting for tunnel…"
URL=""
for ((i = 1; i <= 30; i++)); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/ideaforge-tunnel.log 2>/dev/null | tail -1 || true)
  if [ -n "$URL" ] && curl -sf --max-time 10 "${URL}/health" | grep -q '"ok"'; then
    echo "  ✓ $URL"
    break
  fi
  URL=""
  sleep 2
done

if [ -z "$URL" ]; then
  echo "✗ Tunnel failed — use http://localhost:3000 for demo"
  exit 1
fi

echo "$URL" > /tmp/ideaforge-pids/tunnel.url
if grep -q '^ORCHESTRATOR_PUBLIC_URL=' .env; then
  sed -i '' "s|^ORCHESTRATOR_PUBLIC_URL=.*|ORCHESTRATOR_PUBLIC_URL=${URL}|" .env
else
  echo "ORCHESTRATOR_PUBLIC_URL=${URL}" >> .env
fi

export ORCHESTRATOR_PUBLIC_URL="$URL"
echo "→ Redeploying Vercel panel with API URL $URL"
bash "$ROOT/scripts/deploy-web.sh"
echo ""
echo "✓ Panel: https://idea-forge-eta-six.vercel.app"
echo "  API:   $URL/health"
echo "  Keep this Mac awake — tunnel dies if cloudflared stops."
