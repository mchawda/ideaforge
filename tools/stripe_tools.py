from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx
import stripe

from orchestrator.stage_log import error, info, warning


def resolve_checkout_success_url(product_url: str) -> str:
    """Best post-checkout landing path on the deployed product.

    Prefer real onboarding routes (/signup, /dashboard) before /app.html: Next.js
    (v0) apps return a soft 200 for unknown paths like /app.html, which would send
    payers to a not-found page. The root "/?checkout=success" fallback is handled
    natively by our functional single-page apps.
    """
    base = (product_url or "").strip().rstrip("/")
    if not base or not urlparse(base).scheme:
        return ""

    def _real(path: str) -> bool:
        try:
            response = httpx.get(f"{base}{path}", timeout=12, follow_redirects=True)
            if response.status_code >= 400:
                return False
            body = response.text.lower()
            # Reject Next.js soft-404 pages (200 status but "not found" content).
            if "this page could not be found" in body or "404" in body[:2000] and "not found" in body:
                return False
            return True
        except httpx.HTTPError:
            return False

    for path in ("/signup", "/dashboard", "/app", "/login", "/app.html"):
        if _real(path):
            return f"{base}{path}?checkout=success"
    return f"{base}/?checkout=success"


def _payment_link_id(url: str) -> str | None:
    if not url:
        return None
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    for link in stripe.PaymentLink.list(limit=100).auto_paging_iter():
        if link.url == url:
            return link.id
    return None


def configure_checkout_redirect(
    payment_link_url: str,
    *,
    success_url: str,
    session_id: str | None = None,
) -> bool:
    """Send customers to the live product after Stripe checkout completes."""
    if not payment_link_url or not success_url:
        return False

    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    link_id = _payment_link_id(payment_link_url)
    if not link_id:
        warning(session_id, "stripe", "payment link not found for redirect", url=payment_link_url[:80])
        return False

    stripe.PaymentLink.modify(
        link_id,
        after_completion={
            "type": "redirect",
            "redirect": {"url": success_url},
        },
    )
    info(session_id, "stripe", "checkout redirect configured", link=payment_link_url[-24:], to=success_url)
    return True


def configure_session_checkout_redirects(
    state: dict[str, Any],
    *,
    product_url: str | None = None,
    session_id: str | None = None,
) -> dict[str, str]:
    """Point all session Stripe links at the product after checkout."""
    sid = session_id or state.get("session_id")
    live_url = (product_url or state.get("final_url") or state.get("vercel_deployment_url") or "").strip()
    success_url = resolve_checkout_success_url(live_url)
    if not success_url:
        return {}

    updated: dict[str, str] = {}
    for key in ("stripe_free_payment_link", "stripe_payment_link"):
        link = (state.get(key) or "").strip()
        if link and configure_checkout_redirect(link, success_url=success_url, session_id=sid):
            updated[key] = link
    return updated


def _ensure_free_tier(price_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Always include a $0 starter tier for 'Start free' Stripe checkout."""
    if any((tier.get("price") or 0) <= 0 for tier in price_points):
        return price_points
    return [{"name": "Starter", "price": 0, "features": []}, *price_points]


def create_product_with_prices(
    *,
    product_name: str,
    description: str,
    price_points: list[dict[str, Any]],
    session_id: str | None = None,
    success_url: str = "",
) -> dict[str, Any]:
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    tiers = _ensure_free_tier(price_points)
    info(session_id, "stripe", "creating product", name=product_name, tiers=len(tiers))

    try:
        product = stripe.Product.create(name=product_name, description=description)
        prices: list[dict[str, Any]] = []
        free_payment_link = ""
        paid_payment_link = ""

        for tier in tiers:
            amount = tier.get("price")
            if amount is None:
                continue
            amount = float(amount)
            if amount < 0:
                continue

            tier_name = tier.get("name", "Pro")
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(amount * 100),
                currency="usd",
                recurring={"interval": "month"},
                nickname=tier_name,
            )
            link_params: dict[str, Any] = {
                "line_items": [{"price": price.id, "quantity": 1}],
            }
            # $0 subscriptions: email only — no card required (Stripe default is "always")
            if amount <= 0:
                link_params["payment_method_collection"] = "if_required"
            if success_url:
                link_params["after_completion"] = {
                    "type": "redirect",
                    "redirect": {"url": success_url},
                }
            link = stripe.PaymentLink.create(**link_params)
            entry = {
                "tier": tier_name,
                "price_id": price.id,
                "payment_link": link.url,
                "amount": amount,
            }
            prices.append(entry)

            if amount <= 0 and not free_payment_link:
                free_payment_link = link.url
                info(session_id, "stripe", "free tier link", tier=tier_name, url=link.url)
            elif amount > 0 and not paid_payment_link:
                paid_payment_link = link.url
                info(session_id, "stripe", "paid tier link", tier=tier_name, url=link.url)

        # Fallback: if only free tier exists, paid link stays empty
        if not free_payment_link and prices:
            free_payment_link = prices[0]["payment_link"]

        info(
            session_id,
            "stripe",
            "product ok",
            product_id=product.id,
            tiers=len(prices),
            has_free=bool(free_payment_link),
            has_paid=bool(paid_payment_link),
        )
        return {
            "stripe_product_id": product.id,
            "stripe_prices": prices,
            "stripe_free_payment_link": free_payment_link,
            "stripe_payment_link": paid_payment_link or free_payment_link,
            "stripe_checkout_url": paid_payment_link or free_payment_link,
        }
    except stripe.StripeError as exc:
        error(session_id, "stripe", f"API error: {exc}", exc_info=True)
        raise
