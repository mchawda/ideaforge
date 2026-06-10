from __future__ import annotations

import os
from typing import Any

from exa_py import Exa

from orchestrator.stage_log import error, info


def _client() -> Exa:
    return Exa(api_key=os.environ["EXA_API_KEY"])


def exa_search(
    query: str,
    num_results: int = 4,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    info(session_id, "exa", "search", query=query[:80], num_results=num_results)
    try:
        results = _client().search_and_contents(
            query,
            num_results=num_results,
            text={"max_characters": 900},
        )
        items = [
            {
                "title": item.title,
                "url": item.url,
                "snippet": (item.text or "")[:900],
            }
            for item in results.results
        ]
        info(session_id, "exa", "search ok", returned=len(items))
        return items
    except Exception as exc:
        error(session_id, "exa", f"search failed: {exc}", query=query[:80], exc_info=True)
        raise


def exa_get_contents(url: str, session_id: str | None = None) -> str:
    info(session_id, "exa", "get_contents", url=url[:120])
    try:
        results = _client().get_contents([url], text={"max_characters": 3500})
        if not results.results:
            info(session_id, "exa", "get_contents empty")
            return ""
        text = (results.results[0].text or "")[:3500]
        info(session_id, "exa", "get_contents ok", chars=len(text))
        return text
    except Exception as exc:
        error(session_id, "exa", f"get_contents failed: {exc}", url=url[:120], exc_info=True)
        raise
