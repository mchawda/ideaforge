from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditEntry(TypedDict, total=False):
    agent: str
    decision: str
    rationale: str
    sources: list[str]
    timestamp: str


class AgentState(TypedDict, total=False):
    user_input: str
    input_mode: Literal["ideabrowser", "idea"]
    ideabrowser_url: str
    session_id: str
    status: str
    current_step: str
    started_at: str
    last_heartbeat: str
    completed_at: str
    progress_log: list[dict[str, str]]
    market_research: dict[str, Any]
    competitors: list[dict[str, Any]]
    pain_points: list[str]
    demand_signals: list[str]
    product_name: str
    niche: str
    icp: str
    features: list[str]
    pricing_model: str
    price_points: list[dict[str, Any]]
    strategy_rationale: str
    human_approved: bool
    human_feedback: str
    pending_approval: dict[str, Any]
    v0_prompt: str
    generated_ui_code: str
    vercel_project_id: str
    vercel_deployment_url: str
    aws_status: str
    aws_skip_reason: str
    aws_stack_name: str
    aws_api_url: str
    aws_table_name: str
    stripe_product_id: str
    stripe_price_ids: list[str]
    stripe_checkout_url: str
    stripe_payment_link: str
    stripe_free_payment_link: str
    audit_log: list[AuditEntry]
    final_brief: str
    final_url: str
    error: str
    retry_count: int
    complexity: str
    time_estimate: dict[str, Any]
    v0_status: str
    aura_template: dict[str, Any]
    ui_builder: str
    background_build: bool


def new_session_state(
    *,
    user_input: str,
    input_mode: Literal["ideabrowser", "idea"],
    ideabrowser_url: str | None = None,
) -> AgentState:
    return {
        "session_id": str(uuid4()),
        "user_input": user_input,
        "input_mode": input_mode,
        "ideabrowser_url": ideabrowser_url or "",
        "status": "queued",
        "current_step": "Queued",
        "started_at": utc_now(),
        "last_heartbeat": utc_now(),
        "progress_log": [],
        "audit_log": [],
        "retry_count": 0,
    }


def append_audit(
    state: AgentState,
    *,
    agent: str,
    decision: str,
    rationale: str,
    sources: list[str] | None = None,
) -> AgentState:
    log = list(state.get("audit_log") or [])
    log.append(
        {
            "agent": agent,
            "decision": decision,
            "rationale": rationale,
            "sources": sources or [],
            "timestamp": utc_now(),
        }
    )
    return {**state, "audit_log": log}
