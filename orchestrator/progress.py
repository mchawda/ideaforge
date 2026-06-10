from __future__ import annotations

import logging

from orchestrator.state import AgentState, utc_now

_sessions_ref: dict[str, AgentState] | None = None
_debug = logging.getLogger("ideaforge.progress")


def bind_sessions(store: dict[str, AgentState]) -> None:
    global _sessions_ref
    _sessions_ref = store


def report_progress(session_id: str, message: str) -> None:
    if not _sessions_ref or session_id not in _sessions_ref:
        _debug.debug("[%s] [progress] dropped — session not bound", session_id[:8])
        return

    _debug.debug("[%s] [progress] %s", session_id[:8], message)
    state = _sessions_ref[session_id]
    log = list(state.get("progress_log") or [])
    log.append({"message": message, "timestamp": utc_now()})
    updated: AgentState = {
        **state,
        "current_step": message,
        "progress_log": log[-40:],
        "last_heartbeat": utc_now(),
    }
    _sessions_ref[session_id] = updated
    # Persist every progress tick so builds survive tab close and API restarts.
    try:
        from orchestrator import store

        store.persist(updated)
    except Exception as exc:
        _debug.warning("[%s] [progress] persist failed: %s", session_id[:8], exc)
