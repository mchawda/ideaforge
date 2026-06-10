"""Deterministic functional product app generator.

v0 codegen is unreliable (credits/limits) and won't wire to our backend.
This module produces a complete, self-contained single-page app (Tailwind via CDN +
vanilla JS) that we fully control, wired directly to the live AWS API
(see tools/aws_backend.py). It guarantees a real, usable product on every build:
signup/login + a daily logging dashboard with scores — not just a marketing page.

Data persists to the AWS backend when reachable, with a localStorage fallback so
the demo never dead-ends offline.
"""

from __future__ import annotations

import html
import json
from typing import Any


def _esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def build_functional_app_html(
    *,
    product_name: str,
    tagline: str,
    niche: str,
    features: list[str],
    api_url: str,
    free_checkout: str = "",
    paid_checkout: str = "",
    price_points: list[dict[str, Any]] | None = None,
    accent: str = "#10b981",
) -> str:
    """Return a complete HTML document: marketing hero + auth + working dashboard."""
    product = _esc(product_name or "Your Product")
    tag = _esc(tagline or f"The fastest way to run {niche or 'your'} the right way.")
    feats = [f for f in (features or []) if f][:4] or [
        "Log entries in seconds",
        "Track daily scores",
        "See your trends",
    ]
    feature_cards = "".join(
        f'<div class="rounded-2xl border border-white/10 bg-white/5 p-5">'
        f'<div class="text-sm font-medium text-white">{_esc(f)}</div></div>'
        for f in feats
    )
    tiers = price_points or [
        {"name": "Starter", "price": 0},
        {"name": "Pro", "price": 29},
    ]
    cfg = {
        "apiBase": api_url or "",
        "product": product_name or "Your Product",
        "niche": niche or "live product",
        "freeCheckout": free_checkout or "",
        "paidCheckout": paid_checkout or "",
        "tiers": tiers[:4],
        "accent": accent,
    }
    cfg_json = json.dumps(cfg)

    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{product} — {tag}</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  :root {{ --accent: {accent}; }}
  body {{ font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }}
  .accent-bg {{ background: var(--accent); }}
  .accent-text {{ color: var(--accent); }}
  .grid-bg {{ background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,.05) 1px, transparent 0); background-size: 28px 28px; }}
</style>
</head>
<body class="min-h-screen bg-[#0a0b0f] text-slate-100 grid-bg">
<div id="root"></div>

<script>
const CFG = {cfg_json};
const API = CFG.apiBase;
const LS = {{
  get t() {{ return localStorage.getItem("token") || ""; }},
  set t(v) {{ v ? localStorage.setItem("token", v) : localStorage.removeItem("token"); }},
  get email() {{ return localStorage.getItem("email") || ""; }},
  set email(v) {{ v ? localStorage.setItem("email", v) : localStorage.removeItem("email"); }},
}};

// ---- API with localStorage fallback (never dead-ends) ----
async function api(path, method, body) {{
  if (!API) throw new Error("offline");
  const res = await fetch(API + path, {{
    method,
    headers: {{ "Content-Type": "application/json", ...(LS.t ? {{ Authorization: "Bearer " + LS.t }} : {{}}) }},
    body: body ? JSON.stringify(body) : undefined,
  }});
  const data = await res.json().catch(() => ({{}}));
  if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
  return data;
}}

const localItems = {{
  key() {{ return "items:" + (LS.email || "anon"); }},
  list() {{ try {{ return JSON.parse(localStorage.getItem(this.key()) || "[]"); }} catch {{ return []; }} }},
  save(arr) {{ localStorage.setItem(this.key(), JSON.stringify(arr)); }},
}};

async function signup(name, email, password) {{
  try {{ const d = await api("/signup", "POST", {{ name, email, password }}); LS.t = d.token; LS.email = email; return; }}
  catch (e) {{ if (e.message === "offline") {{ LS.t = "local-" + email; LS.email = email; return; }} throw e; }}
}}
async function login(email, password) {{
  try {{ const d = await api("/login", "POST", {{ email, password }}); LS.t = d.token; LS.email = email; return; }}
  catch (e) {{ if (e.message === "offline") {{ LS.t = "local-" + email; LS.email = email; return; }} throw e; }}
}}
async function getItems() {{
  try {{ const d = await api("/items", "GET"); return d.items || []; }}
  catch (e) {{ if (e.message === "offline" || String(LS.t).startsWith("local-")) return localItems.list(); throw e; }}
}}
async function addItem(rec) {{
  try {{ return await api("/items", "POST", rec); }}
  catch (e) {{
    if (e.message === "offline" || String(LS.t).startsWith("local-")) {{
      const arr = localItems.list(); const item = {{ ...rec, id: "loc" + Date.now(), created_at: Date.now()/1000 }};
      arr.unshift(item); localItems.save(arr); return item;
    }}
    throw e;
  }}
}}
async function delItem(id) {{
  try {{ await api("/items/" + id, "DELETE"); }}
  catch (e) {{ if (e.message === "offline" || String(LS.t).startsWith("local-")) {{ localItems.save(localItems.list().filter(x => x.id !== id)); return; }} throw e; }}
}}

// ---- Views ----
const root = document.getElementById("root");
function h(s) {{ return s; }}

function pricingCards() {{
  const tiers = CFG.tiers || [{{name:"Starter",price:0}},{{name:"Pro",price:29}}];
  return tiers.map((t, i) => {{
    const isPro = i > 0;
    const price = t.price === 0 ? "Free" : "$" + t.price + "/mo";
    const cta = isPro && CFG.paidCheckout
      ? `<a href="${{CFG.paidCheckout}}" class="mt-6 block w-full rounded-xl ${{isPro ? "accent-bg text-black" : "border border-white/15 text-white hover:bg-white/5"}} py-3 text-center font-semibold">Subscribe to ${{escapeHtml(t.name)}}</a>`
      : `<button onclick="showAuth('signup')" class="mt-6 w-full rounded-xl accent-bg py-3 font-semibold text-black">Start free</button>`;
    return `<div class="rounded-2xl border ${{isPro ? "border-emerald-500/40 bg-emerald-500/5" : "border-white/10 bg-white/5"}} p-6">
      <div class="text-sm font-medium text-slate-400">${{escapeHtml(t.name)}}</div>
      <div class="mt-2 text-4xl font-semibold">${{price}}</div>
      <ul class="mt-4 space-y-2 text-sm text-slate-400">
        <li>✓ Daily logging dashboard</li>
        <li>✓ Trend scores & history</li>
        ${{isPro ? "<li>✓ Protocol tracking & exports</li><li>✓ Priority support</li>" : "<li>✓ Up to 50 entries/mo</li>"}}
      </ul>
      ${{cta}}
    </div>`;
  }}).join("");
}}

function landing() {{
  const checkoutBanner = new URLSearchParams(location.search).get("checkout") === "success"
    ? `<div class="mx-auto max-w-6xl px-6 pt-4"><div class="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">Payment received — create your account to access your workspace.</div></div>` : "";
  root.innerHTML = h(`
  ${{checkoutBanner}}
  <header class="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
    <div class="flex items-center gap-2"><div class="h-7 w-7 rounded-lg accent-bg"></div><span class="text-lg font-semibold">${{CFG.product}}</span></div>
    <nav class="hidden items-center gap-6 text-sm text-slate-400 md:flex">
      <a href="#features" class="hover:text-white">Features</a>
      <a href="#pricing" class="hover:text-white">Pricing</a>
      <button onclick="showAuth('login')" class="hover:text-white">Sign in</button>
    </nav>
    <div class="flex items-center gap-3">
      <button onclick="showAuth('signup')" class="rounded-full accent-bg px-5 py-2 text-sm font-semibold text-black">Start free</button>
    </div>
  </header>
  <main class="mx-auto max-w-6xl px-6">
    <section class="py-16 md:py-24">
      <div class="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-slate-300">Self-experimentation platform</div>
      <h1 class="mt-6 max-w-3xl text-5xl font-semibold leading-tight tracking-tight md:text-6xl">${{CFG.product}} — track what actually moves the needle</h1>
      <p class="mt-5 max-w-xl text-lg text-slate-400">{tag}</p>
      <div class="mt-8 flex flex-wrap gap-3">
        <button onclick="showAuth('signup')" class="rounded-full accent-bg px-6 py-3 font-semibold text-black">Open workspace — free</button>
        ${{CFG.paidCheckout ? `<a href="${{CFG.paidCheckout}}" class="rounded-full border border-white/15 px-6 py-3 font-semibold text-white hover:bg-white/5">Go Pro — $29/mo</a>` : ""}}
        ${{CFG.freeCheckout ? `<a href="${{CFG.freeCheckout}}" class="rounded-full border border-white/15 px-6 py-3 text-sm text-slate-300 hover:bg-white/5">Stripe checkout (free tier)</a>` : ""}}
      </div>
      <div class="mt-14 grid grid-cols-2 gap-4 md:grid-cols-4">{feature_cards}</div>
    </section>
    <section id="features" class="border-t border-white/10 py-20">
      <h2 class="text-3xl font-semibold">Everything you need to run experiments</h2>
      <p class="mt-3 max-w-2xl text-slate-400">Log biomarkers daily, tag protocols, and see before/after trends — not another static landing page.</p>
      <div class="mt-10 grid gap-5 md:grid-cols-2">{feature_cards}</div>
    </section>
    <section id="pricing" class="border-t border-white/10 py-20">
      <h2 class="text-3xl font-semibold">Simple pricing</h2>
      <p class="mt-3 text-slate-400">Start free. Upgrade when you need protocol tracking and exports.</p>
      <div class="mt-10 grid gap-6 md:grid-cols-2 max-w-3xl">${{pricingCards()}}</div>
    </section>
    <section class="border-t border-white/10 py-16 text-center">
      <h2 class="text-2xl font-semibold">Ready to log your first entry?</h2>
      <button onclick="showAuth('signup')" class="mt-6 rounded-full accent-bg px-8 py-3 font-semibold text-black">Create free account</button>
    </section>
  </main>
  <footer class="mx-auto max-w-6xl border-t border-white/10 px-6 py-10 text-sm text-slate-500">Built autonomously by IdeaForge · ${{CFG.product}}</footer>
  `);
}}

function showAuth(mode) {{
  const isSignup = mode === "signup";
  root.insertAdjacentHTML("beforeend", h(`
  <div id="authModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
    <div class="w-full max-w-md rounded-2xl border border-white/10 bg-[#12141a] p-7">
      <div class="flex items-center justify-between"><h2 class="text-xl font-semibold">${{isSignup ? "Create your account" : "Welcome back"}}</h2>
        <button onclick="closeAuth()" class="text-slate-400 hover:text-white">✕</button></div>
      <p class="mt-1 text-sm text-slate-400">${{isSignup ? "Start tracking in seconds." : "Sign in to your workspace."}}</p>
      <div class="mt-5 space-y-3">
        ${{isSignup ? `<input id="f-name" placeholder="Name" class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none focus:border-white/30" />` : ""}}
        <input id="f-email" type="email" placeholder="you@email.com" class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none focus:border-white/30" />
        <input id="f-pass" type="password" placeholder="Password" class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none focus:border-white/30" />
        <p id="auth-err" class="hidden text-sm text-red-400"></p>
        <button id="auth-btn" onclick="doAuth(${{isSignup}})" class="w-full rounded-xl accent-bg px-4 py-3 font-semibold text-black">${{isSignup ? "Create account" : "Sign in"}}</button>
        <button onclick="closeAuth();showAuth('${{isSignup ? "login" : "signup"}}')" class="w-full text-center text-sm text-slate-400 hover:text-white">${{isSignup ? "Have an account? Sign in" : "New here? Create an account"}}</button>
        <p class="text-center text-xs text-slate-500">Demo: demo@demo.com / demo123</p>
      </div>
    </div>
  </div>`));
}}
function closeAuth() {{ const m = document.getElementById("authModal"); if (m) m.remove(); }}
async function doAuth(isSignup) {{
  const err = document.getElementById("auth-err");
  const btn = document.getElementById("auth-btn");
  const email = (document.getElementById("f-email").value || "").trim();
  const pass = document.getElementById("f-pass").value || "";
  const name = isSignup ? (document.getElementById("f-name").value || "").trim() : "";
  if (!email || !pass) {{ err.textContent = "Email and password required."; err.classList.remove("hidden"); return; }}
  btn.disabled = true; btn.textContent = "…";
  try {{
    if (isSignup) await signup(name, email, pass); else await login(email, pass);
    closeAuth(); dashboard();
  }} catch (e) {{ err.textContent = e.message || "Something went wrong."; err.classList.remove("hidden"); btn.disabled = false; btn.textContent = isSignup ? "Create account" : "Sign in"; }}
}}

async function dashboard() {{
  root.innerHTML = h(`
  <header class="border-b border-white/10">
    <div class="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
      <div class="flex items-center gap-2"><div class="h-6 w-6 rounded-md accent-bg"></div><span class="font-semibold">${{CFG.product}}</span></div>
      <div class="flex items-center gap-3 text-sm"><span class="text-slate-400">${{LS.email}}</span>
        <button onclick="logout()" class="rounded-full border border-white/15 px-4 py-1.5 hover:bg-white/5">Log out</button></div>
    </div>
  </header>
  <main class="mx-auto max-w-5xl px-6 py-8">
    <div id="stats" class="grid grid-cols-3 gap-4"></div>
    <div class="mt-8 grid gap-6 md:grid-cols-[360px_1fr]">
      <div class="rounded-2xl border border-white/10 bg-white/5 p-5">
        <h3 class="font-semibold">Log an entry</h3>
        <div class="mt-4 space-y-3">
          <input id="i-name" placeholder="Name (e.g. Vitamin D3)" class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm outline-none focus:border-white/30" />
          <input id="i-amount" placeholder="Amount / dose (e.g. 125 mg)" class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm outline-none focus:border-white/30" />
          <div>
            <label class="text-xs text-slate-400">Score: <span id="score-val">7</span>/10</label>
            <input id="i-score" type="range" min="1" max="10" value="7" oninput="document.getElementById('score-val').textContent=this.value" class="w-full accent-emerald-500" />
          </div>
          <textarea id="i-notes" rows="2" placeholder="Notes (optional)" class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm outline-none focus:border-white/30"></textarea>
          <button id="add-btn" onclick="submitItem()" class="w-full rounded-xl accent-bg px-4 py-2.5 font-semibold text-black">Add entry</button>
        </div>
      </div>
      <div>
        <h3 class="font-semibold">Your log</h3>
        <div id="list" class="mt-4 space-y-3"><p class="text-sm text-slate-500">Loading…</p></div>
      </div>
    </div>
  </main>`);
  await renderList();
}}

function fmtScore(s) {{ const n = Number(s); return isNaN(n) ? "—" : n.toFixed(0); }}
async function renderList() {{
  const list = document.getElementById("list");
  const stats = document.getElementById("stats");
  let items = [];
  try {{ items = await getItems(); }} catch (e) {{ list.innerHTML = `<p class="text-sm text-red-400">${{e.message}}</p>`; return; }}
  const scores = items.map(i => Number(i.score)).filter(n => !isNaN(n));
  const avg = scores.length ? (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1) : "—";
  stats.innerHTML = `
    <div class="rounded-2xl border border-white/10 bg-white/5 p-5"><div class="text-3xl font-semibold">${{items.length}}</div><div class="mt-1 text-sm text-slate-400">entries logged</div></div>
    <div class="rounded-2xl border border-white/10 bg-white/5 p-5"><div class="text-3xl font-semibold accent-text">${{avg}}</div><div class="mt-1 text-sm text-slate-400">avg score</div></div>
    <div class="rounded-2xl border border-white/10 bg-white/5 p-5"><div class="text-3xl font-semibold">${{new Set(items.map(i=>i.name)).size}}</div><div class="mt-1 text-sm text-slate-400">unique items</div></div>`;
  if (!items.length) {{ list.innerHTML = `<div class="rounded-2xl border border-dashed border-white/10 p-8 text-center text-sm text-slate-500">No entries yet — log your first one.</div>`; return; }}
  list.innerHTML = items.map(i => `
    <div class="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
      <div><div class="font-medium">${{escapeHtml(i.name || "Entry")}}</div>
        <div class="text-sm text-slate-400">${{escapeHtml(i.amount || "")}} ${{i.notes ? "· " + escapeHtml(i.notes) : ""}}</div></div>
      <div class="flex items-center gap-4">
        <div class="text-right"><div class="text-lg font-semibold accent-text">${{fmtScore(i.score)}}</div><div class="text-xs text-slate-500">score</div></div>
        <button onclick="removeItem('${{i.id}}')" class="text-slate-500 hover:text-red-400">✕</button>
      </div>
    </div>`).join("");
}}
async function submitItem() {{
  const btn = document.getElementById("add-btn");
  const name = (document.getElementById("i-name").value || "").trim();
  if (!name) {{ document.getElementById("i-name").focus(); return; }}
  const rec = {{
    name,
    amount: (document.getElementById("i-amount").value || "").trim(),
    score: Number(document.getElementById("i-score").value),
    notes: (document.getElementById("i-notes").value || "").trim(),
  }};
  btn.disabled = true; btn.textContent = "…";
  try {{ await addItem(rec); document.getElementById("i-name").value=""; document.getElementById("i-amount").value=""; document.getElementById("i-notes").value=""; await renderList(); }}
  catch (e) {{ alert(e.message); }}
  finally {{ btn.disabled = false; btn.textContent = "Add entry"; }}
}}
async function removeItem(id) {{ await delItem(id); await renderList(); }}
function logout() {{ LS.t = ""; LS.email = ""; landing(); }}
function escapeHtml(s) {{ return String(s == null ? "" : s).replace(/[&<>\"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c])); }}

// ---- Boot ----
(function () {{
  const params = new URLSearchParams(location.search);
  if (LS.t) {{ dashboard(); }}
  else {{ landing(); if (params.get("checkout") === "success") showAuth("signup"); }}
}})();
</script>
</body>
</html>"""
