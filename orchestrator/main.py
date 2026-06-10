from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tools.aura_portfolio import list_aura_templates
from orchestrator.pipeline import (
    auto_resume_interrupted,
    create_session,
    get_session,
    hydrate_sessions,
    is_resumable,
    resume_session,
    run_after_approval,
    run_until_approval,
)
from orchestrator.api_view import public_session_view
from orchestrator.stage_log import error, info, setup_logging, warning
from orchestrator import store
from tools.aws_tools import refresh_hint, validate_credentials

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
setup_logging()

app = FastAPI(title="IdeaForge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://idea-forge-eta-six.vercel.app",
        os.getenv("WEB_ORIGIN", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    user_input: str = Field(min_length=3)
    input_mode: str = Field(default="idea")
    ideabrowser_url: str | None = None


class ApprovalRequest(BaseModel):
    approved: bool
    feedback: str = ""


@app.on_event("startup")
def on_startup() -> None:
    store.init_db()
    aws = validate_credentials()
    if aws.get("ok"):
        info(None, "aws", "credentials OK", account=aws.get("account"), region=aws.get("region"))
    else:
        warning(None, "aws", "credentials invalid — builds will skip AWS", hint=refresh_hint(aws.get("error", ""))[:200])
    hydrated = hydrate_sessions()
    resumed = auto_resume_interrupted()
    from tools.aura_portfolio import resolve_ui_builder

    has_v0 = bool(os.getenv("V0_API_KEY", "").strip())
    info(
        None,
        "api",
        "builder config",
        ui_builder_env=os.getenv("UI_BUILDER") or ("v0" if has_v0 else "aura"),
        resolved=resolve_ui_builder({}),
        has_v0_key=has_v0,
    )
    info(None, "api", "startup complete", hydrated=hydrated, auto_resumed=resumed)


@app.get("/health")
def health() -> dict[str, str | bool]:
    aws = validate_credentials()
    return {
        "status": "ok",
        "aws_ok": bool(aws.get("ok")),
        "aws_hint": refresh_hint(aws.get("error", "")) if not aws.get("ok") else "",
    }


@app.post("/admin/deploy-web")
def deploy_web_panel() -> dict:
    from tools.vercel_tools import deploy_control_panel

    try:
        result = deploy_control_panel()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        error(None, "api", "deploy-web failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@app.get("/aura/templates")
def aura_templates() -> dict:
    return {"templates": list_aura_templates(), "source": "https://www.aura.build/"}


@app.post("/session/start")
def start_session(payload: StartRequest, background: BackgroundTasks) -> dict:
    mode = payload.input_mode if payload.input_mode in {"ideabrowser", "idea"} else "idea"
    info(None, "api", "POST /session/start", input_mode=mode)
    state = create_session(
        user_input=payload.user_input,
        input_mode=mode,  # type: ignore[arg-type]
        ideabrowser_url=payload.ideabrowser_url,
    )
    background.add_task(run_until_approval, state["session_id"])
    info(state["session_id"], "api", "session queued for pre-approval pipeline")
    return {"session_id": state["session_id"], "status": state["status"]}


@app.get("/sessions")
def list_sessions() -> dict:
    return {"sessions": store.list_summaries()}


@app.get("/session/{session_id}")
def session_status(session_id: str) -> dict:
    state = get_session(session_id)
    if not state:
        warning(session_id, "api", "GET /session — not found")
        raise HTTPException(status_code=404, detail="Session not found")
    slim = public_session_view(state)
    return {**slim, "resumable": is_resumable(state)}


@app.post("/session/{session_id}/resume")
def resume_build(session_id: str, background: BackgroundTasks) -> dict:
    state = get_session(session_id)
    if not state:
        warning(session_id, "api", "POST /resume — session not found")
        raise HTTPException(status_code=404, detail="Session not found")
    if not is_resumable(state):
        raise HTTPException(status_code=400, detail="Session is not resumable")

    background.add_task(resume_session, session_id)
    info(session_id, "api", "resume queued", status=state.get("status"))
    return {"session_id": session_id, "status": "resuming"}


@app.post("/session/{session_id}/approve")
def approve_session(
    session_id: str,
    payload: ApprovalRequest,
    background: BackgroundTasks,
) -> dict:
    state = get_session(session_id)
    if not state:
        warning(session_id, "api", "POST /approve — session not found")
        raise HTTPException(status_code=404, detail="Session not found")
    if state.get("status") != "awaiting_approval":
        warning(
            session_id,
            "api",
            "POST /approve — invalid status",
            status=state.get("status"),
        )
        raise HTTPException(status_code=400, detail="Session is not awaiting approval")

    background.add_task(
        run_after_approval,
        session_id,
        approved=payload.approved,
        feedback=payload.feedback,
    )
    info(session_id, "api", "approval queued for post-approval pipeline", approved=payload.approved)
    return {"session_id": session_id, "status": "processing"}
