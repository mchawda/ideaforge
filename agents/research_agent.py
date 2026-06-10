from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from orchestrator.progress import report_progress
from orchestrator.stage_log import info, stage, warning
from orchestrator.state import AgentState, append_audit
from tools.exa_tools import exa_search
from tools.ideabrowser_tools import import_idea_from_url

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _idea_seed(state: AgentState) -> str:
    """Best-effort readable idea phrase for Exa research.

    Falls back to a slug derived from a URL path when the operator only gave a link.
    """
    raw = (state.get("user_input") or "").strip()
    if raw and not _URL_RE.match(raw):
        return raw
    candidate = raw or (state.get("ideabrowser_url") or "").strip()
    if _URL_RE.match(candidate):
        path = re.sub(r"^https?://[^/]+/?", "", candidate).strip("/")
        slug = path.split("/")[-1] if path else ""
        words = re.sub(r"[-_]+", " ", slug).strip()
        return words or "startup idea"
    return candidate or "startup idea"


def run_research(state: AgentState) -> AgentState:
    sid = state["session_id"]
    with stage(sid, "research", input_mode=state.get("input_mode")):
        url = (state.get("ideabrowser_url") or "").strip()
        wants_ideabrowser = state.get("input_mode") == "ideabrowser" and bool(url)

        if wants_ideabrowser and not _URL_RE.match(url):
            warning(sid, "research", "ideabrowser_url is not a URL — researching as an idea", value=url[:80])
            report_progress(sid, "That wasn't a URL — researching it as an idea instead…")
            wants_ideabrowser = False

        if wants_ideabrowser:
            report_progress(sid, "Fetching IdeaBrowser page with Exa…")
            try:
                imported = import_idea_from_url(url, session_id=sid)
                research = {
                    "source": "ideabrowser",
                    "imported": imported,
                    "competitors": [{"name": imported.get("main_competitor", ""), "url": ""}],
                    "pain_points": [imported.get("problem", "")],
                    "demand_signals": imported.get("execution_hints", []),
                }
                updated = {
                    **state,
                    "status": "researched",
                    "market_research": research,
                    "competitors": research["competitors"],
                    "pain_points": research["pain_points"],
                    "demand_signals": research["demand_signals"],
                }
                info(sid, "research", "ideabrowser import ok", product=imported.get("product_name"))
                return append_audit(
                    updated,
                    agent="research",
                    decision="Imported IdeaBrowser research",
                    rationale=imported.get("description", ""),
                    sources=[url],
                )
            except Exception as exc:
                warning(
                    sid,
                    "research",
                    f"IdeaBrowser import failed — falling back to idea research: {exc}",
                )
                report_progress(sid, "Couldn't read that IdeaBrowser page — researching it as an idea instead…")

        domain = _idea_seed(state)
        report_progress(sid, f"Running 3 Exa searches in parallel for “{domain}”…")

        queries = [
            (f"best {domain} software competitors pricing", "competitors"),
            (f"reddit {domain} frustrating problems", "pain_points"),
            (f"{domain} product hunt OR show hn launch", "demand"),
        ]

        results: dict[str, list] = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(exa_search, query, 3, sid): label for query, label in queries
            }
            for future in as_completed(futures):
                label = futures[future]
                results[label] = future.result()
                info(sid, "research", f"exa {label} ok", count=len(results[label]))
                report_progress(sid, f"Exa {label} search complete")

        competitors = results.get("competitors", [])
        pain_points = results.get("pain_points", [])
        demand = results.get("demand", [])

        research = {
            "source": "exa",
            "competitors": competitors,
            "pain_points": [p.get("snippet", "")[:240] for p in pain_points],
            "demand_signals": [d.get("title", "") for d in demand],
        }

        updated = {
            **state,
            "status": "researched",
            "market_research": research,
            "competitors": competitors,
            "pain_points": research["pain_points"],
            "demand_signals": research["demand_signals"],
        }
        return append_audit(
            updated,
            agent="research",
            decision=f"Completed parallel Exa research for {domain}",
            rationale="Collected competitors, pain points, and demand signals concurrently.",
            sources=[item["url"] for item in competitors[:3] if item.get("url")],
        )
