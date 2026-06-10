#!/usr/bin/env python3
"""Point all product Stripe checkout links at the live app after payment."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tools.stripe_tools import configure_session_checkout_redirects, resolve_checkout_success_url  # noqa: E402


def main() -> None:
    db = ROOT / "data" / "sessions.db"
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT session_id, state_json FROM sessions").fetchall()

    for session_id, raw in rows:
        state = json.loads(raw)
        if state.get("status") not in ("complete", "complete_with_warnings"):
            continue
        name = (state.get("pending_approval") or {}).get("product_name") or state.get("product_name") or session_id[:8]
        product_url = (state.get("final_url") or state.get("vercel_deployment_url") or "").strip()
        if not product_url or "buy.stripe.com" in product_url:
            print(f"skip {name}: no product URL")
            continue
        success = resolve_checkout_success_url(product_url)
        updated = configure_session_checkout_redirects(state, product_url=product_url, session_id=session_id)
        print(f"{name}: {success} ({len(updated)} link(s))")


if __name__ == "__main__":
    main()
