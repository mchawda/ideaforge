from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from typing import Any

import httpx

from orchestrator.stage_log import error, info, warning
from tools.vercel_tools import (
    ensure_project_public,
    resolve_v0_production_url,
    verify_public_url,
    wait_for_deployment_ready,
)


class V0BuildError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['V0_API_KEY']}",
        "Content-Type": "application/json",
    }


def _params() -> dict[str, str]:
    team_id = os.getenv("VERCEL_TEAM_ID", "").strip()
    return {"teamId": team_id} if team_id else {}


def _product_slug_tokens(product_name: str) -> list[str]:
    slug = re.sub(r"[^a-z0-9]+", "-", product_name.lower()).strip("-")
    return [t for t in slug.split("-") if len(t) >= 4]


def _chat_matches_product(chat: dict[str, Any], product_name: str) -> bool:
    tokens = _product_slug_tokens(product_name)
    if not tokens:
        return False
    haystack = " ".join(
        str(chat.get(key) or "") for key in ("name", "title", "description")
    ).lower()
    return any(token in haystack for token in tokens)


def deploy_url_matches_product(url: str, product_name: str) -> bool:
    """Reject v0 deploy URLs that clearly belong to a different product."""
    if not url or not product_name:
        return True
    host = url.lower().split("//", 1)[-1].split("/")[0]
    tokens = _product_slug_tokens(product_name)
    if not tokens:
        return True
    return any(token in host for token in tokens)


def _version_completed(latest: dict[str, Any], data: dict[str, Any]) -> bool:
    """True only when v0 has finished generating the app.

    v0 exposes a `demoUrl` preview the instant a chat is created — while the
    version is still `status: pending` with zero real files. Deploying that
    pending shell ships a near-empty Next.js app (only /404), which then fails
    the Vercel build (missing routes-manifest.json). The version `status` is the
    one reliable signal: it flips `pending` -> `completed` when generation is done.
    File counts are NOT reliable here — v0's API returns 0 files for completed
    chats too — so we gate strictly on status.
    """
    status = str(latest.get("status") or data.get("status") or "").lower()
    # If v0 ever omits status, fall back to permissive behaviour (don't block).
    if not status:
        return True
    return status in {"completed", "complete", "ready", "succeeded"}


def _extract_result(data: dict[str, Any]) -> dict[str, Any]:
    latest = data.get("latestVersion") or {}
    if not _version_completed(latest, data):
        return {}
    files = latest.get("files") or data.get("files") or []
    demo_url = latest.get("demoUrl") or data.get("demo") or ""
    if demo_url or files:
        return {
            "chat_id": data.get("id"),
            "version_id": latest.get("id", ""),
            "demo_url": demo_url,
            "files": files,
        }
    return {}


def _project_name_from_deployment(deployment: dict[str, Any]) -> str:
    inspector = deployment.get("inspectorUrl") or ""
    match = re.search(r"vercel\.com/[^/]+/([^/]+)/", inspector)
    return match.group(1) if match else ""


def fetch_chat(chat_id: str, *, session_id: str | None = None) -> dict[str, Any]:
    with httpx.Client(timeout=httpx.Timeout(30.0, read=120.0)) as client:
        response = client.get(
            f"https://api.v0.dev/v1/chats/{chat_id}",
            headers=_headers(),
            params=_params(),
        )
        if response.status_code >= 400:
            warning(
                session_id,
                "v0",
                "fetch chat failed",
                chat_id=chat_id,
                status=response.status_code,
                body=response.text[:200],
            )
        response.raise_for_status()
        return response.json()


def deploy_v0_production(
    chat_id: str,
    version_id: str,
    *,
    session_id: str | None = None,
    max_attempts: int = 4,
) -> dict[str, Any]:
    """Publish v0 chat to a permanent *.vercel.app URL via v0 Platform API."""
    if not chat_id or not version_id:
        raise V0BuildError("Cannot deploy — missing chat_id or version_id")

    info(session_id, "v0", "deploying to production", chat_id=chat_id, version_id=version_id)
    last_error = "unknown error"
    data: dict[str, Any] = {}

    with httpx.Client(timeout=httpx.Timeout(30.0, read=300.0)) as client:
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                delay = min(8, 2 ** attempt)
                info(session_id, "v0", "retrying production deploy", attempt=attempt, delay_s=delay)
                time.sleep(delay)
                # v0 may publish a new version while we wait — use the latest one.
                chat = fetch_chat(chat_id, session_id=session_id)
                latest = chat.get("latestVersion") or {}
                version_id = latest.get("id") or version_id

            response = client.post(
                "https://api.v0.dev/v1/deployments",
                headers=_headers(),
                params=_params(),
                json={"chatId": chat_id, "versionId": version_id},
            )
            if response.status_code >= 400:
                last_error = response.text[:300]
                warning(
                    session_id,
                    "v0",
                    "deploy HTTP error",
                    attempt=attempt,
                    status=response.status_code,
                    body=last_error,
                )
                if response.status_code >= 500 and attempt < max_attempts:
                    continue
                response.raise_for_status()

            data = response.json()
            web_url = data.get("webUrl") or ""
            if web_url:
                break
            last_error = "v0 deploy succeeded but no webUrl returned"
            warning(session_id, "v0", last_error, attempt=attempt)

    if not data.get("webUrl"):
        raise V0BuildError(last_error)

    # Verify the Vercel build actually succeeds. v0 reports the deploy as soon as
    # it is queued; the build can still fail asynchronously and serve a
    # 'Deployment has failed' page (HTTP 200). Never treat an ERROR build as live.
    deployment_url = data.get("webUrl") or ""
    build_state = wait_for_deployment_ready(deployment_url, session_id=session_id)
    if build_state == "ERROR":
        raise V0BuildError(
            f"v0 Vercel build failed (readyState=ERROR) for {deployment_url}"
        )

    stable_url = resolve_v0_production_url(data)
    project_name = _project_name_from_deployment(data)
    if project_name:
        ensure_project_public(project_name, session_id=session_id)
        if not verify_public_url(stable_url) and data.get("webUrl"):
            ensure_project_public(project_name, session_id=session_id)
            time.sleep(2)
            if verify_public_url(stable_url):
                info(session_id, "v0", "stable production URL verified", url=stable_url)
            else:
                warning(
                    session_id,
                    "v0",
                    "stable URL not yet public — using deployment URL",
                    stable=stable_url,
                    deployment=data.get("webUrl", "")[:80],
                )
                stable_url = data.get("webUrl") or stable_url

    info(session_id, "v0", "production deploy ok", url=stable_url)
    return {
        "deployment_id": data.get("id"),
        "web_url": stable_url,
        "deployment_url": data.get("webUrl") or stable_url,
        "inspector_url": data.get("inspectorUrl", ""),
        "project_name": project_name,
    }


def redeploy_v0_chat(
    chat_id: str,
    *,
    session_id: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Redeploy an existing v0 chat to a fresh permanent Vercel URL."""
    chat = fetch_chat(chat_id, session_id=session_id)
    latest = chat.get("latestVersion") or {}
    version_id = latest.get("id")
    if not version_id:
        raise V0BuildError(f"v0 chat {chat_id} has no deployable version")

    if on_progress:
        on_progress("Publishing v0 UI to permanent Vercel URL…")
    deployed = deploy_v0_production(chat_id, version_id, session_id=session_id)
    return {
        "chat_id": chat_id,
        "version_id": version_id,
        "demo_url": latest.get("demoUrl") or "",
        "production_url": deployed["web_url"],
        "deployment_id": deployed["deployment_id"],
        "files": latest.get("files") or [],
    }


def create_v0_chat(
    prompt: str,
    *,
    poll_timeout: int = 480,
    session_id: str | None = None,
    on_progress: Callable[[str], None] | None = None,
    name_hint: str = "",
) -> dict[str, Any]:
    """Create a v0 chat and poll until the preview is ready."""

    def pulse(message: str) -> None:
        if on_progress:
            on_progress(message)

    create_timeout = httpx.Timeout(30.0, read=180.0)
    started = time.time()
    info(session_id, "v0", "create chat", prompt_len=len(prompt))

    with httpx.Client(timeout=create_timeout) as client:
        pulse("Connecting to v0 and sending your full product prompt (marketing + auth + app)…")
        data: dict[str, Any] = {}
        chat_id = ""
        try:
            response = client.post(
                "https://api.v0.dev/v1/chats",
                headers=_headers(),
                params=_params(),
                json={"message": prompt},
            )
            if response.status_code >= 400:
                warning(
                    session_id,
                    "v0",
                    "create HTTP error",
                    status=response.status_code,
                    body=response.text[:300],
                )
            response.raise_for_status()
            data = response.json()
            chat_id = data.get("id", "")
        except httpx.ReadTimeout:
            warning(session_id, "v0", "create read timeout — checking existing chats")
            pulse("v0 is still generating — checking for an existing preview…")
            recovered = _find_ready_chat(
                client, session_id=session_id, name_hint=name_hint
            )
            if recovered:
                info(
                    session_id,
                    "v0",
                    "recovered matching chat",
                    chat_id=recovered["chat_id"],
                    name_hint=name_hint[:40],
                )
                pulse("Found matching v0 preview — using that.")
                return _maybe_deploy(recovered, session_id=session_id, on_progress=on_progress)
            # The create call usually DID land server-side even when the response
            # times out — v0 just acknowledges slowly on busy days. Adopt the
            # in-flight chat and wait for it instead of raising (which would burn
            # a duplicate generation on retry).
            chat_id = _find_matching_chat_id(
                client, session_id=session_id, name_hint=name_hint
            )
            if not chat_id:
                raise V0BuildError(
                    "v0 is taking longer than usual. Stripe and AWS will still deploy — retry for UI."
                )
            info(
                session_id,
                "v0",
                "adopted in-flight chat after create timeout",
                chat_id=chat_id,
                name_hint=name_hint[:40],
            )
            pulse("v0 acknowledged slowly — waiting on the in-flight generation (no duplicate spend)…")
        except httpx.HTTPError as exc:
            # v0's create endpoint can return a hard 5xx while STILL creating the
            # chat server-side (observed repeatedly: 500 response, chat exists).
            # Adopt the in-flight chat instead of raising — a blind retry would
            # pay for a duplicate generation.
            status_code = getattr(getattr(exc, "response", None), "status_code", 0) or 0
            if status_code >= 500:
                warning(session_id, "v0", f"create returned {status_code} — checking for in-flight chat")
                pulse("v0 errored on create — checking if the generation actually started…")
                time.sleep(5)
                chat_id = _find_matching_chat_id(
                    client, session_id=session_id, name_hint=name_hint
                )
                if chat_id:
                    info(
                        session_id,
                        "v0",
                        "adopted in-flight chat after create 5xx",
                        chat_id=chat_id,
                        name_hint=name_hint[:40],
                    )
                    pulse("Generation is running on v0 — waiting for it (no duplicate spend)…")
            if not chat_id:
                error(session_id, "v0", f"create failed: {exc}", exc_info=True)
                raise V0BuildError(f"v0 create failed: {exc}") from exc

        if not chat_id:
            error(session_id, "v0", "no chat id in response")
            raise V0BuildError("v0 did not return a chat id")

        info(session_id, "v0", "chat created", chat_id=chat_id)
        pulse("v0 received your prompt — generating UI components…")

        ready = _extract_result(data)
        if ready:
            info(session_id, "v0", "preview ready immediately", elapsed_s=int(time.time() - started))
            pulse("v0 preview is ready.")
            return _maybe_deploy(ready, session_id=session_id, on_progress=on_progress)

        poll_timeout_cfg = httpx.Timeout(20.0, read=60.0)
        deadline = time.time() + poll_timeout
        poll_count = 0
        while time.time() < deadline:
            elapsed = int(time.time() - started)
            poll_count += 1
            if poll_count == 1 or poll_count % 5 == 0:
                info(session_id, "v0", "polling", elapsed_s=elapsed, poll=poll_count)
            pulse(
                f"Still generating UI with v0… {elapsed}s elapsed "
                f"(this can take 3–8 minutes — your agents are working)"
            )
            time.sleep(3)
            try:
                poll = client.get(
                    f"https://api.v0.dev/v1/chats/{chat_id}",
                    headers=_headers(),
                    params=_params(),
                    timeout=poll_timeout_cfg,
                )
                poll.raise_for_status()
                ready = _extract_result(poll.json())
                if ready:
                    info(session_id, "v0", "preview ready", elapsed_s=elapsed, polls=poll_count)
                    pulse(f"v0 preview ready after {elapsed}s.")
                    return _maybe_deploy(ready, session_id=session_id, on_progress=on_progress)
            except httpx.HTTPError as exc:
                warning(session_id, "v0", f"poll error #{poll_count}: {exc}")
                pulse(f"Waiting on v0 response… check #{poll_count}")
                continue

    error(session_id, "v0", "poll timeout", chat_id=chat_id, timeout_s=poll_timeout)
    raise V0BuildError(
        f"v0 preview not ready after {poll_timeout}s — chat {chat_id} may still be generating"
    )


def _find_matching_chat_id(
    client: httpx.Client,
    *,
    session_id: str | None,
    name_hint: str = "",
) -> str:
    """Most recent chat matching the product, regardless of generation status.

    Used after a create-call timeout: the chat almost always exists server-side,
    so we adopt it and poll instead of creating (and paying for) a duplicate.
    """
    if not name_hint.strip():
        return ""
    try:
        response = client.get(
            "https://api.v0.dev/v1/chats",
            headers=_headers(),
            params=_params(),
            timeout=httpx.Timeout(20.0, read=60.0),
        )
        response.raise_for_status()
        for chat in response.json().get("data", [])[:12]:
            if _chat_matches_product(chat, name_hint):
                return chat.get("id") or ""
    except httpx.HTTPError as exc:
        warning(session_id, "v0", f"list chats for adoption failed: {exc}")
    return ""


def _find_ready_chat(
    client: httpx.Client,
    *,
    session_id: str | None,
    name_hint: str = "",
) -> dict[str, Any]:
    """Reuse a recent v0 chat that already has a preview (avoids duplicate creates on resume)."""
    poll_cfg = httpx.Timeout(20.0, read=60.0)
    try:
        response = client.get(
            "https://api.v0.dev/v1/chats",
            headers=_headers(),
            params=_params(),
            timeout=poll_cfg,
        )
        response.raise_for_status()
        if not name_hint.strip():
            warning(session_id, "v0", "chat recovery skipped — no product name hint")
            return {}

        chats = response.json().get("data", [])
        chats = sorted(
            chats,
            key=lambda c: _chat_matches_product(c, name_hint),
            reverse=True,
        )
        for chat in chats[:12]:
            if not _chat_matches_product(chat, name_hint):
                continue
            chat_id = chat.get("id")
            if not chat_id:
                continue
            detail = client.get(
                f"https://api.v0.dev/v1/chats/{chat_id}",
                headers=_headers(),
                params=_params(),
                timeout=poll_cfg,
            )
            detail.raise_for_status()
            ready = _extract_result(detail.json())
            if ready.get("demo_url"):
                return ready
        warning(session_id, "v0", "no matching v0 chat for recovery", name_hint=name_hint[:40])
    except httpx.HTTPError as exc:
        warning(session_id, "v0", f"list chats for recovery failed: {exc}")
    return {}


def _auto_deploy_enabled() -> bool:
    return os.getenv("V0_AUTO_DEPLOY", "true").strip().lower() in {"1", "true", "yes"}


def _maybe_deploy(
    result: dict[str, Any],
    *,
    session_id: str | None,
    on_progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    if not _auto_deploy_enabled():
        return result

    chat_id = result.get("chat_id", "")
    version_id = result.get("version_id", "")
    if not chat_id or not version_id:
        warning(session_id, "v0", "skipping production deploy — no version_id")
        return result

    # v0 sometimes 500s if we deploy the instant preview metadata appears.
    time.sleep(2)

    if on_progress:
        on_progress("Publishing v0 UI to permanent Vercel URL…")
    try:
        deployed = deploy_v0_production(chat_id, version_id, session_id=session_id)
        result["production_url"] = deployed["web_url"]
        result["demo_url"] = deployed["web_url"]
        result["deployment_id"] = deployed["deployment_id"]
        result["vercel_project_name"] = deployed.get("project_name", "")
        if on_progress:
            on_progress(f"Live on Vercel — {deployed['web_url']}")
    except Exception as exc:
        warning(session_id, "v0", f"production deploy failed, keeping preview URL: {exc}")
        if on_progress:
            on_progress(f"Preview ready (permanent deploy skipped: {str(exc)[:80]})")

    return result
