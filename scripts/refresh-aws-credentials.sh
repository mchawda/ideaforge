#!/usr/bin/env bash
# Refresh AWS sandbox credentials in .env (hackathon session tokens expire ~24h).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

echo "AWS sandbox credentials expire every ~24 hours."
echo "You need fresh: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN"
echo ""

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
HOW TO GET NEW KEYS (SuperAI hackathon sandbox)
==============================================

Method 1 — Hackathon / Event portal (most common)
  1. Open the AWS access link from kickoff (Event Engine, workshop email, or Telegram).
  2. Sign in → choose your sandbox account.
  3. Click "Programmatic access" or "Command line credentials".
  4. Copy the three export lines (or the three values).
  5. Run:  bash scripts/refresh-aws-credentials.sh --from-clipboard
     Or paste values when prompted:  bash scripts/refresh-aws-credentials.sh --interactive

Method 2 — AWS Console (if already logged into sandbox in browser)
  1. AWS Console → top-right account menu → "Command line or programmatic access".
  2. Copy "Option 1: export environment variables" or the three keys.
  3. Run this script with --interactive or --from-clipboard.

Method 3 — AWS SSO (only if your team set up SSO)
  aws sso login --profile YOUR_PROFILE
  eval "$(aws configure export-credentials --profile YOUR_PROFILE --format env)"
  bash scripts/refresh-aws-credentials.sh --from-env

After updating .env:
  source .venv/bin/activate && python scripts/verify_keys.py
  npm run start   # restart API so builds pick up new creds

EOF
  exit 0
fi

update_env_var() {
  local key=$1 value=$2
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # macOS sed
    sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

apply_creds() {
  local id secret token
  id=${AWS_ACCESS_KEY_ID:-}
  secret=${AWS_SECRET_ACCESS_KEY:-}
  token=${AWS_SESSION_TOKEN:-}
  if [[ -z "$id" || -z "$secret" ]]; then
    echo "✗ Missing AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY"
    exit 1
  fi
  if [[ -z "$token" ]]; then
    echo "⚠ No AWS_SESSION_TOKEN — OK for long-lived keys, but hackathon sandboxes usually need one."
  fi
  [[ -f "$ENV_FILE" ]] || { echo "✗ No .env at $ENV_FILE"; exit 1; }
  update_env_var "AWS_ACCESS_KEY_ID" "$id"
  update_env_var "AWS_SECRET_ACCESS_KEY" "$secret"
  if [[ -n "$token" ]]; then
    update_env_var "AWS_SESSION_TOKEN" "$token"
  fi
  echo "✓ Updated $ENV_FILE"
  echo "→ Verifying…"
  set -a && source "$ENV_FILE" && set +a
  if aws sts get-caller-identity --region "${AWS_REGION:-${AWS_DEFAULT_REGION:-us-west-2}}" >/dev/null 2>&1; then
    echo "✓ AWS STS OK — account $(aws sts get-caller-identity --query Account --output text)"
  else
    echo "✗ STS still failing — double-check copied values"
    exit 1
  fi
}

case "${1:-}" in
  --from-env)
    apply_creds
    ;;
  --interactive)
    read -r -p "AWS_ACCESS_KEY_ID: " AWS_ACCESS_KEY_ID
    read -r -p "AWS_SECRET_ACCESS_KEY: " AWS_SECRET_ACCESS_KEY
    read -r -p "AWS_SESSION_TOKEN: " AWS_SESSION_TOKEN
    export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
    apply_creds
    ;;
  --from-clipboard)
    if ! command -v pbpaste >/dev/null; then
      echo "Paste export block, then Ctrl-D:"
      eval "$(cat)"
    else
      clip=$(pbpaste)
      if echo "$clip" | grep -q AWS_ACCESS_KEY_ID; then
        eval "$(echo "$clip" | grep -E '^export AWS_|^AWS_')"
      else
        echo "Clipboard doesn't look like AWS export block. Paste manually:"
        eval "$(cat)"
      fi
    fi
    apply_creds
    ;;
  *)
    echo "Usage:"
    echo "  bash scripts/refresh-aws-credentials.sh --help"
    echo "  bash scripts/refresh-aws-credentials.sh --interactive"
    echo "  bash scripts/refresh-aws-credentials.sh --from-clipboard"
    echo "  bash scripts/refresh-aws-credentials.sh --from-env   # after: eval \$(aws configure export-credentials ...)"
    exit 1
    ;;
esac
