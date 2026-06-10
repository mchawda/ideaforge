from __future__ import annotations

import os
import re

from orchestrator.progress import report_progress
from orchestrator.stage_log import error, info, stage
from orchestrator.state import AgentState, append_audit
from tools.aws_backend import deploy_app_backend
from tools.aws_tools import _skip_infra_enabled, refresh_hint, validate_credentials


def _safe_name(product_name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]", "-", product_name.lower()).strip("-")
    return slug[:24] or "ideaforge-app"


def run_infra(state: AgentState) -> AgentState:
    sid = state["session_id"]
    with stage(sid, "infra"):
        report_progress(sid, "Provisioning AWS Lambda, DynamoDB, and API Gateway…")
        product_name = state.get("product_name", "ideaforge-app")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-west-2")

        if _skip_infra_enabled():
            info(sid, "infra", "AWS_SKIP_INFRA set — skipping")
            return append_audit(
                {
                    **state,
                    "status": "infra_ready",
                    "aws_status": "skipped",
                    "aws_skip_reason": "AWS_SKIP_INFRA enabled in .env",
                },
                agent="infra",
                decision=f"Skipped AWS for {product_name} (AWS_SKIP_INFRA)",
                rationale="Infra disabled via environment variable.",
                sources=[],
            )

        creds = validate_credentials(sid)
        if not creds.get("ok"):
            reason = refresh_hint(creds.get("error", "AWS unavailable"))
            info(sid, "infra", "AWS unavailable — continuing without infra", reason=reason[:200])
            return append_audit(
                {
                    **state,
                    "status": "infra_ready",
                    "aws_status": "skipped",
                    "aws_skip_reason": reason[:500],
                },
                agent="infra",
                decision=f"Skipped AWS provisioning for {product_name}",
                rationale=reason[:300],
                sources=[],
            )

        account = creds["account"]

        try:
            backend = deploy_app_backend(product_name, session_id=sid)
        except Exception as exc:
            error(sid, "infra", f"AWS backend deploy failed — continuing without it: {exc}", exc_info=True)
            return append_audit(
                {
                    **state,
                    "status": "infra_ready",
                    "aws_status": "skipped",
                    "aws_skip_reason": f"AWS backend deploy failed: {exc}"[:500],
                },
                agent="infra",
                decision=f"AWS backend deploy failed for {product_name}",
                rationale=str(exc)[:300],
                sources=[f"aws://{account}/{region}"],
            )

        info(
            sid,
            "infra",
            "AWS backend live",
            account=account,
            region=backend["region"],
            api=backend["api_url"],
            table=backend["table_name"],
        )

        updated = {
            **state,
            "status": "infra_ready",
            "aws_status": "ready",
            "aws_stack_name": backend["function_name"],
            "aws_api_url": backend["api_url"],
            "aws_table_name": backend["table_name"],
        }
        return append_audit(
            updated,
            agent="infra",
            decision=f"Deployed live AWS backend for {product_name}",
            rationale=(
                f"AWS account {account}: DynamoDB table {backend['table_name']} + "
                f"Lambda {backend['function_name']} + public API Gateway at {backend['api_url']}. "
                f"Provides /signup, /login, /items auth + data API."
            ),
            sources=[f"aws://{account}/{backend['region']}", backend["api_url"]],
        )
