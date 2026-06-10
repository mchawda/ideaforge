from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

PORTFOLIO_PATH = Path(__file__).resolve().parent.parent / "config" / "aura_portfolio.json"


@lru_cache(maxsize=1)
def _load_portfolio() -> list[dict[str, Any]]:
    with PORTFOLIO_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def list_aura_templates() -> list[dict[str, Any]]:
    return _load_portfolio()


def _score_template(template: dict[str, Any], haystack: str) -> int:
    score = 0
    for niche in template.get("niches") or []:
        token = niche.lower().strip()
        if not token:
            continue
        if token in haystack:
            score += 3
        for word in token.split():
            if len(word) > 3 and word in haystack:
                score += 1
    name = str(template.get("name", "")).lower()
    if name and name in haystack:
        score += 2
    return score


def select_aura_template(
    *,
    product_name: str = "",
    niche: str = "",
    icp: str = "",
    features: list[str] | None = None,
    user_input: str = "",
) -> dict[str, Any]:
    """Pick the best-matching Aura portfolio template for a product idea."""
    portfolio = _load_portfolio()
    haystack = " ".join(
        [
            product_name,
            niche,
            icp,
            user_input,
            " ".join(features or []),
        ]
    ).lower()
    haystack = re.sub(r"\s+", " ", haystack).strip()

    ranked = sorted(
        portfolio,
        key=lambda template: _score_template(template, haystack),
        reverse=True,
    )
    best = ranked[0]
    best_score = _score_template(best, haystack)

    if best_score == 0:
        # Stable variety when no niche match — hash product name to index.
        idx = sum(ord(ch) for ch in (product_name or user_input or "idea")) % len(portfolio)
        best = portfolio[idx]

    slug = best.get("aura_slug", "")
    share_url = f"https://www.aura.build/share/{slug}" if slug else "https://www.aura.build/"
    return {
        "id": best["id"],
        "name": best["name"],
        "source": best.get("source", "aura.build"),
        "aura_slug": slug,
        "mood": best.get("mood", ""),
        "layout": best.get("layout", ""),
        "typography": best.get("typography", ""),
        "reference_url": share_url,
        "aura_share_url": share_url,
    }


def resolve_ui_builder(state: dict) -> str:
    """Pick v0 or aura_html for product UI generation.

    Default: v0 when V0_API_KEY is set (full Next.js app). Aura is fallback only.
    """
    has_v0 = bool(os.getenv("V0_API_KEY", "").strip())
    pref = os.getenv("UI_BUILDER", "v0" if has_v0 else "aura").strip().lower()
    complexity = str(state.get("complexity") or "standard").lower()

    if pref in {"functional", "app", "spa"}:
        return "functional"
    if pref in {"aura", "aura_html", "aura.build"}:
        return "aura_html"
    if pref == "v0":
        return "v0" if has_v0 else "aura_html"
    if pref == "auto":
        if has_v0 and complexity in {"enterprise", "complex", "full", "standard"}:
            return "v0"
        return "aura_html"
    return "v0" if has_v0 else "aura_html"


def aura_style_block(template: dict[str, Any]) -> str:
    """Prompt fragment instructing v0 to remix an Aura portfolio direction."""
    return (
        f"Design direction — remix the Aura template portfolio style "
        f"\"{template['name']}\" ({template['source']}). "
        f"Mood: {template.get('mood', '')}. "
        f"Layout: {template.get('layout', '')}. "
        f"Typography: {template.get('typography', '')}. "
        "Make this product visually distinct from generic SaaS — unique palette, "
        "hero composition, and section rhythm matched to the niche. "
        "Do not copy IdeaForge operator branding (no Forge orange wordmark)."
    )
