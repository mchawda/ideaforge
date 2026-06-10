from tools.aura_portfolio import list_aura_templates, resolve_ui_builder, select_aura_template


def test_portfolio_has_expanded_catalog():
    templates = list_aura_templates()
    assert len(templates) >= 20


def test_selects_ai_template_for_ai_product():
    template = select_aura_template(
        product_name="AgentOps",
        niche="AI developer tools",
        icp="ML engineers",
        features=["agent monitoring", "trace replay"],
    )
    assert template["id"] in {
        "lumina-ai",
        "aura-assistant",
        "enterprise-infra",
        "verdant-saas",
        "nexus-ai-consulting",
    }


def test_resolve_ui_builder_aura_is_default():
    import os

    old_pref = os.environ.get("UI_BUILDER")
    old_v0 = os.environ.get("V0_API_KEY")
    os.environ["UI_BUILDER"] = "aura"
    os.environ["V0_API_KEY"] = "present"
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


def test_resolve_ui_builder_starter_uses_aura_when_forced():
    import os

    old_pref = os.environ.get("UI_BUILDER")
    old_v0 = os.environ.get("V0_API_KEY")
    os.environ["UI_BUILDER"] = "aura"
    os.environ["V0_API_KEY"] = "present"
    try:
        assert resolve_ui_builder({"complexity": "starter"}) == "aura_html"
    finally:
        if old_pref is None:
            os.environ.pop("UI_BUILDER", None)
        else:
            os.environ["UI_BUILDER"] = old_pref
        if old_v0 is None:
            os.environ.pop("V0_API_KEY", None)
        else:
            os.environ["V0_API_KEY"] = old_v0


def test_resolve_ui_builder_defaults_to_v0_when_key_present():
    import os

    old_pref = os.environ.get("UI_BUILDER")
    old_v0 = os.environ.get("V0_API_KEY")
    os.environ.pop("UI_BUILDER", None)
    os.environ["V0_API_KEY"] = "present"
    try:
        assert resolve_ui_builder({"complexity": "standard"}) == "v0"
    finally:
        if old_pref is None:
            os.environ.pop("UI_BUILDER", None)
        else:
            os.environ["UI_BUILDER"] = old_pref
        if old_v0 is None:
            os.environ.pop("V0_API_KEY", None)
        else:
            os.environ["V0_API_KEY"] = old_v0
