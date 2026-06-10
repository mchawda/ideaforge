#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [ -z "${VERCEL_TOKEN:-}" ]; then
  VERCEL_TOKEN="${AI_GATEWAY_API_KEY:-}"
fi
if [ -z "${VERCEL_TOKEN:-}" ]; then
  echo "ERROR: Set VERCEL_TOKEN in .env (https://vercel.com/account/tokens)"
  exit 1
fi

if [ -z "${ORCHESTRATOR_PUBLIC_URL:-}" ]; then
  echo "ERROR: Set ORCHESTRATOR_PUBLIC_URL to your public FastAPI URL (e.g. Render/Railway)"
  exit 1
fi

export NEXT_PUBLIC_API_URL="$ORCHESTRATOR_PUBLIC_URL"
export NEXT_PUBLIC_APP_URL="${NEXT_PUBLIC_APP_URL:-https://idea-forge-eta-six.vercel.app}"

echo "Exporting history snapshot for Vercel…"
python3 scripts/export-history-snapshot.py

echo "Building web app..."
(
  cd apps/web
  NEXT_PUBLIC_API_URL="$ORCHESTRATOR_PUBLIC_URL" \
  NEXT_PUBLIC_APP_URL="${NEXT_PUBLIC_APP_URL:-https://idea-forge-eta-six.vercel.app}" \
  bun run build
)

SCOPE_ARGS=()
SCOPE="${VERCEL_SCOPE:-${VERCEL_TEAM_ID:-}}"
if [ -n "$SCOPE" ]; then
  SCOPE_ARGS=(--scope "$SCOPE")
fi

echo "Deploying to Vercel (production)..."
bunx vercel deploy --prod --yes --cwd apps/web --token "$VERCEL_TOKEN" "${SCOPE_ARGS[@]}"

echo "Done — control panel should be live at https://idea-forge-eta-six.vercel.app"
