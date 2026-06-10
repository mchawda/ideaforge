#!/usr/bin/env python3
"""Verify .env credentials without printing secret values."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

REQUIRED = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AI_GATEWAY_API_KEY",
    "EXA_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "ANTHROPIC_API_KEY",
]

RECOMMENDED = [
    "V0_API_KEY",
    "VERCEL_TOKEN",
]

OPTIONAL = [
    "VERCEL_TOKEN",
    "VERCEL_TEAM_ID",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "DIFY_API_KEY",
    "LANGSMITH_API_KEY",
    "CDK_DEFAULT_ACCOUNT",
]


def status(name: str, ok: bool, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    suffix = f" — {detail}" if detail else ""
    print(f"  {mark} {name}{suffix}")


def main() -> int:
    print("Checking .env variables...\n")

    missing = []
    for key in REQUIRED:
        value = os.getenv(key, "").strip()
        ok = bool(value)
        if not ok:
            missing.append(key)
        status(key, ok, "set" if ok else "MISSING")

    print("\nRecommended:")
    for key in RECOMMENDED:
        value = os.getenv(key, "").strip()
        status(key, bool(value), "set" if value else "not set")

    print("\nOptional:")
    for key in OPTIONAL:
        value = os.getenv(key, "").strip()
        status(key, bool(value), "set" if value else "not set")

    print("\nLive API checks...\n")
    failures = 0

    # AWS STS
    try:
        import boto3

        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        sts = boto3.client(
            "sts",
            region_name=region,
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
        )
        identity = sts.get_caller_identity()
        status("AWS STS", True, f"account {identity['Account']}")
    except Exception as exc:
        failures += 1
        status("AWS STS", False, str(exc)[:80])

    # Anthropic
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=5,
            messages=[{"role": "user", "content": "ping"}],
        )
        status("Anthropic", True, "API reachable")
    except Exception as exc:
        failures += 1
        status("Anthropic", False, str(exc)[:80])

    # Stripe
    try:
        import stripe

        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        stripe.Account.retrieve()
        status("Stripe", True, "test mode OK")
    except Exception as exc:
        failures += 1
        status("Stripe", False, str(exc)[:80])

    # Exa
    try:
        from exa_py import Exa

        exa = Exa(api_key=os.environ["EXA_API_KEY"])
        exa.search("test", num_results=1)
        status("Exa", True, "search OK")
    except Exception as exc:
        failures += 1
        status("Exa", False, str(exc)[:80])

    # Vercel AI Gateway (Top 5 requirement)
    gateway_key = os.getenv("AI_GATEWAY_API_KEY", "").strip()
    if gateway_key:
        try:
            import httpx

            resp = httpx.get(
                "https://ai-gateway.vercel.sh/v1/models",
                headers={"Authorization": f"Bearer {gateway_key}"},
                timeout=20,
            )
            ok = resp.status_code == 200
            detail = f"HTTP {resp.status_code}"
            if not ok and resp.status_code == 403:
                detail += " (billing/card may be required for completions)"
            status("AI Gateway", ok, detail)
            if not ok:
                failures += 1
        except Exception as exc:
            failures += 1
            status("AI Gateway", False, str(exc)[:80])
    else:
        status("AI Gateway", False, "AI_GATEWAY_API_KEY not set")

    # Vercel deploy token
    token = os.getenv("VERCEL_TOKEN", "").strip()
    if token:
        try:
            import httpx

            resp = httpx.get(
                "https://api.vercel.com/v2/user",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            status("Vercel deploy", resp.status_code == 200, f"HTTP {resp.status_code}")
            if resp.status_code != 200:
                failures += 1
        except Exception as exc:
            failures += 1
            status("Vercel deploy", False, str(exc)[:80])
    else:
        status("Vercel deploy", False, "VERCEL_TOKEN not set")

    # v0 platform API (separate key from VERCEL_TOKEN)
    v0_key = os.getenv("V0_API_KEY", "").strip()
    if v0_key:
        try:
            import httpx

            params = {}
            team_id = os.getenv("VERCEL_TEAM_ID", "").strip()
            if team_id:
                params["teamId"] = team_id
            resp = httpx.get(
                "https://api.v0.dev/v1/chats",
                headers={"Authorization": f"Bearer {v0_key}"},
                params=params,
                timeout=15,
            )
            ok = resp.status_code == 200
            status("v0 platform", ok, f"HTTP {resp.status_code}")
            if not ok:
                failures += 1
        except Exception as exc:
            failures += 1
            status("v0 platform", False, str(exc)[:80])
    else:
        status("v0 platform", False, "V0_API_KEY not set")

    print()
    if missing:
        print(f"Missing required vars: {', '.join(missing)}")
        return 1
    if failures:
        print(f"{failures} live check(s) failed — review above.")
        return 1

    print("All required keys present and live checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
