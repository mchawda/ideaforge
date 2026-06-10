from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx

from orchestrator.stage_log import info, warning

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "apps" / "web"


def _vercel_token() -> str:
    token = os.getenv("VERCEL_TOKEN", "").strip()
    if token:
        return token
    # Hackathon fallback: AI Gateway keys are Vercel account tokens (vck_*)
    return os.getenv("AI_GATEWAY_API_KEY", "").strip()


def _team_params() -> dict[str, str]:
    team_id = os.getenv("VERCEL_TEAM_ID", "").strip()
    return {"teamId": team_id} if team_id else {}


def resolve_v0_production_url(deployment: dict[str, Any]) -> str:
    """Map v0 deploy response to the stable *.vercel.app production alias."""
    import re

    inspector = deployment.get("inspectorUrl") or ""
    match = re.search(r"vercel\.com/[^/]+/([^/]+)/", inspector)
    if match:
        return f"https://{match.group(1)}.vercel.app"

    web_url = (deployment.get("webUrl") or "").strip()
    if web_url and "-ideaforge-projects.vercel.app" not in web_url:
        return web_url

    # Team deployment URLs embed a hash; production alias is usually hash-free.
    match = re.search(r"https://([a-z0-9-]+)-[a-z0-9]+-ideaforge-projects\.vercel\.app", web_url)
    if match:
        return f"https://{match.group(1)}-ideaforge-projects.vercel.app"

    return web_url


def ensure_project_public(
    project_name: str,
    *,
    session_id: str | None = None,
) -> bool:
    """Disable Vercel Authentication so product URLs are publicly reachable."""
    token = _vercel_token()
    if not token or not project_name:
        return False

    response = httpx.patch(
        f"https://api.vercel.com/v9/projects/{project_name}",
        headers={"Authorization": f"Bearer {token}"},
        params=_team_params(),
        # Clear every protection gate so product URLs never show a Vercel login wall.
        json={"ssoProtection": None, "passwordProtection": None},
        timeout=30,
    )
    if response.status_code >= 400:
        warning(
            session_id,
            "vercel",
            "could not disable deployment protection",
            project=project_name,
            status=response.status_code,
            body=response.text[:200],
        )
        return False

    info(session_id, "vercel", "deployment protection disabled", project=project_name)
    return True


def verify_public_url(url: str) -> bool:
    if not url:
        return False
    try:
        response = httpx.get(url, timeout=20, follow_redirects=True)
        return response.status_code < 400
    except httpx.HTTPError:
        return False


def wait_for_deployment_ready(
    deployment_url_or_id: str,
    *,
    session_id: str | None = None,
    timeout: int = 240,
    interval: int = 5,
) -> str:
    """Poll a Vercel deployment until its build finishes.

    v0/Vercel return a URL the moment a deployment is queued, but the build
    completes (or fails) asynchronously seconds-to-minutes later. A failed build
    serves a 'Deployment has failed' page with HTTP 200, so a one-shot URL fetch
    can't tell success from failure. This polls the deployment's `readyState`
    until it reaches a terminal state and returns it (READY/ERROR/CANCELED).
    """
    import time

    token = _vercel_token()
    if not token or not deployment_url_or_id:
        return "UNKNOWN"

    ident = (
        deployment_url_or_id.replace("https://", "")
        .replace("http://", "")
        .strip("/")
    )
    deadline = time.time() + timeout
    last = "UNKNOWN"
    while time.time() < deadline:
        try:
            response = httpx.get(
                f"https://api.vercel.com/v13/deployments/{ident}",
                headers={"Authorization": f"Bearer {token}"},
                params=_team_params(),
                timeout=30,
            )
        except httpx.HTTPError:
            time.sleep(interval)
            continue
        if response.status_code >= 400:
            return last
        body = response.json()
        last = str(body.get("readyState") or body.get("status") or "UNKNOWN").upper()
        if last in {"READY", "ERROR", "CANCELED"}:
            break
        time.sleep(interval)

    info(session_id, "vercel", "deployment build state", state=last, target=ident[:60])
    return last


def get_deployment_status(project_name: str) -> dict[str, Any]:
    token = _vercel_token()
    if not token:
        return {"status": "skipped", "reason": "VERCEL_TOKEN not configured"}

    response = httpx.get(
        f"https://api.vercel.com/v9/projects/{project_name}",
        headers={"Authorization": f"Bearer {token}"},
        params=_team_params(),
        timeout=30,
    )
    if response.status_code == 404:
        return {"status": "not_found"}
    response.raise_for_status()
    return response.json()


def project_name_taken(project_name: str) -> bool:
    """True if a Vercel project with this name already exists on the team."""
    status = get_deployment_status(project_name)
    return status.get("status") not in ("not_found", "skipped")


def _session_hash(session_id: str, *, length: int = 12) -> str:
    clean = re.sub(r"[^a-z0-9]", "", session_id.lower())
    if len(clean) >= length:
        return clean[:length]
    digest = hashlib.sha256(session_id.encode()).hexdigest()
    return digest[:length]


def allocate_project_name(
    session_id: str,
    *,
    product_name: str = "",
    preferred: str | None = None,
) -> str:
    """Pick a unique Vercel project name.

    Product URLs are ephemeral deploy targets — they use a session hash, not the
    marketing product name. If a name is already taken, append -2, -3, …
    """
    sid = session_id
    sid8 = _session_hash(sid, length=8)
    sid12 = _session_hash(sid, length=12)

    candidates: list[str] = []
    # Hash-first: stable per session, no product-title coupling
    candidates.append(f"if-{sid12}")
    candidates.append(f"if-{sid8}")
    if product_name:
        slug = re.sub(r"[^a-z0-9]+", "-", product_name.lower()).strip("-")[:20] or "app"
        candidates.append(f"if-{slug}-{sid8}")
    if preferred:
        candidates.append(preferred.strip().lower())

    seen: set[str] = set()
    for base in candidates:
        if not base or base in seen:
            continue
        seen.add(base)
        if not project_name_taken(base):
            return base
        for suffix in range(2, 25):
            numbered = f"{base}-{suffix}"
            if not project_name_taken(numbered):
                return numbered

    fallback = f"if-{_session_hash(session_id, length=16)}"
    if not project_name_taken(fallback):
        return fallback
    return f"{fallback}-{_session_hash(session_id + product_name, length=6)}"


def deploy_control_panel(
    *,
    api_url: str | None = None,
    production: bool = True,
) -> dict[str, Any]:
    """Deploy IdeaForge Next.js control panel to Vercel."""
    token = _vercel_token()
    if not token:
        raise RuntimeError(
            "VERCEL_TOKEN not set — create one at https://vercel.com/account/tokens"
        )

    public_api = (api_url or os.getenv("ORCHESTRATOR_PUBLIC_URL", "")).strip()
    if not public_api:
        raise RuntimeError(
            "Set ORCHESTRATOR_PUBLIC_URL to your public FastAPI URL before deploying the web app"
        )

    env = {
        **os.environ,
        "VERCEL_TOKEN": token,
        "NEXT_PUBLIC_API_URL": public_api,
        "NEXT_PUBLIC_APP_URL": os.getenv("NEXT_PUBLIC_APP_URL", "https://idea-forge-eta-six.vercel.app"),
    }

    cmd = [
        "bunx",
        "vercel",
        "deploy",
        "--yes",
        "--cwd",
        str(WEB_DIR),
    ]
    if production:
        cmd.append("--prod")
    scope = os.getenv("VERCEL_SCOPE", "").strip()
    if scope:
        cmd.extend(["--scope", scope])

    info(None, "vercel", "deploying control panel", api_url=public_api, prod=production)
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        warning(None, "vercel", "deploy failed", stderr=result.stderr[:500])
        raise RuntimeError(f"Vercel deploy failed: {result.stderr[-400:]}")

    output = (result.stdout or "") + (result.stderr or "")
    url = _extract_url(output) or "https://idea-forge-eta-six.vercel.app"
    info(None, "vercel", "control panel deployed", url=url)
    return {"url": url, "api_url": public_api}


def _extract_url(output: str) -> str:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("https://") and "vercel.app" in stripped:
            return stripped
    return ""
