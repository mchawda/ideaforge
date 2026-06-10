from __future__ import annotations

from typing import Any

import httpx

from orchestrator.llm import chat_json
from orchestrator.stage_log import info, warning
from tools.exa_tools import exa_get_contents, exa_search


def import_idea_from_url(url: str, *, session_id: str | None = None) -> dict[str, Any]:
    info(session_id, "ideabrowser", "import started", url=url[:120])
    try:
        raw_text = exa_get_contents(url, session_id=session_id)
    except Exception as exc:
        warning(session_id, "ideabrowser", f"Exa fetch failed, trying HTTP: {exc}")
        response = httpx.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        raw_text = response.text[:6000]
        info(session_id, "ideabrowser", "HTTP fallback ok", chars=len(raw_text))

    if not raw_text.strip():
        raise ValueError("Could not fetch IdeaBrowser page. Paste idea text instead.")

    result = chat_json(
        "Extract structured startup idea data. Return JSON only.",
        f"""Extract from this IdeaBrowser page:

{raw_text}

Return:
{{
  "product_name": "...",
  "description": "...",
  "problem": "...",
  "why_now": "...",
  "market_size": "...",
  "market_gap": "...",
  "main_competitor": "...",
  "target_customer": "...",
  "execution_hints": ["..."],
  "category": "...",
  "source_url": "{url}"
}}""",
        tier="fast",
        session_id=session_id,
    )
    info(session_id, "ideabrowser", "extract ok", product=result.get("product_name"))
    return result


def search_ideabrowser(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    return exa_search(f"site:ideabrowser.com {query}", num_results=num_results)
