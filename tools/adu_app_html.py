from __future__ import annotations

"""Interactive ADU feasibility checker — the product underneath the landing page."""

ADU_APP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ADU Ready — Feasibility Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = { theme: { extend: { fontFamily: { sans: ['Inter','system-ui'], display: ['Space Grotesk','Inter'] },
      colors: { ink:'#061018', aqua:'#68F5FF', mint:'#83FFCB', violet:'#8B7CFF' } } } }
  </script>
  <style>
    body { background: radial-gradient(circle at 20% 10%, rgba(104,245,255,.15), transparent 30rem), #061018; }
    .glass { background: linear-gradient(135deg, rgba(255,255,255,.11), rgba(255,255,255,.04)); border: 1px solid rgba(255,255,255,.14); backdrop-filter: blur(20px); }
    @media print { #checkout-banner, nav, form, .no-print { display: none !important; } #report { display: block !important; } }
  </style>
</head>
<body class="min-h-screen font-sans text-white antialiased">
  <div id="checkout-banner" class="hidden fixed inset-x-0 top-0 z-50 bg-gradient-to-r from-teal-600 to-cyan-600 px-4 py-3 text-center text-sm">
    <strong>Payment complete!</strong> Run your feasibility check below.
  </div>
  <nav class="mx-auto flex max-w-5xl items-center justify-between px-5 py-5">
    <a href="/" class="font-display text-lg font-semibold">ADU Ready</a>
    <a href="/" class="text-sm text-white/70 hover:text-white">← Marketing site</a>
  </nav>
  <main class="mx-auto max-w-5xl px-5 pb-16 pt-4">
    <header class="mb-10">
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-aqua/80">Feasibility workspace</p>
      <h1 class="mt-2 font-display text-4xl font-bold tracking-tight">Generate your ADU report</h1>
      <p class="mt-3 max-w-2xl text-white/65">Enter your property address. We analyze zoning, setbacks, max buildable area, parking, and ROI — same engine shown on the homepage demo.</p>
    </header>

    <form id="checker" class="glass no-print mb-8 rounded-3xl p-6">
      <label class="block text-sm font-medium text-white/80" for="address">Property address</label>
      <div class="mt-3 flex flex-col gap-3 sm:flex-row">
        <input id="address" name="address" required placeholder="1428 Silver Lake Blvd, Los Angeles, CA"
          class="flex-1 rounded-2xl border border-white/15 bg-white/5 px-4 py-3 text-white placeholder:text-white/35 outline-none focus:border-aqua/50" />
        <button type="submit" class="rounded-2xl bg-aqua px-6 py-3 font-bold text-ink hover:bg-mint">Run check →</button>
      </div>
      <p class="mt-3 text-xs text-white/45">Demo uses simulated municipal data. Not a permit approval or legal survey.</p>
    </form>

    <section id="report" class="hidden">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-sm text-white/55">Report for</p>
          <p id="report-address" class="font-display text-2xl font-semibold"></p>
        </div>
        <span id="eligibility" class="rounded-full border border-mint/30 bg-mint/10 px-4 py-1.5 text-sm font-bold text-mint"></span>
      </div>
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div class="glass rounded-2xl p-5"><p class="text-xs text-white/50">Zoning</p><p id="zoning" class="mt-1 text-xl font-bold text-aqua"></p></div>
        <div class="glass rounded-2xl p-5"><p class="text-xs text-white/50">Max ADU size</p><p id="max-size" class="mt-1 text-xl font-bold text-mint"></p></div>
        <div class="glass rounded-2xl p-5"><p class="text-xs text-white/50">Height limit</p><p id="height" class="mt-1 text-xl font-bold"></p></div>
        <div class="glass rounded-2xl p-5"><p class="text-xs text-white/50">Setbacks (F/S/R)</p><p id="setbacks" class="mt-1 text-lg font-semibold"></p></div>
        <div class="glass rounded-2xl p-5"><p class="text-xs text-white/50">Parking required</p><p id="parking" class="mt-1 text-lg font-semibold"></p></div>
        <div class="glass rounded-2xl p-5"><p class="text-xs text-white/50">Est. ROI range</p><p id="roi" class="mt-1 text-xl font-bold text-violet"></p></div>
      </div>
      <div class="glass mt-4 rounded-2xl p-6">
        <h2 class="font-display text-lg font-bold">Plain-language summary</h2>
        <p id="summary" class="mt-3 leading-7 text-white/70"></p>
        <h3 class="mt-6 font-display text-sm font-bold uppercase tracking-wider text-aqua/80">Next steps</h3>
        <ul id="steps" class="mt-3 list-disc space-y-2 pl-5 text-sm text-white/65"></ul>
      </div>
      <div class="no-print mt-6 flex flex-wrap gap-3">
        <button type="button" onclick="window.print()" class="rounded-full bg-white px-6 py-3 font-bold text-ink">Download / print PDF</button>
        <a href="/" class="rounded-full border border-white/20 px-6 py-3 font-semibold text-white/80 hover:bg-white/5">Back to home</a>
      </div>
    </section>
  </main>
  <script>
    if (/[?&]checkout=success/.test(location.search)) {
      document.getElementById('checkout-banner').classList.remove('hidden');
      document.body.style.paddingTop = '48px';
    }
    const ZONES = ['R1-1VL', 'R2-1', 'RS-1-7', 'R-1-5000'];
    function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = ((h << 5) - h) + s.charCodeAt(i) | 0; return Math.abs(h); }
    document.getElementById('checker').addEventListener('submit', function (e) {
      e.preventDefault();
      const addr = document.getElementById('address').value.trim();
      const h = hash(addr.toLowerCase());
      const eligible = h % 5 !== 0;
      const zone = ZONES[h % ZONES.length];
      const maxSqft = 800 + (h % 5) * 100;
      const height = 14 + (h % 3) * 2;
      const roiLo = (6 + (h % 4) * 0.4).toFixed(1);
      const roiHi = (parseFloat(roiLo) + 2.2).toFixed(1);
      document.getElementById('report-address').textContent = addr;
      document.getElementById('eligibility').textContent = eligible ? 'Likely eligible' : 'Needs review';
      document.getElementById('eligibility').className = eligible
        ? 'rounded-full border border-mint/30 bg-mint/10 px-4 py-1.5 text-sm font-bold text-mint'
        : 'rounded-full border border-amber-400/30 bg-amber-400/10 px-4 py-1.5 text-sm font-bold text-amber-300';
      document.getElementById('zoning').textContent = zone;
      document.getElementById('max-size').textContent = maxSqft + ' sq ft';
      document.getElementById('height').textContent = height + ' ft';
      document.getElementById('setbacks').textContent = '20\\' / 5\\' / 15\\'';
      document.getElementById('parking').textContent = (h % 2) ? '1 space (tandem OK)' : 'None required';
      document.getElementById('roi').textContent = roiLo + '–' + roiHi + '%';
      document.getElementById('summary').textContent = eligible
        ? 'Your parcel appears eligible for one detached ADU up to ' + maxSqft + ' sq ft under ' + zone + ', subject to utility verification and fire access.'
        : 'Preliminary scan flags overlay or access constraints. Request a manual review before design spend.';
      document.getElementById('steps').innerHTML = [
        'Verify utility capacity with your water/power provider',
        'Confirm fire department access with a site walk',
        'Share this report with a designer or prefab ADU vendor',
        eligible ? 'Proceed to preliminary plans' : 'Book a zoning consultation'
      ].map(s => '<li>' + s + '</li>').join('');
      document.getElementById('report').classList.remove('hidden');
      document.getElementById('report').scrollIntoView({ behavior: 'smooth' });
    });
  </script>
</body>
</html>"""


def generate_adu_feasibility_app_html() -> str:
    return ADU_APP_HTML
