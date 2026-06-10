import os

import pytest

from tools.aura_build_client import (
    aura_share_url,
    fetch_shared_code,
    prepare_reference_excerpt,
    resolve_template_slug,
)
from tools.aura_portfolio import list_aura_templates, resolve_ui_builder, select_aura_template


def test_portfolio_entries_have_aura_slugs():
    templates = list_aura_templates()
    assert all(t.get("aura_slug") for t in templates)
    assert all(str(t.get("reference_url", "")).startswith("https://www.aura.build/share/") for t in templates)


def test_resolve_ui_builder_defaults_to_aura_even_with_v0_key():
    import os

    old_pref = os.environ.get("UI_BUILDER")
    old_v0 = os.environ.get("V0_API_KEY")
    os.environ["UI_BUILDER"] = "aura"
    os.environ["V0_API_KEY"] = "test-key"
    try:
        assert resolve_ui_builder({"complexity": "standard"}) == "aura_html"
    finally:
        if old_pref is None:
            os.environ.pop("UI_BUILDER", None)
        else:
            os.environ["UI_BUILDER"] = old_pref
        if old_v0 is None:
            os.environ.pop("V0_API_KEY", None)
        else:
            os.environ["V0_API_KEY"] = old_v0


@pytest.mark.skipif(
    os.getenv("AURA_INTEGRATION_TEST") != "1",
    reason="Set AURA_INTEGRATION_TEST=1 to hit aura.build Supabase",
)
def test_fetch_public_aura_template():
    template = select_aura_template(product_name="AgentOps", niche="AI SaaS", icp="developers")
    slug = resolve_template_slug(template)
    row = fetch_shared_code(slug)
    assert row["code"]
    assert "<html" in row["code"].lower()
    assert aura_share_url(slug).startswith("https://www.aura.build/share/")


def test_prepare_reference_excerpt_truncates_large_html():
    html = "<html><head><title>x</title></head><body>" + ("x" * 30_000) + "</body></html>"
    excerpt = prepare_reference_excerpt(html, max_chars=1000)
    assert len(excerpt) <= 1100
    assert "<html" in excerpt.lower()
