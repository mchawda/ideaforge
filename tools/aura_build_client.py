from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote

import httpx

from orchestrator.stage_log import info, warning

# Public anon key shipped with aura.build web app (read-only public templates).
DEFAULT_SUPABASE_URL = "https://hoirqrkdgbmvpwutwuwj.supabase.co"
DEFAULT_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhvaXJxcmtkZ2JtdnB3dXR3dXdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2Nzc2NTAsImV4cCI6MjA1OTI1MzY1MH0."
    "_UsCSHsTELn7m54tOhX3ySm67WEhcyHAPbuxEQZsl3c"
)

AURA_SHARE_BASE = "https://www.aura.build/share"


class AuraBuildError(Exception):
    pass


def _supabase_url() -> str:
    return os.getenv("AURA_SUPABASE_URL", DEFAULT_SUPABASE_URL).rstrip("/")


def _supabase_anon_key() -> str:
    return os.getenv("AURA_SUPABASE_ANON_KEY", DEFAULT_SUPABASE_ANON_KEY).strip()


def _headers() -> dict[str, str]:
    key = _supabase_anon_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def aura_share_url(slug: str) -> str:
    return f"{AURA_SHARE_BASE}/{slug}"


def search_templates_by_title(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Search public Aura.build shared_code templates by title."""
    pattern = f"*{query.strip()}*"
    url = (
        f"{_supabase_url()}/rest/v1/shared_code"
        f"?select=slug,title,id&title=ilike.{quote(pattern)}&limit={limit}"
    )
    response = httpx.get(url, headers=_headers(), timeout=30)
    if response.status_code >= 400:
        raise AuraBuildError(f"Aura template search failed: HTTP {response.status_code}")
    return response.json()


def fetch_shared_code(slug: str, *, session_id: str | None = None) -> dict[str, Any]:
    """Fetch public HTML from aura.build via Supabase RPC."""
    response = httpx.post(
        f"{_supabase_url()}/rest/v1/rpc/get_public_shared_code_by_slug",
        headers=_headers(),
        json={"p_slug": slug},
        timeout=60,
    )
    if response.status_code >= 400:
        raise AuraBuildError(f"Aura fetch failed for {slug}: HTTP {response.status_code}")

    payload = response.json()
    row: dict[str, Any] | None = None
    if isinstance(payload, list) and payload:
        row = payload[0]
    elif isinstance(payload, dict) and payload.get("code"):
        row = payload

    if not row or not row.get("code"):
        raise AuraBuildError(f"Aura template not found or private: {slug}")

    info(
        session_id,
        "aura_build",
        "fetched template",
        slug=slug,
        title=row.get("title"),
        bytes=len(row.get("code", "")),
    )
    return row


def resolve_template_slug(template: dict[str, Any], *, session_id: str | None = None) -> str:
    slug = str(template.get("aura_slug") or "").strip()
    if slug:
        return slug

    name = str(template.get("name") or template.get("id") or "").strip()
    if not name:
        raise AuraBuildError("Aura template missing name and aura_slug")

    matches = search_templates_by_title(name, limit=3)
    if matches:
        resolved = str(matches[0]["slug"])
        warning(session_id, "aura_build", "resolved slug by title search", name=name, slug=resolved)
        return resolved

    raise AuraBuildError(f"No aura.build slug for template: {name}")


def fetch_template_html(
    template: dict[str, Any],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Load production HTML from aura.build for a portfolio template."""
    slug = resolve_template_slug(template, session_id=session_id)
    row = fetch_shared_code(slug, session_id=session_id)
    return {
        "slug": slug,
        "title": row.get("title") or template.get("name"),
        "html": str(row.get("code") or ""),
        "share_url": aura_share_url(slug),
        "source": "aura.build",
    }


def _strip_preview_controller(html: str) -> str:
    return re.sub(
        r"<script id=\"aura-preview-performance-controller\">[\s\S]*?</script>",
        "",
        html,
        count=1,
    )


def prepare_reference_excerpt(html: str, *, max_chars: int = 14_000) -> str:
    """Head + opening body for @-reference prompting (Aura workflow)."""
    cleaned = _strip_preview_controller(html)
    if len(cleaned) <= max_chars:
        return cleaned

    note = "\n<!-- excerpt truncated — preserve Aura layout/motion from reference -->"
    head_match = re.search(r"<head[\s\S]*?</head>", cleaned, re.IGNORECASE)
    body_open = re.search(r"<body[^>]*>", cleaned, re.IGNORECASE)
    # Keep the document opening (doctype/<html>) through </head> so the
    # reference excerpt stays valid markup the model can anchor on.
    head = cleaned[: head_match.end()] if head_match else ""
    start = body_open.start() if body_open else len(head)
    budget = max_chars - len(head) - len(note) - 1
    body_chunk = cleaned[start : start + max(0, budget)]
    return f"{head}\n{body_chunk}{note}"
