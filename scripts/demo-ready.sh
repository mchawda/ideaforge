#!/usr/bin/env bash
# Prepare IdeaForge for a clean video demo — run from repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then set -a && source .env && set +a; fi

echo "→ Pausing in-flight forges (won't compete with your demo)…"
python3 <<'PY'
import json, sqlite3

PAUSED = "Paused — demo recording in progress"
with sqlite3.connect("data/sessions.db") as conn:
    for sid, raw in conn.execute("SELECT session_id, state_json FROM sessions").fetchall():
        s = json.loads(raw)
        status = s.get("status", "")
        if status in ("building", "generating_ui", "researching", "provisioning_aws", "setting_up_stripe", "finalizing"):
            s["status"] = "complete_with_warnings"
            s["v0_status"] = "skipped"
            s["current_step"] = PAUSED
            conn.execute(
                "UPDATE sessions SET state_json=? WHERE session_id=?",
                (json.dumps(s), sid),
            )
            print(f"  paused {s.get('product_name', sid[:8])}")
    conn.commit()
PY

echo "→ Restarting all services…"
bash "$ROOT/scripts/start-all.sh"

cat <<'EOF'

✓ Demo-ready

  1. Open:  http://localhost:3000/?fresh=1
  2. Click "Your idea" and paste your demo prompt
  3. Hit Build → approve strategy → wait ~15 min for v0
  4. History → Open (product) / Details (pipeline)

  Suggested prompt:
  "AI invoice tool for freelancers — scan receipts, auto-categorize expenses,
   Stripe subscription at $19/mo"

EOF
