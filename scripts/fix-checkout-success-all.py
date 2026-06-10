#!/usr/bin/env python3
"""Add post-checkout success UX to every deployed product."""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tools.aura_html_tools import deploy_static_html, _slugify  # noqa: E402
from tools.checkout_success import (  # noqa: E402
    V0_CHECKOUT_SUCCESS_MESSAGE,
    inject_checkout_success_script,
)
from tools.stripe_tools import configure_session_checkout_redirects  # noqa: E402
from tools.v0_tools import fetch_chat, redeploy_v0_chat  # noqa: E402
from tools.vercel_tools import ensure_project_public  # noqa: E402

DB = ROOT / "data" / "sessions.db"

V0_CHATS = {
    "30301ad5": "vGKW0lLx6fV",  # BloodLens
    "52a67c3a": "oIfDeiajAwD",  # AskCRM
    "86da655a": "pPQn93ieU6B",  # Helix
    "aea4f8f3": "jZQ9gaAjDpC",  # LotReady
}


def _v0_headers() -> dict[str, str]:
    import os

    return {
        "Authorization": f"Bearer {os.environ['V0_API_KEY']}",
        "Content-Type": "application/json",
    }


def _v0_params() -> dict[str, str]:
    import os

    team = os.getenv("VERCEL_TEAM_ID", "").strip()
    return {"teamId": team} if team else {}


def _project_from_url(url: str) -> str:
    match = re.search(r"https://([a-z0-9-]+)(?:-[a-z0-9]+)?-ideaforge-projects\.vercel\.app", url)
    if match:
        return match.group(1)
    match = re.search(r"https://([a-z0-9-]+)\.vercel\.app", url)
    return match.group(1) if match else ""


def patch_aura_html(state: dict, session_id: str) -> str:
    """Regenerate from aura.build — never re-fetch live HTML (preview shell breaks deploys)."""
    from tools.aura_build_tools import build_and_deploy_aura_product

    name = state.get("product_name") or "product"
    aura = state.get("aura_template") or {"id": "nexus-cyber", "aura_slug": "nexus-cyber"}
    project = _slugify(name, session_id)
    print(f"  aura.build regenerate {name}")
    result = build_and_deploy_aura_product(
        state, aura, session_id=session_id[:8], project_name=project
    )
    html = inject_checkout_success_script(result["html"])
    live = deploy_static_html(html, project_name=project, session_id=session_id[:8])
    ensure_project_public(_project_from_url(live) or project)
    return live


def patch_v0_chat(chat_id: str, session_prefix: str) -> str:
    before = fetch_chat(chat_id, session_id=session_prefix)
    vid_before = (before.get("latestVersion") or {}).get("id")
    content_before = "\n".join(
        (f.get("content") or "") for f in (before.get("latestVersion") or {}).get("files") or []
    )
    if "CheckoutSuccessBanner" in content_before or "checkout=success" in content_before:
        print(f"  v0 chat {chat_id} already has checkout banner")
    else:
        print(f"  v0 messaging {chat_id}…")
        with httpx.Client(timeout=httpx.Timeout(30.0, read=180.0)) as client:
            client.post(
                f"https://api.v0.dev/v1/chats/{chat_id}/messages",
                headers=_v0_headers(),
                params=_v0_params(),
                json={"message": V0_CHECKOUT_SUCCESS_MESSAGE},
            )
        deadline = time.time() + 600
        while time.time() < deadline:
            time.sleep(8)
            chat = fetch_chat(chat_id, session_id=session_prefix)
            vid = (chat.get("latestVersion") or {}).get("id")
            files = (chat.get("latestVersion") or {}).get("files") or []
            content = "\n".join((f.get("content") or "") for f in files)
            if vid and vid != vid_before and files and (
                "CheckoutSuccessBanner" in content or "checkout=success" in content
            ):
                print(f"  v0 updated {vid}")
                break
        else:
            print(f"  warning: v0 timeout for {chat_id}, redeploying latest anyway")

    result = redeploy_v0_chat(chat_id, session_id=session_prefix)
    return result["production_url"]


def main() -> None:
    with sqlite3.connect(DB) as conn:
        rows = conn.execute("SELECT session_id, state_json FROM sessions").fetchall()

    for session_id, raw in rows:
        state = json.loads(raw)
        if state.get("status") not in ("complete", "complete_with_warnings"):
            continue

        name = (state.get("pending_approval") or {}).get("product_name") or state.get("product_name") or "?"
        prefix = session_id[:8]
        ui = state.get("ui_builder") or ""
        print(f"\n=== {name} ({prefix}) ===")

        try:
            if ui == "aura_html":
                live = patch_aura_html(state, session_id)
            elif prefix in V0_CHATS:
                live = patch_v0_chat(V0_CHATS[prefix], prefix)
            else:
                print("  skip: unknown builder")
                continue

            state["final_url"] = live
            state["vercel_deployment_url"] = live
            state["current_step"] = f"Live — {live}"
            configure_session_checkout_redirects(state, product_url=live, session_id=prefix)

            with sqlite3.connect(DB) as conn:
                conn.execute(
                    "UPDATE sessions SET state_json = ? WHERE session_id = ?",
                    (json.dumps(state), session_id),
                )
                conn.commit()
            print(f"  live → {live}")
        except Exception as exc:
            print(f"  FAILED: {exc}")


if __name__ == "__main__":
    main()
