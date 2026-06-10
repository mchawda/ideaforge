from __future__ import annotations

import re
from typing import Any

from orchestrator.llm import chat_json, chat_text
from orchestrator.stage_log import info, warning
from tools.aura_build_client import (
    AuraBuildError,
    fetch_template_html,
    prepare_reference_excerpt,
)
from tools.aura_html_tools import deploy_static_html
from tools.aura_portfolio import aura_style_block


class AuraBuildToolsError(AuraBuildError):
    pass


def _wire_checkout_urls(html: str, free_checkout: str, paid_checkout: str) -> str:
    """Ensure primary CTAs point at live Stripe checkout URLs."""
    wired = html
    for pattern in (
        r'href=["\']#(?:signup|pricing|checkout|get-started)["\']',
        r'href=["\']#["\']',
    ):
        wired = re.sub(pattern, f'href="{free_checkout}"', wired, count=6)

    wired = re.sub(
        r'(>\s*(?:Pro|Growth|Scale|Upgrade)[^<]{0,40}</a>)',
        lambda m: m.group(0),
        wired,
    )
    if paid_checkout and paid_checkout not in wired:
        wired = wired.replace('href="#pricing"', f'href="{paid_checkout}"', 2)
    return wired


def _remix_with_llm(
    *,
    reference_html: str,
    state: dict[str, Any],
    aura_template: dict[str, Any],
    session_id: str | None,
) -> str:
    product = state.get("product_name", "Product")
    features = state.get("features") or []
    price_points = state.get("price_points") or []
    free_checkout = state.get("stripe_free_payment_link") or state.get("stripe_payment_link") or "#signup"
    paid_checkout = state.get("stripe_payment_link") or "#pricing"
    pricing_lines = ", ".join(
        f"{tier.get('name', 'Plan')}: ${tier.get('price', 0)}/mo" for tier in price_points[:3]
    )
    excerpt = prepare_reference_excerpt(reference_html)
    style_block = aura_style_block(aura_template)
    share = aura_template.get("reference_url") or aura_template.get("aura_share_url", "https://www.aura.build/")

    system = (
        "You remix aura.build landing page HTML for a new SaaS product. "
        "Preserve the Aura template's layout, motion, Tailwind structure, and visual craft. "
        "Return a complete single HTML document only — no markdown fences."
    )
    user = f"""Remix this Aura.build template for a new product.

Aura template: {aura_template.get('name')} ({share})
{style_block}

Product: {product}
Niche: {state.get('niche', '')}
ICP: {state.get('icp', '')}
Features: {', '.join(features[:6])}
Pricing: {pricing_lines or 'Starter free, Pro $29/mo'}
Start free CTA ($0 Stripe): {free_checkout}
Paid plan CTA: {paid_checkout}

Reference HTML from aura.build (@-style context):
{excerpt}

Rules:
- Keep the same section structure and animation patterns as the Aura reference
- Replace all copy, product name, and metadata for {product}
- Wire "Start free" / primary CTAs to {free_checkout}
- Wire paid tier CTAs to {paid_checkout}
- Single index.html, Tailwind via CDN if not already present
- Do not use IdeaForge orange branding
"""

    info(session_id, "aura_build", "remixing template with LLM", product=product)
    raw = ""
    for attempt, (tier, tokens) in enumerate(
        [("builder", 18_000), ("builder", 22_000), ("fast", 14_000)],
        start=1,
    ):
        raw = chat_text(system, user, tier=tier, session_id=session_id, max_tokens=tokens)
        if raw and "<html" in raw.lower() and len(raw) >= 800:
            break
        warning(
            session_id,
            "aura_build",
            f"remix attempt {attempt} insufficient",
            length=len(raw or ""),
        )

    if not raw or "<html" not in raw.lower():
        raise AuraBuildToolsError("Aura remix did not return valid HTML")

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:html)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return _wire_checkout_urls(text, free_checkout, paid_checkout)


def _apply_text_replacements(html: str, replacements: list[dict[str, str]]) -> str:
    updated = html
    for item in replacements:
        find = item.get("find", "")
        replace = item.get("replace", "")
        if find and find in updated:
            updated = updated.replace(find, replace)
    return updated


def _fast_remix_in_place(
    *,
    reference_html: str,
    state: dict[str, Any],
    aura_template: dict[str, Any],
    session_id: str | None,
) -> str | None:
    """Try in-place copy swaps on full Aura HTML before full LLM regen."""
    excerpt = prepare_reference_excerpt(reference_html, max_chars=6000)
    product = state.get("product_name", "Product")
    try:
        plan = chat_json(
            "You customize aura.build landing pages. Return JSON only.",
            f"""Given this Aura template excerpt and new product, return text replacements.

Aura template: {aura_template.get('name')}
Reference excerpt:
{excerpt}

New product: {product}
Niche: {state.get('niche', '')}
ICP: {state.get('icp', '')}
Features: {state.get('features', [])[:5]}

Return:
{{
  "replacements": [{{"find": "exact string from excerpt", "replace": "new string"}}],
  "title": "new <title> text without tags"
}}
Max 25 replacements. Only strings that literally appear in the reference.""",
            tier="fast",
            session_id=session_id,
        )
    except Exception as exc:
        warning(session_id, "aura_build", f"fast remix plan failed: {exc}")
        return None

    replacements = plan.get("replacements") or []
    if not replacements:
        return None

    html = _apply_text_replacements(reference_html, replacements)
    title = plan.get("title")
    if title:
        html = re.sub(r"<title>[^<]*</title>", f"<title>{title}</title>", html, count=1)

    free_checkout = state.get("stripe_free_payment_link") or state.get("stripe_payment_link") or "#signup"
    paid_checkout = state.get("stripe_payment_link") or "#pricing"
    return _wire_checkout_urls(html, free_checkout, paid_checkout)


def generate_aura_product_html(
    state: dict[str, Any],
    aura_template: dict[str, Any],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Fetch aura.build template HTML, remix for product, return html + metadata."""
    fetched = fetch_template_html(aura_template, session_id=session_id)
    reference_html = fetched["html"]
    aura_template = {
        **aura_template,
        "aura_slug": fetched["slug"],
        "reference_url": fetched["share_url"],
        "aura_share_url": fetched["share_url"],
    }

    html = _fast_remix_in_place(
        reference_html=reference_html,
        state=state,
        aura_template=aura_template,
        session_id=session_id,
    )
    if not html or len(html) < 500:
        html = _remix_with_llm(
            reference_html=reference_html,
            state=state,
            aura_template=aura_template,
            session_id=session_id,
        )

    if "<html" not in html.lower() or len(html) < 500:
        raise AuraBuildToolsError("Aura.build remix produced invalid HTML")

    return {
        "html": html,
        "aura_slug": fetched["slug"],
        "aura_share_url": fetched["share_url"],
        "aura_template_title": fetched["title"],
        "source": "aura.build",
    }


def build_and_deploy_aura_product(
    state: dict[str, Any],
    aura_template: dict[str, Any],
    *,
    session_id: str | None = None,
    project_name: str,
) -> dict[str, Any]:
    result = generate_aura_product_html(state, aura_template, session_id=session_id)
    demo_url = deploy_static_html(
        result["html"],
        project_name=project_name,
        session_id=session_id,
        product_name=state.get("product_name", ""),
    )
    return {**result, "demo_url": demo_url}
