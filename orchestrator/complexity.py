from __future__ import annotations

import os
from typing import Any

from orchestrator.llm import chat_json, model_for_tier
from orchestrator.stage_log import info, warning
from orchestrator.state import AgentState


def _fast_mode() -> bool:
    return os.getenv("FAST_MODE", "false").strip().lower() in {"1", "true", "yes"}


def estimate_initial(state: AgentState) -> dict[str, Any]:
    """Rough estimate before research completes."""
    ideabrowser = state.get("input_mode") == "ideabrowser" and bool(state.get("ideabrowser_url"))
    research_min = 0.5 if ideabrowser else 1.5
    return {
        "complexity": "standard",
        "total_minutes": round(research_min + 1 + 0.5 + (0 if _fast_mode() else 5), 1),
        "phases": {
            "research": {"minutes": research_min, "label": "Exa research"},
            "strategy": {"minutes": 1.0, "label": "Strategy (Claude Opus 4.8)"},
            "approval": {"minutes": 0.5, "label": "Your review"},
            "deploy": {"minutes": 0.5, "label": "Stripe + AWS (parallel)"},
            "v0": {
                "minutes": 0 if _fast_mode() else 5.0,
                "label": "v0 UI (background)" if not _fast_mode() else "v0 skipped (turbo)",
            },
        },
        "summary": _summary_message("standard", research_min + 1 + (0 if _fast_mode() else 5.5)),
        "models": {
            "research": model_for_tier("fast"),
            "strategy": model_for_tier("strategy"),
            "builder": model_for_tier("builder"),
        },
        "fast_mode": _fast_mode(),
    }


def estimate_after_strategy(state: AgentState) -> dict[str, Any]:
    """Refined estimate once product scope is known."""
    features = state.get("features") or []
    feature_count = len(features)
    pricing_tiers = len(state.get("price_points") or [])

    sid = state.get("session_id")
    try:
        analysis = chat_json(
            "You assess SaaS build complexity. Return JSON only.",
            f"""Assess this product build:

Product: {state.get('product_name')}
Features ({feature_count}): {features}
Pricing tiers: {pricing_tiers}
Niche: {state.get('niche')}
ICP: {state.get('icp')}

Return:
{{
  "complexity": "simple|standard|complex",
  "ui_scope": "landing|marketing_site|app_shell|full_product",
  "rationale": "one sentence"
}}

Prefer ui_scope "full_product" for CRM, dashboards, or any product users should log into and use.""",
            tier="fast",
            session_id=sid,
        )
        complexity = analysis.get("complexity", "standard")
        ui_scope = analysis.get("ui_scope", "landing")
        info(sid, "complexity", "assessed", complexity=complexity, ui_scope=ui_scope)
    except Exception as exc:
        complexity = "complex" if feature_count > 5 else "standard" if feature_count > 2 else "simple"
        ui_scope = "landing"
        analysis = {"rationale": "Heuristic estimate from feature count."}
        warning(sid, "complexity", f"LLM assess failed, using heuristic: {exc}", complexity=complexity)

    v0_minutes = {
        "simple": 2.5,
        "standard": 5.0,
        "complex": 8.0,
    }[complexity if complexity in {"simple", "standard", "complex"} else "standard"]

    ui_multiplier = {
        "landing": 1.0,
        "marketing_site": 1.4,
        "app_shell": 1.8,
        "full_product": 2.2,
    }.get(ui_scope, 2.0)
    v0_minutes = round(v0_minutes * ui_multiplier, 1)

    if _fast_mode():
        v0_minutes = 0

    deploy_minutes = 0.5
    total = round(0.5 + deploy_minutes + v0_minutes, 1)

    return {
        "complexity": complexity,
        "ui_scope": ui_scope,
        "total_minutes": total,
        "phases": {
            "approval": {"minutes": 0.5, "label": "Your review"},
            "deploy": {"minutes": deploy_minutes, "label": "Stripe + AWS (parallel)"},
            "v0": {
                "minutes": v0_minutes,
                "label": "v0 UI in background" if v0_minutes else "Turbo mode — no v0 wait",
            },
        },
        "summary": _summary_message(complexity, total, post_approval=True),
        "rationale": analysis.get("rationale", ""),
        "models": {
            "strategy": model_for_tier("strategy"),
            "builder": model_for_tier("builder"),
        },
        "fast_mode": _fast_mode(),
    }


def _summary_message(complexity: str, total_min: float, *, post_approval: bool = False) -> str:
    rounded = max(1, round(total_min))
    scope = "After you approve" if post_approval else "This forge"
    if _fast_mode():
        return f"{scope}: ~{rounded} min — turbo mode ships Stripe + AWS immediately."
    if post_approval:
        return (
            f"{scope}: ~{rounded} min total — Stripe + AWS in ~30s, "
            f"v0 UI continues in background ({complexity} build)."
        )
    return f"{scope} should take ~{rounded} min ({complexity} complexity)."
