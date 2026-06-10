from __future__ import annotations

from typing import Any

# Fields kept server-side only — not needed by the web UI polling /session.
_STRIP_KEYS = frozenset(
    {
        "generated_ui_code",
        "market_research",
        "v0_prompt",
        "competitors",
        "pain_points",
        "demand_signals",
    }
)


def public_session_view(state: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in state.items() if key not in _STRIP_KEYS}
