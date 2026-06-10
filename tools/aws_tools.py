from __future__ import annotations

import os
from typing import Any

import boto3

from orchestrator.stage_log import info, warning


def _skip_infra_enabled() -> bool:
    return os.getenv("AWS_SKIP_INFRA", "").strip().lower() in {"1", "true", "yes"}


def validate_credentials(session_id: str | None = None) -> dict[str, Any]:
    """Return {ok, account?, error?} — never raises."""
    if _skip_infra_enabled():
        return {"ok": False, "skipped": True, "error": "AWS_SKIP_INFRA is set"}

    key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    if not key or not secret:
        return {"ok": False, "error": "AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY missing in .env"}

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
    try:
        sts = boto3.client(
            "sts",
            region_name=region,
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        )
        identity = sts.get_caller_identity()
        info(session_id, "aws", "credentials valid", account=identity["Account"], region=region)
        return {"ok": True, "account": identity["Account"], "region": region}
    except Exception as exc:
        msg = str(exc)
        warning(session_id, "aws", "credentials invalid", error=msg[:200])
        return {"ok": False, "error": msg}


def refresh_hint(error: str) -> str:
    if "ExpiredToken" in error or "expired" in error.lower():
        return (
            "AWS session token expired. Re-login (e.g. aws sso login) and paste fresh "
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN into .env"
        )
    return error
