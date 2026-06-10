from __future__ import annotations

from orchestrator.progress import report_progress
from orchestrator.stage_log import info, stage
from orchestrator.state import AgentState, append_audit
from tools.stripe_tools import create_product_with_prices


def run_monetization(state: AgentState) -> AgentState:
    sid = state["session_id"]
    with stage(sid, "monetization"):
        report_progress(sid, "Creating Stripe products and payment links…")
        result = create_product_with_prices(
            product_name=state.get("product_name", "IdeaForge Product"),
            description=state.get("strategy_rationale", "Autonomous SaaS product"),
            price_points=state.get("price_points") or [{"name": "Pro", "price": 29}],
            session_id=sid,
        )

        info(
            sid,
            "monetization",
            "Stripe product created",
            product_id=result["stripe_product_id"],
            tiers=len(result["stripe_prices"]),
        )

        updated = {
            **state,
            "status": "monetized",
            "stripe_product_id": result["stripe_product_id"],
            "stripe_price_ids": [p["price_id"] for p in result["stripe_prices"]],
            "stripe_free_payment_link": result["stripe_free_payment_link"],
            "stripe_payment_link": result["stripe_payment_link"],
            "stripe_checkout_url": result["stripe_checkout_url"],
            "final_url": (
                state.get("vercel_deployment_url")
                or state.get("stripe_free_payment_link")
                or state.get("stripe_payment_link")
                or state.get("final_url", "")
            ),
        }
        return append_audit(
            updated,
            agent="monetization",
            decision="Created Stripe product with free + paid checkout links",
            rationale=(
                f"Product {result['stripe_product_id']}: "
                f"$0 link for Start free, paid link for Pro tiers "
                f"({len(result['stripe_prices'])} prices)"
            ),
            sources=["stripe.com"],
        )
