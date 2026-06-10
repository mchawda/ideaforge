from __future__ import annotations

from orchestrator.stage_log import info, stage
from orchestrator.state import AgentState, append_audit


def run_audit(state: AgentState) -> AgentState:
    sid = state["session_id"]
    with stage(sid, "audit"):
        brief_lines = [
            f"# {state.get('product_name', 'Product')} — Decision Brief",
            "",
            f"**Niche:** {state.get('niche', '')}",
            f"**ICP:** {state.get('icp', '')}",
            "",
            "## Strategy",
            state.get("strategy_rationale", ""),
            "",
            "## Live assets",
            f"- Product URL: {state.get('final_url', 'pending')}",
            f"- AWS API: {state.get('aws_api_url', 'pending')}",
            f"- Stripe free checkout ($0): {state.get('stripe_free_payment_link', 'pending')}",
            f"- Stripe paid checkout: {state.get('stripe_payment_link', 'pending')}",
            "",
            "## Agent audit trail",
        ]
        for entry in state.get("audit_log") or []:
            brief_lines.append(
                f"- **{entry.get('agent')}**: {entry.get('decision')} — {entry.get('rationale')}"
            )

        brief = "\n".join(brief_lines)
        info(sid, "audit", "brief generated", lines=len(brief_lines))
        updated = {**state, "status": "complete", "final_brief": brief}
        return append_audit(
            updated,
            agent="audit",
            decision="Published final decision brief",
            rationale="All agent decisions compiled with sources.",
            sources=[],
        )
