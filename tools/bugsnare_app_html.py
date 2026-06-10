from __future__ import annotations

"""Interactive BugSnare API scanner — the product underneath the landing page."""

BUGSNARE_APP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BugSnare — API Scan Console</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Geist:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background: #000; color: #f5f5f5; font-family: Geist, system-ui, sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .glass { background: rgba(255,255,255,.04); border: 1px solid rgba(255,171,0,.15); }
    .glow { box-shadow: 0 0 40px rgba(255,109,0,.12); }
    @media print { nav, form, .no-print { display: none !important; } }
  </style>
</head>
<body class="min-h-screen">
  <div id="checkout-banner" class="hidden border-b border-[#FFAB00]/30 bg-[#FF6D00]/20 px-4 py-2.5 text-center text-sm text-[#FFAB00]">
    <strong>Access granted.</strong> Run your first API scan below.
  </div>
  <nav class="flex items-center justify-between border-b border-[#FFAB00]/10 bg-black/80 px-5 py-4 backdrop-blur-md">
    <a href="/" class="mono text-sm font-bold tracking-widest text-[#FFAB00]">BUGSNARE</a>
    <a href="/" class="text-sm text-white/50 hover:text-white">← Site</a>
  </nav>

  <main class="mx-auto max-w-6xl px-5 py-10">
    <header class="mb-8">
      <p class="mono text-xs uppercase tracking-[0.3em] text-[#FFAB00]/80">Scan console v4.1</p>
      <h1 class="mt-2 text-3xl font-bold tracking-tight">API bug detection workspace</h1>
      <p class="mt-2 max-w-2xl text-white/55">Crawl endpoints, classify failures, and surface regressions — the operational layer behind the marketing site.</p>
    </header>

    <form id="scan-form" class="glass no-print glow mb-8 rounded-2xl p-6">
      <div class="grid gap-4 md:grid-cols-2">
        <div>
          <label class="text-xs font-semibold uppercase tracking-wider text-white/50" for="base">API base URL</label>
          <input id="base" required placeholder="https://api.example.com/v1"
            class="mono mt-2 w-full rounded-xl border border-white/10 bg-black/60 px-4 py-3 text-sm outline-none focus:border-[#FFAB00]/50" />
        </div>
        <div>
          <label class="text-xs font-semibold uppercase tracking-wider text-white/50" for="spec">OpenAPI spec (optional)</label>
          <input id="spec" placeholder="https://api.example.com/openapi.json"
            class="mono mt-2 w-full rounded-xl border border-white/10 bg-black/60 px-4 py-3 text-sm outline-none focus:border-[#FFAB00]/50" />
        </div>
      </div>
      <div class="mt-5 flex flex-wrap gap-3">
        <button type="submit" class="rounded-full bg-[#FF6D00] px-8 py-3 text-sm font-bold text-black hover:bg-[#FFAB00]">Initialize scan →</button>
        <button type="button" id="demo-scan" class="rounded-full border border-[#FFAB00]/50 px-8 py-3 text-sm font-bold text-[#FFAB00] hover:bg-[#FFAB00]/10">Run demo scan</button>
      </div>
      <p class="mt-3 text-xs text-white/40">Demo mode uses simulated findings — any URL works. Try the demo button or paste an example below.</p>
      <div class="mt-3 flex flex-wrap gap-2 text-xs">
        <button type="button" class="demo-url rounded-full border border-white/10 px-3 py-1 text-white/55 hover:border-[#FFAB00]/40 hover:text-[#FFAB00]" data-base="https://api.bugsnare-demo.dev/v1" data-spec="https://api.bugsnare-demo.dev/openapi.json">BugSnare sample API</button>
        <button type="button" class="demo-url rounded-full border border-white/10 px-3 py-1 text-white/55 hover:border-[#FFAB00]/40 hover:text-[#FFAB00]" data-base="https://petstore.swagger.io/v2" data-spec="https://petstore.swagger.io/v2/swagger.json">Petstore (Swagger)</button>
        <button type="button" class="demo-url rounded-full border border-white/10 px-3 py-1 text-white/55 hover:border-[#FFAB00]/40 hover:text-[#FFAB00]" data-base="https://jsonplaceholder.typicode.com" data-spec="">JSONPlaceholder</button>
      </div>
    </form>

    <section id="results" class="hidden">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-sm text-white/50">Target</p>
          <p id="target" class="mono text-lg text-[#FFAB00]"></p>
        </div>
        <div class="flex gap-4 text-center">
          <div><p id="stat-endpoints" class="text-2xl font-bold">0</p><p class="text-xs text-white/45">endpoints</p></div>
          <div><p id="stat-bugs" class="text-2xl font-bold text-red-400">0</p><p class="text-xs text-white/45">bugs</p></div>
          <div><p id="stat-pass" class="text-2xl font-bold text-emerald-400">0</p><p class="text-xs text-white/45">clean</p></div>
        </div>
      </div>
      <div class="glass overflow-hidden rounded-2xl">
        <table class="w-full text-left text-sm">
          <thead class="mono border-b border-white/10 bg-white/[0.03] text-xs uppercase tracking-wider text-white/45">
            <tr><th class="px-4 py-3">Endpoint</th><th class="px-4 py-3">Status</th><th class="px-4 py-3">Severity</th><th class="px-4 py-3">Classification</th></tr>
          </thead>
          <tbody id="rows" class="mono divide-y divide-white/5"></tbody>
        </table>
      </div>
      <div class="no-print mt-6 flex gap-3">
        <button type="button" onclick="window.print()" class="rounded-full border border-[#FFAB00]/40 px-6 py-2.5 text-sm font-semibold text-[#FFAB00]">Export report</button>
        <button type="button" id="rescan" class="rounded-full bg-white/10 px-6 py-2.5 text-sm font-semibold hover:bg-white/15">Rescan</button>
      </div>
    </section>
  </main>

  <script>
    if (/[?&]checkout=success/.test(location.search)) {
      document.getElementById('checkout-banner').classList.remove('hidden');
    }
    function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = ((h << 5) - h) + s.charCodeAt(i) | 0; return Math.abs(h); }
    const FINDINGS = [
      { method: 'GET', path: '/users/{id}', status: 403, severity: 'HIGH', cls: 'Auth / access restriction' },
      { method: 'POST', path: '/checkout', status: 500, severity: 'CRITICAL', cls: 'Regression — schema drift' },
      { method: 'GET', path: '/health', status: 200, severity: '—', cls: 'OK' },
      { method: 'PATCH', path: '/orders/{id}', status: 429, severity: 'MED', cls: 'Rate limit misconfig' },
      { method: 'GET', path: '/search', status: 200, severity: 'LOW', cls: 'Response mutation vs baseline' },
      { method: 'DELETE', path: '/sessions', status: 401, severity: 'HIGH', cls: 'Token scope mismatch' },
    ];
    function runScan(base) {
      const h = hash(base);
      const rows = FINDINGS.map((f, i) => ({ ...f, status: f.status === 200 && (h + i) % 4 === 0 ? 502 : f.status }));
      const bugs = rows.filter(r => r.severity !== '—' && r.severity !== 'LOW');
      document.getElementById('target').textContent = base;
      document.getElementById('stat-endpoints').textContent = rows.length;
      document.getElementById('stat-bugs').textContent = bugs.length;
      document.getElementById('stat-pass').textContent = rows.length - bugs.length;
      document.getElementById('rows').innerHTML = rows.map(r => {
        const sevColor = r.severity === 'CRITICAL' ? 'text-red-400' : r.severity === 'HIGH' ? 'text-orange-400' : r.severity === 'MED' ? 'text-yellow-400' : r.severity === 'LOW' ? 'text-amber-200' : 'text-emerald-400';
        return '<tr class="hover:bg-white/[0.02]"><td class="px-4 py-3"><span class="text-[#FFAB00]">' + r.method + '</span> ' + r.path + '</td><td class="px-4 py-3">' + r.status + '</td><td class="px-4 py-3 ' + sevColor + '">' + r.severity + '</td><td class="px-4 py-3 text-white/65">' + r.cls + '</td></tr>';
      }).join('');
      document.getElementById('results').classList.remove('hidden');
      document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
    }
    const DEMO_BASE = 'https://api.bugsnare-demo.dev/v1';
    const DEMO_SPEC = 'https://api.bugsnare-demo.dev/openapi.json';
    document.getElementById('base').value = DEMO_BASE;
    document.getElementById('spec').value = DEMO_SPEC;
    document.getElementById('scan-form').addEventListener('submit', e => { e.preventDefault(); runScan(document.getElementById('base').value.trim()); });
    document.getElementById('rescan').addEventListener('click', () => document.getElementById('scan-form').requestSubmit());
    document.getElementById('demo-scan').addEventListener('click', () => {
      document.getElementById('base').value = DEMO_BASE;
      document.getElementById('spec').value = DEMO_SPEC;
      document.getElementById('scan-form').requestSubmit();
    });
    document.querySelectorAll('.demo-url').forEach(btn => btn.addEventListener('click', () => {
      document.getElementById('base').value = btn.dataset.base || '';
      document.getElementById('spec').value = btn.dataset.spec || '';
      document.getElementById('scan-form').requestSubmit();
    }));
  </script>
</body>
</html>"""


def generate_bugsnare_console_html() -> str:
    return BUGSNARE_APP_HTML
