from tools.vercel_tools import allocate_project_name, resolve_v0_production_url
from tools.v0_tools import (
    _chat_matches_product,
    _extract_result,
    _version_completed,
    deploy_url_matches_product,
)


def test_extract_result_skips_pending_preview():
    """A pending v0 version exposes a demoUrl but isn't a real app yet."""
    data = {
        "id": "chat_1",
        "latestVersion": {
            "id": "ver_1",
            "status": "pending",
            "demoUrl": "https://demo-abc.vusercontent.net",
            "files": [],
        },
    }
    assert _extract_result(data) == {}


def test_extract_result_accepts_completed_version():
    data = {
        "id": "chat_1",
        "latestVersion": {
            "id": "ver_1",
            "status": "completed",
            "demoUrl": "https://demo-abc.vusercontent.net",
            "files": [],
        },
    }
    result = _extract_result(data)
    assert result["chat_id"] == "chat_1"
    assert result["version_id"] == "ver_1"


def test_version_completed_status_vocabulary():
    assert _version_completed({"status": "completed"}, {})
    assert not _version_completed({"status": "pending"}, {})
    # Missing status stays permissive (backward compatible).
    assert _version_completed({}, {})


def test_resolve_v0_production_url_from_inspector():
    deployment = {
        "webUrl": "https://v0-lotready-saas-i352uj1d3-ideaforge-projects.vercel.app",
        "inspectorUrl": "https://vercel.com/ideaforge-projects/v0-lotready-saas-app/EVpmCgUB7v49RkNa3jFYoYomPxww",
    }
    assert resolve_v0_production_url(deployment) == "https://v0-lotready-saas-app.vercel.app"


def test_resolve_v0_production_url_keeps_simple_alias():
    deployment = {"webUrl": "https://my-product.vercel.app"}
    assert resolve_v0_production_url(deployment) == "https://my-product.vercel.app"


def test_deploy_url_matches_product_rejects_cross_product():
    url = "https://v0-lotready-saas-22kksy9gt-ideaforge-projects.vercel.app"
    assert not deploy_url_matches_product(url, "BioStack")
    assert deploy_url_matches_product(url, "LotReady")


def test_chat_matches_product_by_title():
    chat = {"title": "BioStack — biohacking tracker", "name": "v0 chat"}
    assert _chat_matches_product(chat, "BioStack")
    assert not _chat_matches_product(chat, "LotReady")


def test_allocate_project_name_prefers_session_hash(monkeypatch):
    monkeypatch.setattr(
        "tools.vercel_tools.project_name_taken",
        lambda name: name == "if-taken-project",
    )
    name = allocate_project_name(
        "7801a2be-a36e-43e7-a154-51116fd2bb60",
        product_name="BioStack",
        preferred="if-taken-project",
    )
    assert name.startswith("if-7801a2be")
    assert name != "if-taken-project"


def test_allocate_project_name_adds_suffix_when_taken(monkeypatch):
    sid = "abc12345-0000-0000-0000-000000000000"
    primary = allocate_project_name(sid)
    taken = {primary}

    monkeypatch.setattr("tools.vercel_tools.project_name_taken", lambda name: name in taken)
    name = allocate_project_name(sid)
    assert name == f"{primary}-2"
