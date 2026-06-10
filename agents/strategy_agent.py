from __future__ import annotations

from orchestrator.llm import chat_json
from orchestrator.progress import report_progress
from orchestrator.stage_log import info, stage
from orchestrator.state import AgentState, append_audit
from tools.aura_portfolio import select_aura_template


def run_strategy(state: AgentState) -> AgentState:
    sid = state["session_id"]
    with stage(sid, "strategy"):
        report_progress(sid, "Drafting product strategy with AI…")
        feedback = state.get("human_feedback", "")
        research = state.get("market_research") or {}
        slim_research = {
            "source": research.get("source"),
            "competitors": [
                {"title": c.get("title"), "url": c.get("url")}
                for c in (research.get("competitors") or [])[:4]
            ],
            "pain_points": (research.get("pain_points") or [])[:5],
            "demand_signals": (research.get("demand_signals") or [])[:5],
        }

        strategy = chat_json(
            "You are a startup strategy agent. Use research evidence and return JSON only.",
            f"""Create a product strategy from this research.

User input: {state.get('user_input')}
Research: {slim_research}
Feedback to incorporate: {feedback or 'none'}

Return:
{{
  "product_name": "...",
  "niche": "...",
  "icp": "...",
  "features": ["..."],
  "pricing_model": "freemium|flat|usage",
  "price_points": [{{"name": "Starter", "price": 0}}, {{"name": "Pro", "price": 29}}],
  "strategy_rationale": "..."
}}""",
            tier="strategy",
            session_id=sid,
        )

        pending = {
            "product_name": strategy["product_name"],
            "niche": strategy["niche"],
            "icp": strategy["icp"],
            "features": strategy["features"],
            "price_points": strategy["price_points"],
            "rationale": strategy["strategy_rationale"],
        }

        aura_template = select_aura_template(
            product_name=strategy["product_name"],
            niche=strategy["niche"],
            icp=strategy["icp"],
            features=strategy["features"],
            user_input=state.get("user_input", ""),
        )
        slug = aura_template.get("aura_slug") or aura_template.get("id")
        report_progress(sid, f"aura.build template: {aura_template['name']} ({slug})")

        updated = {
            **state,
            "status": "awaiting_approval",
            "product_name": strategy["product_name"],
            "niche": strategy["niche"],
            "icp": strategy["icp"],
            "features": strategy["features"],
            "pricing_model": strategy["pricing_model"],
            "price_points": strategy["price_points"],
            "strategy_rationale": strategy["strategy_rationale"],
            "aura_template": aura_template,
            "pending_approval": pending,
        }
        info(sid, "strategy", "product proposed", product=strategy["product_name"])
        result = append_audit(
            updated,
            agent="strategy",
            decision=f"Proposed product: {strategy['product_name']}",
            rationale=strategy["strategy_rationale"],
            sources=[state.get("ideabrowser_url", "")] if state.get("ideabrowser_url") else [],
        )
        report_progress(
            sid,
            f"Strategy ready — review and approve “{strategy['product_name']}” to continue",
        )
        return result
