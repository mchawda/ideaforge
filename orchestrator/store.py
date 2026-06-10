from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from orchestrator.state import AgentState, utc_now

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("SESSION_DB_PATH", str(ROOT / "data" / "sessions.db")))


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def persist(state: AgentState) -> None:
    init_db()
    session_id = state["session_id"]
    payload = json.dumps(state, default=str)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (session_id, payload, utc_now()),
        )
        conn.commit()


def load(session_id: str) -> AgentState | None:
    if not DB_PATH.exists():
        return None
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT state_json FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def load_all() -> dict[str, AgentState]:
    if not DB_PATH.exists():
        return {}
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT session_id, state_json FROM sessions").fetchall()
    return {row[0]: json.loads(row[1]) for row in rows}


def delete_session(session_id: str) -> bool:
    """Remove a session from the store. Returns True if a row was deleted."""
    if not DB_PATH.exists():
        return False
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "DELETE FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
        return cursor.rowcount > 0


def list_summaries() -> list[dict[str, str | None]]:
    """Lightweight index of all persisted forges for the Builds page."""
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT session_id, state_json, updated_at
            FROM sessions
            ORDER BY updated_at DESC
            """
        ).fetchall()

    summaries: list[dict[str, str | None]] = []
    for session_id, state_json, updated_at in rows:
        state = json.loads(state_json)
        summaries.append(
            {
                "session_id": session_id,
                "product_name": state.get("product_name") or state.get("user_input", "Untitled"),
                "status": state.get("status", "unknown"),
                "v0_status": state.get("v0_status"),
                "final_url": state.get("final_url") or state.get("vercel_deployment_url"),
                "started_at": state.get("started_at"),
                "updated_at": updated_at,
                "user_input": (state.get("user_input") or "")[:120],
            }
        )
    return summaries
