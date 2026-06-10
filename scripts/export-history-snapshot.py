#!/usr/bin/env python3
"""Export local sessions for Vercel History (works without live API tunnel)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.api_view import public_session_view
from orchestrator import store

OUT = ROOT / "apps" / "web" / "public"
STATES = OUT / "session-states"


def main() -> None:
    store.init_db()
    summaries = store.list_summaries()
    OUT.mkdir(parents=True, exist_ok=True)
    STATES.mkdir(parents=True, exist_ok=True)

    (OUT / "history-snapshot.json").write_text(
        json.dumps({"sessions": summaries}, indent=2),
        encoding="utf-8",
    )

    for summary in summaries:
        sid = summary["session_id"]
        state = store.load(sid)
        if not state:
            continue
        slim = public_session_view({**state, "resumable": False})
        (STATES / f"{sid}.json").write_text(json.dumps(slim, indent=2), encoding="utf-8")

    print(f"Exported {len(summaries)} session(s) → apps/web/public/history-snapshot.json")


if __name__ == "__main__":
    main()
