#!/usr/bin/env python3
"""Wire $0 Stripe checkout into an existing v0 product and redeploy."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import httpx
import stripe
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from tools.v0_tools import redeploy_v0_chat, fetch_chat  # noqa: E402

WIRE_MSG = """CRITICAL STRIPE WIRING FIX — do not change layout or copy.

Wire checkout URLs exactly:
- ALL "Start free", "Try for free", "Get started", hero primary CTA, and Free/Starter tier buttons → {free}
- Growth/Pro/Scale/Enterprise paid tier buttons only → {paid}
- Do NOT use the paid link for free-tier CTAs.

After editing, ensure /pricing Free tier and homepage hero CTA use the free Stripe link."""


def _v0_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['V0_API_KEY']}",
        "Content-Type": "application/json",
    }


def _v0_params() -> dict[str, str]:
    team_id = os.getenv("VERCEL_TEAM_ID", "").strip()
    return {"teamId": team_id} if team_id else {}


def ensure_no_card_free_checkout(free_url: str) -> None:
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    links = stripe.PaymentLink.list(limit=100)
    for link in links.data:
        if link.url == free_url and link.payment_method_collection != "if_required":
            stripe.PaymentLink.modify(link.id, payment_method_collection="if_required")
            print(f"Updated {link.id} → if_required (no card for $0)")


def wire_v0_chat(chat_id: str, free_url: str, paid_url: str, session_id: str) -> None:
    before = fetch_chat(chat_id, session_id=session_id)
    version_before = (before.get("latestVersion") or {}).get("id")
    token = free_url.rsplit("/", 1)[-1]
    existing = "\n".join(
        (f.get("content") or "") for f in (before.get("latestVersion") or {}).get("files") or []
    )
    if token in existing:
        print(f"Chat {chat_id} already references free checkout")
        return

    with httpx.Client(timeout=httpx.Timeout(30.0, read=120.0)) as client:
        response = client.post(
            f"https://api.v0.dev/v1/chats/{chat_id}/messages",
            headers=_v0_headers(),
            params=_v0_params(),
            json={"message": WIRE_MSG.format(free=free_url, paid=paid_url)},
        )
        response.raise_for_status()

        for _ in range(60):
            time.sleep(5)
            chat = fetch_chat(chat_id, session_id=session_id)
            version = (chat.get("latestVersion") or {}).get("id")
            files = (chat.get("latestVersion") or {}).get("files") or []
            if version and version != version_before and files:
                content = "\n".join((f.get("content") or "") for f in files)
                if token in content:
                    print(f"Chat {chat_id} updated → {version}")
                    return

    raise RuntimeError(f"Timed out wiring Stripe links for chat {chat_id}")


def patch_session(session_prefix: str, *, final_url: str, chat_id: str, version_id: str, free: str, paid: str) -> None:
    db = ROOT / "data" / "sessions.db"
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT session_id, state_json FROM sessions WHERE session_id LIKE ?",
            (f"{session_prefix}%",),
        ).fetchone()
        if not row:
            raise SystemExit(f"No session matching {session_prefix}")
        sid, state = row[0], json.loads(row[1])
        state["final_url"] = final_url
        state["vercel_deployment_url"] = final_url
        state["stripe_free_payment_link"] = free
        state["stripe_payment_link"] = paid
        state["v0_chat_id"] = chat_id
        state["v0_version_id"] = version_id
        state["current_step"] = f"Live — {final_url}"
        conn.execute(
            "UPDATE sessions SET state_json = ? WHERE session_id = ?",
            (json.dumps(state), sid),
        )
        conn.commit()
        print(f"Patched session {sid[:8]} → {final_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-prefix", required=True)
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--free-url", required=True)
    parser.add_argument("--paid-url", required=True)
    args = parser.parse_args()

    ensure_no_card_free_checkout(args.free_url)
    wire_v0_chat(args.chat_id, args.free_url, args.paid_url, args.session_prefix)
    result = redeploy_v0_chat(args.chat_id, session_id=args.session_prefix)
    patch_session(
        args.session_prefix,
        final_url=result["production_url"],
        chat_id=args.chat_id,
        version_id=result.get("version_id", ""),
        free=args.free_url,
        paid=args.paid_url,
    )


if __name__ == "__main__":
    main()
