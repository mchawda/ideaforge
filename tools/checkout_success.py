from __future__ import annotations

import re

CHECKOUT_SUCCESS_SCRIPT = """
<script id="ideaforge-checkout-success">
(function () {
  if (!/[?&]checkout=success(?:&|$)/.test(location.search)) return;
  var origin = location.origin;
  var paths = [
    { label: "Open your product", path: "/app.html" },
    { label: "Open your account", path: "/signup" },
    { label: "Sign in", path: "/login" },
    { label: "Open dashboard", path: "/dashboard" },
  ];
  function probe(i, cb) {
    if (i >= paths.length) return cb(null);
    var item = paths[i];
    fetch(origin + item.path, { method: "GET", redirect: "follow" })
      .then(function (r) {
        if (r.ok) cb(item);
        else probe(i + 1, cb);
      })
      .catch(function () { probe(i + 1, cb); });
  }
  probe(0, function (best) {
    var bar = document.createElement("div");
    bar.setAttribute("role", "status");
    bar.style.cssText =
      "position:fixed;top:0;left:0;right:0;z-index:2147483647;padding:14px 20px;" +
      "background:linear-gradient(90deg,#0d9488,#0891b2);color:#fff;font-family:system-ui,sans-serif;" +
      "display:flex;align-items:center;justify-content:center;gap:14px;flex-wrap:wrap;" +
      "box-shadow:0 4px 24px rgba(0,0,0,.35)";
    var text = document.createElement("span");
    text.innerHTML = "<strong>Payment complete!</strong> You&rsquo;re ready to use the product.";
    var btn = document.createElement("a");
    btn.style.cssText =
      "background:#fff;color:#0d9488;padding:10px 22px;border-radius:999px;" +
      "font-weight:700;text-decoration:none;white-space:nowrap";
    if (best) {
      btn.href = origin + best.path + "?from=checkout";
      btn.textContent = best.label + " \\u2192";
    } else {
      btn.href = origin + "/";
      btn.textContent = "Continue to product \\u2192";
    }
    var hint = document.createElement("span");
    hint.style.cssText = "font-size:12px;opacity:.9";
    hint.textContent = "Demo: demo@demo.com / demo123";
    bar.appendChild(text);
    bar.appendChild(btn);
    bar.appendChild(hint);
    document.body.prepend(bar);
    document.body.style.paddingTop = "72px";
  });
})();
</script>
""".strip()

V0_CHECKOUT_SUCCESS_MESSAGE = """CHECKOUT SUCCESS FIX — required on every page.

Add a client component `CheckoutSuccessBanner` and include it in the root `app/layout.tsx`.

When the URL has `?checkout=success`:
- Show a fixed top banner (teal gradient, high z-index)
- Text: "Payment complete! You're ready to use the product."
- Primary button "Open your account" → `/signup` (or `/dashboard` if that exists)
- Secondary link "Sign in" → `/login`
- Small hint: "Demo: demo@demo.com / demo123"

If `/signup` and `/dashboard` do not exist yet, add minimal working routes:
- `/signup` — email/password form, saves to localStorage, redirects to `/dashboard`
- `/login` — accepts demo@demo.com / demo123, redirects to `/dashboard`
- `/dashboard` — simple CRM home with mock data

Do not change the existing marketing design. This is for post-Stripe redirect UX."""


def inject_checkout_success_script(html: str) -> str:
    if "ideaforge-checkout-success" in html:
        return html
    if "</body>" in html:
        return html.replace("</body>", f"{CHECKOUT_SUCCESS_SCRIPT}\n</body>", 1)
    return html + "\n" + CHECKOUT_SUCCESS_SCRIPT
