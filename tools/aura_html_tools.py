from __future__ import annotations

import os
import re
from typing import Any

import httpx

from orchestrator.llm import chat_text
from orchestrator.stage_log import error, info, warning
from tools.aura_portfolio import aura_style_block
from tools.checkout_success import inject_checkout_success_script


class AuraHtmlError(Exception):
    pass


_FREE_CTA_RE = re.compile(
    r"(start\s*free|get\s*started|try\s*free|start\s*with|initialize|sign\s*up\s*free|free\s*trial)",
    re.I,
)
_PAID_CTA_RE = re.compile(
    r"(upgrade|go\s*pro|buy\s*now|subscribe|get\s*pro|choose\s*pro|paid|growth|scale)",
    re.I,
)


def _wire_stripe_links(html: str, free_checkout: str, paid_checkout: str) -> str:
    """Ensure Stripe checkout URLs appear in CTAs — LLM often omits them."""
    if not free_checkout or free_checkout.startswith("#"):
        return html
    if free_checkout in html and (not paid_checkout or paid_checkout in html or paid_checkout.startswith("#")):
        return html

    def repl_anchor(match: re.Match[str]) -> str:
        tag = match.group(0)
        inner = match.group(2) or ""
        if free_checkout in tag or paid_checkout in tag:
            return tag
        href = paid_checkout if _PAID_CTA_RE.search(inner) and paid_checkout and not paid_checkout.startswith("#") else free_checkout
        if 'href="' in tag:
            return re.sub(r'href="[^"]*"', f'href="{href}"', tag, count=1)
        if "href='" in tag:
            return re.sub(r"href='[^']*'", f"href='{href}'", tag, count=1)
        return tag.replace("<a ", f'<a href="{href}" ', 1)

    # Wire <a> tags with CTA-like text
    html = re.sub(r"<a\b([^>]*)>(.*?)</a>", repl_anchor, html, flags=re.I | re.S)

    # Wire <button onclick> for common CTA buttons without links
    def button_to_link(match: re.Match[str]) -> str:
        inner = match.group(1) or ""
        if _PAID_CTA_RE.search(inner):
            href = paid_checkout if paid_checkout and not paid_checkout.startswith("#") else free_checkout
        else:
            href = free_checkout
        classes = match.group(2) or ""
        return f'<a href="{href}" class="{classes.strip()}">{inner}</a>'

    html = re.sub(
        r"<button([^>]*)class=\"([^\"]*)\"[^>]*>(.*?)</button>",
        lambda m: button_to_link(m) if _FREE_CTA_RE.search(m.group(3) or "") or _PAID_CTA_RE.search(m.group(3) or "") else m.group(0),
        html,
        flags=re.I | re.S,
    )

    # Last resort: inject hidden stripe if still missing
    if free_checkout not in html:
        html = html.replace(
            "</body>",
            f'\n<a id="stripe-free" href="{free_checkout}" style="position:fixed;bottom:1rem;right:1rem;'
            f'padding:0.75rem 1.25rem;background:#f97316;color:#000;border-radius:9999px;'
            f'font-weight:600;text-decoration:none;z-index:9999">Start free</a>\n</body>',
            1,
        )
    return html


def _strip_html_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:html)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _slugify(name: str, session_id: str) -> str:
    from tools.vercel_tools import allocate_project_name

    return allocate_project_name(session_id, product_name=name)


def generate_aura_html(
    state: dict[str, Any],
    aura_template: dict[str, Any],
    *,
    session_id: str | None = None,
) -> str:
    """Generate a single-file Aura-style HTML landing page via LLM."""
    product = state.get("product_name", "Product")
    features = state.get("features") or []
    free_checkout = state.get("stripe_free_payment_link") or state.get("stripe_payment_link") or "#signup"
    paid_checkout = state.get("stripe_payment_link") or "#pricing"
    price_points = state.get("price_points") or []
    pricing_lines = ", ".join(
        f"{tier.get('name', 'Plan')}: ${tier.get('price', 0)}/mo" for tier in price_points[:3]
    )
    style_block = aura_style_block(aura_template)

    system = (
        "You export production-ready landing pages in Aura.build style. "
        "Return a complete single HTML document only — no markdown fences, no explanation."
    )
    user = f"""Build a unique SaaS landing page as one HTML file.

Product: {product}
Niche: {state.get('niche', '')}
ICP: {state.get('icp', '')}
Features: {', '.join(features[:5])}
Pricing: {pricing_lines or 'Starter free, Pro $29/mo'}
Start free CTA ($0 Stripe): {free_checkout}
Paid plan CTA: {paid_checkout}

{style_block}

Requirements:
- Single index.html with Tailwind via CDN (https://cdn.tailwindcss.com)
- Responsive mobile-first layout matching the Aura template mood
- Hero, features, pricing, footer — "Start free" links to {free_checkout}; paid tiers link to {paid_checkout}
- Unique color palette for this product — not IdeaForge orange
- Inline minimal JS only if needed
- Semantic HTML, accessible contrast
"""

    info(session_id, "aura_html", "generating", product=product, template=aura_template.get("id"))

    # GPT-5.x uses max_completion_tokens for reasoning + output — 8k can exhaust with no HTML returned.
    raw = ""
    for attempt, (tier, tokens) in enumerate(
        [("builder", 16_000), ("builder", 20_000), ("fast", 12_000)],
        start=1,
    ):
        raw = chat_text(system, user, tier=tier, session_id=session_id, max_tokens=tokens)
        if raw and "<html" in raw.lower() and len(raw) >= 500:
            break
        warning(
            session_id,
            "aura_html",
            f"attempt {attempt} returned insufficient HTML",
            length=len(raw or ""),
            tier=tier,
        )

    html = _wrap_html_document(_strip_html_fences(raw), product=product)
    html = _wire_stripe_links(html, free_checkout, paid_checkout)
    html = inject_checkout_success_script(html)

    if "<html" not in html.lower() or len(html) < 500:
        warning(session_id, "aura_html", "invalid html output", length=len(html))
        raise AuraHtmlError(
            "Aura HTML generation returned invalid output — LLM token limit may have been exceeded"
        )

    return html


def _wrap_html_document(content: str, *, product: str) -> str:
    """Ensure model output is a complete HTML document."""
    text = content.strip()
    if not text:
        return text
    lower = text.lower()
    if "<html" in lower:
        return text
    if lower.startswith("<!doctype"):
        return text
    body = text
    if "<body" not in lower:
        body = f"<body class=\"min-h-screen bg-slate-950 text-slate-100\">{text}</body>"
    return (
        f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        f"<meta charset=\"UTF-8\" />\n"
        f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
        f"<title>{product}</title>\n"
        f"<script src=\"https://cdn.tailwindcss.com\"></script>\n"
        f"</head>\n{body}\n</html>"
    )


def deploy_static_html(
    html: str,
    *,
    project_name: str = "",
    session_id: str | None = None,
    product_name: str = "",
    extra_files: dict[str, str] | None = None,
) -> str:
    """Deploy HTML to Vercel and return the production URL."""
    from tools.vercel_tools import allocate_project_name, ensure_project_public, verify_public_url

    token = os.getenv("VERCEL_TOKEN", "").strip() or os.getenv("AI_GATEWAY_API_KEY", "").strip()
    if not token:
        raise AuraHtmlError("VERCEL_TOKEN not configured — cannot deploy Aura HTML")

    sid = session_id or "deploy"
    primary = allocate_project_name(
        sid, product_name=product_name, preferred=project_name or None
    )
    deploy_names = [primary]
    fallback = allocate_project_name(f"{sid}-alt", product_name=product_name)
    if fallback not in deploy_names:
        deploy_names.append(fallback)

    team_id = os.getenv("VERCEL_TEAM_ID", "").strip()
    params = {"teamId": team_id} if team_id else {}

    files = [{"file": "index.html", "data": html}]
    for path, content in (extra_files or {}).items():
        files.append({"file": path.lstrip("/"), "data": content})

    payload: dict[str, Any] = {
        "files": files,
        "target": "production",
        "projectSettings": {
            "framework": None,
            "buildCommand": None,
            "installCommand": None,
            "outputDirectory": None,
        },
    }
    params = {**params, "skipAutoDetectionConfirmation": "1"}

    last_error = "unknown deploy error"
    data: dict[str, Any] = {}
    resolved_project = primary

    for attempt_name in deploy_names:
        payload["name"] = attempt_name
        info(session_id, "aura_html", "deploying", project=attempt_name)
        response = httpx.post(
            "https://api.vercel.com/v13/deployments",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            json=payload,
            timeout=120,
        )
        if response.status_code < 400:
            data = response.json()
            resolved_project = attempt_name
            break
        last_error = response.text[:300]
        error(
            session_id,
            "aura_html",
            "deploy failed",
            status=response.status_code,
            body=last_error,
            project=attempt_name,
        )
        if response.status_code not in {400, 409, 422}:
            raise AuraHtmlError(f"Vercel deploy failed: HTTP {response.status_code}")
    else:
        raise AuraHtmlError(f"Vercel deploy failed: {last_error}")

    url = data.get("url") or ""
    alias = (data.get("alias") or [None])[0]
    deployment_url = f"https://{alias}" if alias else (f"https://{url}" if url else "")
    if not deployment_url:
        raise AuraHtmlError("Vercel deploy succeeded but no URL returned")

    ensure_project_public(resolved_project, session_id=session_id)
    if not verify_public_url(deployment_url):
        ensure_project_public(resolved_project, session_id=session_id)
    info(session_id, "aura_html", "deployed", url=deployment_url, project=resolved_project)
    return deployment_url


def build_and_deploy_aura_html(
    state: dict[str, Any],
    aura_template: dict[str, Any],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Generate Aura-style HTML and deploy to Vercel."""
    sid = session_id or state.get("session_id")
    html = generate_aura_html(state, aura_template, session_id=sid)
    product = state.get("product_name", "product")
    project = _slugify(product, sid or "session")
    demo_url = deploy_static_html(
        html,
        project_name=project,
        session_id=sid,
        product_name=product,
    )
    return {
        "html": html,
        "demo_url": demo_url,
        "project_name": project,
    }
