from __future__ import annotations

import os
import re

from orchestrator.llm import chat_json
from orchestrator.progress import report_progress
from orchestrator.stage_log import info, stage, warning
from orchestrator.state import AgentState, append_audit
from tools.aura_build_tools import AuraBuildToolsError, build_and_deploy_aura_product
from tools.aura_html_tools import AuraHtmlError, build_and_deploy_aura_html
from tools.aura_portfolio import aura_style_block, resolve_ui_builder, select_aura_template
from tools.v0_tools import (
    V0BuildError,
    create_v0_chat,
    deploy_url_matches_product,
    redeploy_v0_chat,
)


def _fast_mode() -> bool:
    return os.getenv("FAST_MODE", "false").strip().lower() in {"1", "true", "yes"}


def _pick_aura_template(state: AgentState) -> dict:
    return select_aura_template(
        product_name=state.get("product_name", ""),
        niche=state.get("niche", ""),
        icp=state.get("icp", ""),
        features=state.get("features"),
        user_input=state.get("user_input", ""),
    )


def _integration_urls(state: AgentState) -> tuple[str, str, str]:
    free_checkout = (
        state.get("stripe_free_payment_link")
        or state.get("stripe_payment_link")
        or "{{STRIPE_FREE_CHECKOUT_URL}}"
    )
    paid_checkout = state.get("stripe_payment_link") or "{{STRIPE_CHECKOUT_URL}}"
    api_url = state.get("aws_api_url") or "{{API_URL}}"
    return free_checkout, paid_checkout, api_url


def _price_table(state: AgentState) -> str:
    tiers = state.get("price_points") or []
    if not tiers:
        return "Starter: free, Growth: $79/mo, Scale: custom"
    return ", ".join(
        f"{tier.get('name', 'Plan')}: ${tier.get('price', 0)}/mo" for tier in tiers[:4]
    )


def _is_crm_product(state: AgentState) -> bool:
    haystack = " ".join(
        [
            state.get("product_name") or "",
            state.get("niche") or "",
            state.get("user_input") or "",
            " ".join(state.get("features") or []),
        ]
    ).lower()
    return any(token in haystack for token in ("crm", "customer relationship", "sales pipeline", "deals"))


def _app_routes_spec(state: AgentState) -> str:
    """Domain-specific logged-in app routes — never default to CRM unless the product is a CRM."""
    product = state.get("product_name", "Product")
    features = state.get("features") or []
    feature_list = "\n".join(f"  - {feature}" for feature in features[:6]) or "  - Core workflow"
    niche = state.get("niche", "")

    if _is_crm_product(state):
        return f"""━━━ WORKING APP (protected CRM — must be usable, not a mockup) ━━━
8. /dashboard — CRM home: pipeline value, active deals, revenue signals, recent activity
9. /dashboard/contacts — Searchable contacts table; add/edit/delete (localStorage)
10. /dashboard/deals — Kanban pipeline (Lead → Qualified → Proposal → Closing → Won)
11. /dashboard/settings — Profile, workspace, logout

Seed realistic B2B CRM demo data (companies, contacts, deals in multiple stages)."""

    return f"""━━━ WORKING APP (protected — MUST match this product's niche, NOT a generic CRM) ━━━
Niche: {niche}
Implement these MVP features as real, interactive UI (forms, tables, charts, timelines — not lorem ipsum):
{feature_list}

Required routes (adapt names to the product domain):
8. /dashboard — Main workspace: key metrics + primary workflow for {product}
9. /dashboard/[feature-a] — First core MVP feature page (full CRUD or logging UI)
10. /dashboard/[feature-b] — Second core MVP feature page (distinct from feature-a)
11. /dashboard/settings — Profile, preferences, logout

Each /dashboard/* page must implement the actual product workflow (e.g. biohacking → experiment builder + daily biomarker log;
habit tracker → habits list + streak heatmap; reading app → saved articles queue + tags).
Auth guard: all /dashboard/* redirect to /login without session.
Seed realistic demo data specific to {product} so the app is usable immediately after signup."""


def _full_product_prompt_spec(
    state: AgentState,
    free_checkout: str,
    paid_checkout: str,
    api_url: str,
    aura_template: dict,
) -> str:
    """Detailed v0 spec: marketing site + auth + domain-specific working app."""
    product = state.get("product_name", "Product")
    features = state.get("features") or []
    feature_list = "\n".join(f"  - {feature}" for feature in features[:6]) or "  - Core workflow automation"
    pricing = _price_table(state)
    style_block = aura_style_block(aura_template)
    app_routes = _app_routes_spec(state)

    return f"""Build a complete, production-ready Next.js 14 App Router SaaS product for {product}.
This is NOT a landing-page-only build. Reject scope that stops at marketing — you MUST ship a working logged-in app.

Product context:
- Niche: {state.get('niche', '')}
- ICP: {state.get('icp', '')}
- MVP features:
{feature_list}
- Pricing tiers: {pricing}

Visual direction (must feel distinctive, not a generic template):
{style_block}

━━━ MARKETING SITE (public) ━━━
1. / — Landing: hero, social proof, feature grid, workflow section, pricing preview, FAQ, footer
2. /product — Deep product overview with feature sections tied to the MVP list above
3. /pricing — Full pricing table ({pricing}); free/Starter tier CTA → {free_checkout}; paid tier CTAs → {paid_checkout}
4. /integrations — Integrations relevant to this niche (not generic placeholders)
5. /docs — Getting started docs: quickstart, API overview, FAQ

━━━ AUTH + DATA (use the LIVE AWS backend — this is a real API, not a mock) ━━━
A working REST backend (AWS API Gateway + Lambda + DynamoDB) is deployed at:
  {api_url}
All requests and responses are JSON. After login, send the token on every authed call as a header:
  Authorization: Bearer <token>
Endpoints:
  POST   {api_url}/signup        body {{"email","password","name"}}  -> {{"token","email"}}
  POST   {api_url}/login         body {{"email","password"}}         -> {{"token","email","name"}}  (demo: demo@demo.com / demo123)
  GET    {api_url}/me            (auth)                              -> {{"email","name"}}
  GET    {api_url}/items         (auth)                              -> {{"items":[...]}}
  POST   {api_url}/items         (auth) body {{...your fields}}      -> {{"id",...}}
  PUT    {api_url}/items/<id>    (auth) body {{...fields}}           -> {{"id",...}}
  DELETE {api_url}/items/<id>    (auth)                              -> {{"deleted":"<id>"}}

6. /signup — name + email + password; call POST /signup; store returned token in localStorage; redirect to /dashboard
7. /login — email + password; call POST /login (also accepts demo@demo.com / demo123); store token; redirect to /dashboard
- Persist ALL product data through /items. Each record = one item with product-specific fields
  (for {product}: store the core logged entities — e.g. each log/entry/record the user creates).
  GET /items to render lists, POST /items to create, PUT to edit, DELETE to remove. Never use only mock state.
- Centralize calls in a small lib/api.ts that reads NEXT_PUBLIC_API_URL (default {api_url}) and attaches the token.
- Guard all /dashboard/* routes: if no token in localStorage, redirect to /login.
- Resilience: if a request fails (offline), fall back to localStorage and resync — but the happy path MUST hit the API.

{app_routes}

━━━ CTA & NAV WIRING (critical) ━━━
- Every "Start free", "Start with {product}", hero CTA, and Starter/free tier button → href="{free_checkout}" (Stripe $0 checkout — NOT the paid link)
- Growth/Pro/Scale paid plan buttons → href="{paid_checkout}"
- Header "Sign in" → /login (app login, separate from Stripe checkout)
- Marketing nav links (Product, Pricing, Integrations, Docs) → their routes above
- Footer links → matching pages
- Set NEXT_PUBLIC_API_URL={api_url} and route all auth + data through it (see AUTH + DATA above)

━━━ POST-STRIPE CHECKOUT (critical) ━━━
- Add CheckoutSuccessBanner in root layout when URL has ?checkout=success
- Banner: "Payment complete!" + button "Open your account" → /signup (or /dashboard) + link to /login
- Show hint: demo@demo.com / demo123
- Stripe redirects here after payment — user must see a clear next step, never a dead end

Tech: Tailwind CSS, shadcn/ui, dark mode default, mobile-responsive sidebar on dashboard.
Quality bar: marketing site flows into a real domain-specific product — not a Lovable-style landing page with fake dashboard chrome."""


def _api_hard_block(api_url: str) -> str:
    """Non-negotiable rules appended verbatim so the API wiring is never softened away."""
    return f"""

━━━ NON-NEGOTIABLE BACKEND RULES (do exactly this — do not substitute localStorage) ━━━
This product MUST use the live AWS backend. Build `lib/api.ts` with a HARDCODED constant:
    const API_BASE = "{api_url}";
Do NOT read the URL only from process.env (env vars are not set on this deployment — the literal string above must appear in the code).
- signup(): POST `${{API_BASE}}/signup` {{email,password,name}} → save returned token in localStorage["token"].
- login(): POST `${{API_BASE}}/login` {{email,password}} → save token. (demo@demo.com / demo123 also works.)
- All authed fetches send header  Authorization: `Bearer ${{token}}`.
- Loading data: GET `${{API_BASE}}/items`. Creating: POST `${{API_BASE}}/items` with the record fields.
  Editing: PUT `${{API_BASE}}/items/<id>`. Deleting: DELETE `${{API_BASE}}/items/<id>`.
- The dashboard MUST read/write the user's records through these endpoints — localStorage may ONLY cache the token, never be the data store.
- Every dashboard mutation calls the API and re-fetches; do not keep data only in React state or localStorage.
"""


def _craft_v0_prompt(state: AgentState, aura_template: dict) -> str:
    sid = state["session_id"]
    free_checkout, paid_checkout, api_url = _integration_urls(state)
    product = state.get("product_name", "Product")
    features = state.get("features") or []
    complexity = state.get("complexity", "standard")
    style_block = aura_style_block(aura_template)
    spec = _full_product_prompt_spec(state, free_checkout, paid_checkout, api_url, aura_template)

    try:
        crafted = chat_json(
            "You write v0.dev prompts for full SaaS products (marketing site + auth + dashboard). "
            "Each product must look unique — use the Aura portfolio direction. Return JSON only.",
            f"""Craft a v0 prompt for a {complexity} full-stack SaaS product (not landing-only).

Product: {product}
Niche: {state.get('niche', '')}
Features: {features[:6]}
ICP: {state.get('icp', '')}
Stripe $0 checkout (Start free): {free_checkout}
Stripe paid checkout (Pro tiers): {paid_checkout}
AWS API URL: {api_url}

Aura portfolio direction:
{style_block}

Required deliverable: multi-page Next.js app with marketing pages, /signup, /login, AND a working logged-in app whose dashboard pages implement THIS product's MVP features (not a generic CRM unless the product is a CRM). Landing-only builds are unacceptable.

Use this spec as the foundation (expand with product-specific routes, copy, and UI):
{spec}

Return:
{{
  "prompt": "A detailed 4-6 paragraph v0 prompt covering ALL routes, auth flow, domain-specific app interactions, and visual direction. Be extremely specific about page content and CTA wiring.",
  "scope_note": "why this scope and visual direction fit the product"
}}""",
            tier="builder",
            session_id=sid,
        )
        report_progress(
            sid,
            f"Full product spec: {aura_template['name']} ({crafted.get('scope_note', 'Aura portfolio')[:60]})",
        )
        base = crafted.get("prompt") or spec
        return base + _api_hard_block(api_url)
    except Exception as exc:
        warning(sid, "builder", f"GPT-5.5 prompt craft failed, using fallback: {exc}")
        return spec + _api_hard_block(api_url)


def _fallback_prompt(state: AgentState, checkout: str, aura_template: dict) -> str:
    free_checkout, paid_checkout, api_url = _integration_urls(state)
    return _full_product_prompt_spec(state, free_checkout, paid_checkout, api_url, aura_template) + _api_hard_block(api_url)


def _success_payload(
    state: AgentState,
    *,
    aura_template: dict,
    ui_builder: str,
    prompt: str,
    demo_url: str,
    code: str,
    decision: str,
    rationale: str,
    sources: list[str],
) -> AgentState:
    return append_audit(
        {
            **state,
            "status": "ui_generated",
            "aura_template": aura_template,
            "ui_builder": ui_builder,
            "v0_prompt": prompt,
            "generated_ui_code": code,
            "vercel_deployment_url": demo_url,
            "final_url": demo_url or state.get("final_url", ""),
            "v0_status": "ready" if ui_builder in ("v0", "functional") else "fallback",
        },
        agent="builder",
        decision=decision,
        rationale=rationale,
        sources=sources,
    )


def _run_functional_app(state: AgentState, aura_template: dict) -> AgentState:
    """Deterministic, v0-independent path: a real working app wired to the AWS backend.

    Produces a single-page product (marketing hero + signup/login + logging dashboard)
    that persists to the live AWS API, with a localStorage fallback. Guarantees a usable
    platform on every build regardless of v0 credits/availability.
    """
    sid = state["session_id"]
    from tools.aura_html_tools import deploy_static_html
    from tools.functional_app import build_functional_app_html
    from tools.vercel_tools import allocate_project_name

    free_checkout, paid_checkout, api_url = _integration_urls(state)
    api = api_url if api_url and "{{" not in api_url else ""
    product = state.get("product_name", "Product")
    niche = (state.get("niche") or "").strip()
    tagline = (
        f"Log daily biomarkers, track protocols, and score what actually works."
        if "bio" in niche.lower() or "bio" in product.lower()
        else f"Track your {niche or 'progress'} with daily scores."
    )

    report_progress(sid, "Building functional app (signup + dashboard, wired to AWS)…")
    html = build_functional_app_html(
        product_name=product,
        tagline=tagline,
        niche=state.get("niche", ""),
        features=state.get("features") or [],
        api_url=api,
        free_checkout=free_checkout if "{{" not in free_checkout else "",
        paid_checkout=paid_checkout if "{{" not in paid_checkout else "",
        price_points=state.get("price_points") or [],
    )
    project = allocate_project_name(sid, product_name=product)
    demo_url = deploy_static_html(html, project_name=project, session_id=sid, product_name=product)
    report_progress(sid, f"Live product — {demo_url}")
    return _success_payload(
        state,
        aura_template=aura_template,
        ui_builder="functional",
        prompt="IdeaForge functional app (AWS-wired SPA: signup + logging dashboard)",
        demo_url=demo_url,
        code=html[:12000],
        decision=f"Deployed working {product} app (signup, dashboard, daily logging)",
        rationale=(
            f"v0-independent functional app wired to AWS API "
            f"{api or '(localStorage fallback — no API)'}. Live: {demo_url}"
        ),
        sources=["vercel.com"] + ([api] if api else []),
    )


def _aura_remix_enabled() -> bool:
    return os.getenv("AURA_REMIX_FIRST", "false").strip().lower() in {"1", "true", "yes"}


def _run_aura_html(state: AgentState, aura_template: dict) -> AgentState:
    """Degraded fallback — single-page HTML only. v0 is required for full SaaS apps."""
    sid = state["session_id"]
    from tools.vercel_tools import allocate_project_name

    project = allocate_project_name(sid, product_name=state.get("product_name", "product"))
    warning(
        sid,
        "builder",
        "aura HTML fallback — landing page only (set UI_BUILDER=v0 for full app)",
    )
    report_progress(
        sid,
        "v0 unavailable — deploying single-page HTML fallback (not a full product app)…",
    )

    if _aura_remix_enabled():
        slug = aura_template.get("aura_slug") or aura_template.get("id")
        try:
            result = build_and_deploy_aura_product(
                state,
                aura_template,
                session_id=sid,
                project_name=project,
            )
            demo_url = result["demo_url"]
            html = result["html"]
            share = result.get("aura_share_url") or aura_template.get(
                "reference_url", "https://www.aura.build/"
            )
            merged_template = {
                **aura_template,
                "aura_slug": result.get("aura_slug", slug),
                "reference_url": share,
                "aura_share_url": share,
            }
            report_progress(sid, f"Aura remix live (fallback) — {demo_url}")
            return _success_payload(
                state,
                aura_template=merged_template,
                ui_builder="aura_html",
                prompt=f"aura.build remix fallback: {merged_template['name']}",
                demo_url=demo_url,
                code=html[:12000],
                decision=f"Aura remix fallback — {merged_template['name']}",
                rationale=(
                    f"Degraded path: aura.build template remix (AURA_REMIX_FIRST). "
                    f"Not a full v0 app. Live: {demo_url}"
                ),
                sources=["aura.build", "vercel.com"],
            )
        except (AuraBuildToolsError, AuraHtmlError) as exc:
            warning(sid, "builder", f"aura remix failed, using LLM HTML: {exc}")

    result = build_and_deploy_aura_html(state, aura_template, session_id=sid)
    demo_url = result["demo_url"]
    html = result["html"]
    report_progress(sid, f"Aura HTML live (fallback) — {demo_url}")
    return _success_payload(
        state,
        aura_template=aura_template,
        ui_builder="aura_html",
        prompt=f"Aura HTML fallback: {aura_template['name']}",
        demo_url=demo_url,
        code=html[:12000],
        decision=f"Aura HTML fallback — {aura_template['name']}",
        rationale=(
            f"Degraded path: single-page marketing HTML only. "
            f"Use v0 for full signup + dashboard app. Live: {demo_url}"
        ),
        sources=["aura.build", "vercel.com"],
    )


def _deployment_unhealthy(url: str, sid: str | None = None) -> bool:
    """True if the deployed URL serves a Vercel build-failure / error placeholder.

    v0 can report 'success' and return a URL while the actual Vercel build failed —
    that URL then serves a 'Deployment has failed' page (HTTP 200). Catch it so we
    can fall back to the deterministic functional app instead of shipping a dead link.
    """
    import httpx

    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
    except httpx.HTTPError:
        return True
    body = r.text.lower()
    markers = (
        "deployment has failed",
        "this deployment is not available",
        "deployment_not_found",
        "application error: a client-side exception",
    )
    bad = any(m in body for m in markers)
    if bad:
        warning(sid, "builder", "deployed URL serves an error page", url=url[:80])
    return bad


def _run_v0(state: AgentState, aura_template: dict, prompt: str) -> AgentState:
    sid = state["session_id"]
    product_name = state.get("product_name", "")
    result = create_v0_chat(
        prompt,
        session_id=sid,
        # Full-app generations can take 15-20+ min on v0's slow days; bailing
        # early wastes a paid generation, so give it room to finish.
        poll_timeout=1500,
        on_progress=lambda message: report_progress(sid, message),
        name_hint=product_name,
    )
    demo_url = result.get("demo_url") or ""
    production_url = result.get("production_url") or ""
    preview_only = bool(
        demo_url and "vusercontent.net" in demo_url and not production_url
    )
    live_url = production_url or demo_url
    if live_url and not deploy_url_matches_product(live_url, product_name):
        raise V0BuildError(
            f"v0 returned wrong product URL ({live_url}) for {product_name} — refusing cross-product reuse"
        )
    if preview_only and result.get("chat_id"):
        warning(
            sid,
            "builder",
            "v0 preview only — retrying permanent Vercel deploy",
            preview=demo_url[:80],
        )
        report_progress(sid, "Retrying v0 production deploy for a permanent URL…")
        try:
            result = redeploy_v0_chat(
                result["chat_id"],
                session_id=sid,
                on_progress=lambda message: report_progress(sid, message),
            )
            production_url = result.get("production_url") or ""
            demo_url = result.get("demo_url") or demo_url
            preview_only = bool(
                demo_url and "vusercontent.net" in demo_url and not production_url
            )
            live_url = production_url or demo_url
        except V0BuildError as exc:
            warning(sid, "builder", f"v0 redeploy failed: {exc}")

    if preview_only:
        # v0 generated, but the permanent Vercel build never succeeded. Do NOT ship
        # the preview or downgrade to the functional shell — raise so the builder can
        # retry a fresh v0 generation, then stop and report if it fails again.
        raise V0BuildError(
            f"v0 production deploy failed (preview only, no permanent build): {demo_url[:120]}"
        )

    # v0 returned a URL — verify it actually serves the app, not a build-failure page.
    if live_url and _deployment_unhealthy(live_url, sid):
        raise V0BuildError(
            f"v0 deployment built an error page (Vercel build failed): {live_url[:120]}"
        )

    files = result.get("files") or []
    code = "\n\n".join(
        f"// {file.get('name', 'file')}\n{file.get('content', '')}" for file in files[:3]
    )
    info(
        sid,
        "builder",
        "v0 ok",
        demo_url=demo_url or "pending",
        production_url=production_url or "preview-only",
        files=len(files),
    )
    deploy_note = (
        f"Permanent Vercel URL: {production_url}"
        if production_url
        else f"Preview: {demo_url or 'pending'}"
    )
    payload = _success_payload(
        state,
        aura_template=aura_template,
        ui_builder="v0",
        prompt=prompt,
        demo_url=live_url,
        code=code,
        decision=f"v0 UI — {aura_template['name']} style",
        rationale=f"Aura portfolio direction via v0. {deploy_note}",
        sources=["v0.dev", "aura.build", "vercel.com"],
    )
    payload["v0_chat_id"] = result.get("chat_id", "")
    payload["v0_version_id"] = result.get("version_id", "")
    return payload


def run_builder(state: AgentState) -> AgentState:
    sid = state["session_id"]
    with stage(sid, "builder", fast_mode=_fast_mode()):
        if _fast_mode():
            info(sid, "builder", "skipped — turbo mode")
            return append_audit(
                {**state, "status": "ui_skipped", "v0_prompt": ""},
                agent="builder",
                decision="v0 skipped (turbo mode)",
                rationale="FAST_MODE enabled — Stripe and AWS deploy without waiting for v0.",
                sources=["v0.dev"],
            )

        aura_template = state.get("aura_template") or _pick_aura_template(state)
        ui_builder = resolve_ui_builder(state)
        # Internal portfolio = visual direction for v0 prompts only. Aura HTML/remix is fallback.
        if ui_builder == "aura_html" and os.getenv("V0_API_KEY", "").strip():
            explicit_aura = os.getenv("UI_BUILDER", "").strip().lower() in {
                "aura",
                "aura_html",
                "aura.build",
            }
            if not explicit_aura:
                warning(sid, "builder", "forcing v0 — aura paths are fallback-only")
                ui_builder = "v0"
        info(sid, "builder", "ui builder selected", builder=ui_builder, template=aura_template.get("name"))
        slug = aura_template.get("aura_slug") or "portfolio"
        if ui_builder == "v0":
            report_progress(
                sid,
                f"v0 full app · style from portfolio ({aura_template['name']})",
            )
        elif ui_builder == "functional":
            report_progress(sid, "Building functional app (signup + dashboard) wired to AWS…")
        else:
            report_progress(sid, f"HTML fallback only · {slug}")

        prompt = _craft_v0_prompt(state, aura_template) if ui_builder == "v0" else ""

        # Explicit non-v0 builders run their own deterministic path.
        if ui_builder in ("functional", "aura_html"):
            try:
                return _run_functional_app(state, aura_template)
            except (AuraHtmlError, AuraBuildToolsError) as exc:
                return _builder_failed(state, aura_template, ui_builder, prompt, exc)

        # v0 path: retry once on failure, then STOP and report.
        # Never silently downgrade to the functional single-page shell — a failed
        # v0 build must surface, not ship a degraded product.
        try:
            return _run_v0(state, aura_template, prompt)
        except (V0BuildError, AuraHtmlError, AuraBuildToolsError) as first_exc:
            warning(sid, "builder", f"v0 build failed (attempt 1/2): {first_exc}")
            report_progress(
                sid,
                "v0 build failed — retrying one fresh v0 generation (no shortcuts)…",
            )
            try:
                return _run_v0(state, aura_template, prompt)
            except (V0BuildError, AuraHtmlError, AuraBuildToolsError) as second_exc:
                warning(sid, "builder", f"v0 build failed again (attempt 2/2): {second_exc}")
                return _builder_failed(state, aura_template, "v0", prompt, second_exc)


def _builder_failed(
    state: AgentState,
    aura_template: dict,
    ui_builder: str,
    prompt: str,
    exc: Exception,
) -> AgentState:
    """Record a hard build failure. Does NOT ship a degraded fallback product."""
    sid = state["session_id"]
    err = str(exc)
    if "out of credits" in err.lower() or "payment_required" in err.lower():
        report_progress(sid, "v0 is out of credits — build stopped (no fallback shipped).")
    elif "daily message limit" in err.lower() or "too_many_requests" in err.lower():
        report_progress(sid, "v0 daily limit reached — build stopped (no fallback shipped).")
    else:
        report_progress(sid, "v0 build failed twice — stopped so you can decide next steps.")
    return append_audit(
        {
            **state,
            "status": "ui_failed",
            "aura_template": aura_template,
            "ui_builder": ui_builder,
            "v0_prompt": prompt,
            "error": err,
            "v0_status": "error",
        },
        agent="builder",
        decision="v0 UI generation failed (no degraded fallback shipped)",
        rationale=(
            f"v0 build failed after retry: {err}. Per policy, the pipeline stops "
            f"instead of shipping the functional single-page shell."
        ),
        sources=["v0.dev"],
    )
