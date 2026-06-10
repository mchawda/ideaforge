from __future__ import annotations

import os
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Literal

from agents.audit_agent import run_audit
from agents.builder_agent import run_builder
from agents.infra_agent import run_infra
from agents.monetization_agent import run_monetization
from agents.research_agent import run_research
from agents.strategy_agent import run_strategy
from orchestrator.complexity import estimate_after_strategy, estimate_initial
from orchestrator.progress import bind_sessions, report_progress
from orchestrator.stage_log import error, info, stage, warning
from orchestrator.state import AgentState, append_audit, new_session_state, utc_now
from orchestrator import store

_sessions: dict[str, AgentState] = {}
_session_lock = threading.Lock()
_running: set[str] = set()
_v0_running: set[str] = set()
bind_sessions(_sessions)

_PRE_APPROVAL_ACTIVE = {"queued", "researching", "researched", "revising_strategy"}
_POST_APPROVAL_ACTIVE = {
    "building",
    "generating_ui",
    "provisioning_aws",
    "infra_ready",
    "setting_up_stripe",
    "monetized",
    "finalizing",
}


def hydrate_sessions() -> int:
    """Load persisted sessions into memory on API startup."""
    loaded = store.load_all()
    with _session_lock:
        _sessions.update(loaded)
    if loaded:
        info(None, "store", f"hydrated {len(loaded)} session(s) from disk")
    return len(loaded)


def get_session(session_id: str) -> AgentState | None:
    with _session_lock:
        state = _sessions.get(session_id)
    if state:
        return dict(state)
    disk = store.load(session_id)
    if disk:
        with _session_lock:
            _sessions[session_id] = disk
        return dict(disk)
    return None


def _agents_done(state: AgentState) -> set[str]:
    return {entry.get("agent", "") for entry in state.get("audit_log") or [] if entry.get("agent")}


def is_resumable(state: AgentState) -> bool:
    status = state.get("status", "")
    if status == "awaiting_approval":
        return False
    if status in ("complete", "rejected"):
        return state.get("v0_status") in ("pending", "error")
    if status == "complete_with_warnings":
        if state.get("v0_status") in ("pending", "error"):
            return True
        # Paused mid-pipeline (demo prep or crash) — Stripe/AWS/v0 never finished
        if (
            state.get("v0_status") == "skipped"
            and not state.get("final_url")
            and not state.get("vercel_deployment_url")
            and state.get("human_approved")
            and "monetization" not in _agents_done(state)
        ):
            return True
    if status == "error":
        return True
    if status in _PRE_APPROVAL_ACTIVE | _POST_APPROVAL_ACTIVE:
        return True
    if state.get("v0_status") in ("pending", "error") and state.get("human_approved"):
        return True
    return False


def list_resumable_sessions() -> list[str]:
    with _session_lock:
        states = list(_sessions.values())
    return [s["session_id"] for s in states if is_resumable(s)]


def _fast_mode() -> bool:
    return os.getenv("FAST_MODE", "false").strip().lower() in {"1", "true", "yes"}


def create_session(
    *,
    user_input: str,
    input_mode: Literal["ideabrowser", "idea"],
    ideabrowser_url: str | None = None,
) -> AgentState:
    state = new_session_state(
        user_input=user_input,
        input_mode=input_mode,
        ideabrowser_url=ideabrowser_url,
    )
    estimate = estimate_initial(state)
    state = {
        **state,
        "time_estimate": estimate,
        "complexity": estimate["complexity"],
        "v0_status": "pending",
    }
    _save(state)
    info(
        state["session_id"],
        "session",
        "created",
        input_mode=input_mode,
        complexity=estimate["complexity"],
        est_minutes=estimate["total_minutes"],
    )
    report_progress(
        state["session_id"],
        f"{estimate['summary']} — starting research…",
    )
    return state


def _save(state: AgentState) -> AgentState:
    with _session_lock:
        _sessions[state["session_id"]] = state
    store.persist(state)
    return state


def _merge_parallel(base: AgentState, *results: AgentState) -> AgentState:
    merged: AgentState = dict(base)
    base_audit_len = len(base.get("audit_log") or [])
    audits = list(base.get("audit_log") or [])
    for result in results:
        result_audits = result.get("audit_log") or []
        audits.extend(result_audits[base_audit_len:])
        for key, value in result.items():
            if key in ("audit_log", "session_id"):
                continue
            if value not in (None, "", []):
                merged[key] = value  # type: ignore[literal-required]
    merged["audit_log"] = audits
    errors = [
        r.get("error", "")
        for r in results
        if r.get("error") and not str(r.get("error", "")).startswith("AWS skipped:")
    ]
    if errors:
        merged["error"] = "; ".join(errors)[:500]
        warning(base["session_id"], "pipeline", "parallel step errors", errors="; ".join(errors)[:300])
    elif any(r.get("aws_status") == "skipped" for r in results):
        merged.pop("error", None)
    return merged


def _run_step(
    state: AgentState,
    *,
    step: str,
    status: str,
    runner: Callable[[AgentState], AgentState],
) -> AgentState:
    sid = state["session_id"]
    report_progress(sid, step)
    state = _save({**state, "current_step": step, "status": status})
    try:
        with stage(sid, step, status=status):
            return _save(runner(state))
    except Exception as exc:
        error(sid, step, f"step failed (continuing degraded): {exc}", exc_info=True)
        return _save(
            append_audit(
                {**state, "error": str(exc)},
                agent="orchestrator",
                decision=f"{step} failed — continuing with degraded output",
                rationale=str(exc)[:500],
            )
        )


def _spawn_v0(session_id: str) -> None:
    with _session_lock:
        if session_id in _v0_running:
            info(session_id, "v0_background", "already running — skipping duplicate spawn")
            return
        _v0_running.add(session_id)
    threading.Thread(target=_run_v0_background, args=(session_id,), daemon=True).start()


def _run_v0_background(session_id: str) -> None:
    try:
        with stage(session_id, "v0_background"):
            snapshot = get_session(session_id)
            if not snapshot:
                warning(session_id, "v0_background", "session not found — aborting")
                return
            report_progress(session_id, "v0 UI generating in background (Stripe + AWS already shipping)…")
            result = run_builder(snapshot)
            current = get_session(session_id) or snapshot
            merged = _merge_parallel(current, result)
            v0_ready = result.get("status") == "ui_generated"
            merged["v0_status"] = result.get("v0_status") or (
                "ready" if v0_ready else "skipped"
            )
            merged["background_build"] = False
            if current.get("status") in ("complete", "complete_with_warnings"):
                merged["status"] = (
                    "complete"
                    if v0_ready and not merged.get("error")
                    else current["status"]
                )
            if v0_ready and (
                merged.get("vercel_deployment_url")
                or merged.get("final_url")
                or merged.get("v0_preview_url")
            ):
                live = (
                    merged.get("final_url")
                    or merged.get("vercel_deployment_url")
                    or merged.get("v0_preview_url")
                )
                merged["current_step"] = f"Live — {live}"
                if merged.get("status") in ("complete", "complete_with_warnings", "generating_ui"):
                    merged["status"] = "complete" if not merged.get("error") else merged["status"]
                info(session_id, "v0_background", "preview ready", url=merged["vercel_deployment_url"])
                report_progress(session_id, f"Product live — {live}")
                try:
                    from tools.stripe_tools import configure_session_checkout_redirects

                    configure_session_checkout_redirects(merged, product_url=live, session_id=session_id)
                except Exception as exc:
                    warning(session_id, "v0_background", f"stripe redirect setup skipped: {exc}")
            elif merged.get("error"):
                merged["v0_status"] = "error"
                warning(session_id, "v0_background", "v0 failed", error=merged.get("error", "")[:200])
                report_progress(session_id, f"v0 UI: {merged.get('error', 'failed')[:120]}")
            _save(merged)
    except Exception as exc:
        error(session_id, "v0_background", f"background task crashed: {exc}", exc_info=True)
        current = get_session(session_id)
        if current:
            _save(
                {
                    **current,
                    "v0_status": "error",
                    "error": str(exc)[:500],
                }
            )
        report_progress(session_id, f"v0 background task failed: {str(exc)[:120]}")
    finally:
        with _session_lock:
            _v0_running.discard(session_id)


def _finish_post_approval(state: AgentState) -> AgentState:
    session_id = state["session_id"]
    agents = _agents_done(state)
    estimate = state.get("time_estimate") or estimate_after_strategy(state)

    if "infra" not in agents or "monetization" not in agents:
        base = dict(state)

        def _parallel_step(runner: Callable[[AgentState], AgentState], label: str) -> AgentState:
            try:
                return runner(dict(base))
            except Exception as exc:
                warning(session_id, "parallel_deploy", f"{label} failed", error=str(exc)[:200])
                return {**base, "error": f"{label}: {exc}"[:500]}

        with stage(session_id, "parallel_deploy", fast_mode=_fast_mode()):
            with ThreadPoolExecutor(max_workers=2) as pool:
                infra_future = pool.submit(_parallel_step, run_infra, "AWS")
                stripe_future = pool.submit(_parallel_step, run_monetization, "Stripe")
                infra_result = infra_future.result()
                stripe_result = stripe_future.result()
        state = _save(_merge_parallel(state, infra_result, stripe_result))
        report_progress(session_id, "Stripe + AWS ready — finishing audit brief…")

    if "audit" not in _agents_done(state):
        state = _run_step(
            state,
            step="Writing final audit brief…",
            status="finalizing",
            runner=run_audit,
        )

    if not _fast_mode() and state.get("v0_status") not in ("ready",) and "builder" not in _agents_done(state):
        info(session_id, "v0_background", "spawning background thread")
        v0_minutes = estimate.get("phases", {}).get("v0", {}).get("minutes", 12)
        advisory = (
            f"Full product UI building in the background (~{int(v0_minutes)} min). "
            "Safe to close this tab — your build continues on the server. "
            "Reopen from History or this link anytime."
        )
        report_progress(session_id, advisory)
        _spawn_v0(session_id)
        state = _save(
            {
                **state,
                "status": "generating_ui",
                "current_step": advisory,
                "v0_status": "pending",
                "background_build": True,
            }
        )
    elif _fast_mode():
        state = _save({**state, "v0_status": "skipped"})

    has_error = bool(state.get("error"))
    v0_pending = state.get("v0_status") == "pending"
    final_status = "complete_with_warnings" if has_error or v0_pending else "complete"

    done_message = "Done — Stripe + AWS live"
    if v0_pending:
        done_message += f". v0 UI still generating (~{estimate.get('phases', {}).get('v0', {}).get('minutes', 5)} min)"
    elif _fast_mode():
        done_message += " (turbo mode)"

    finished = utc_now()
    if state.get("final_url") and not v0_pending:
        try:
            from tools.stripe_tools import configure_session_checkout_redirects

            configure_session_checkout_redirects(state, session_id=session_id)
        except Exception as exc:
            warning(session_id, "pipeline", f"stripe redirect setup skipped: {exc}")

    return _save(
        {
            **state,
            "status": final_status,
            "current_step": done_message,
            "completed_at": state.get("completed_at") or finished,
            "last_heartbeat": finished,
        }
    )


def run_until_approval(session_id: str) -> AgentState:
    state = get_session(session_id)
    if not state:
        error(session_id, "pipeline", "session not found at run_until_approval")
        raise KeyError(f"Session {session_id} not found")
    with _session_lock:
        if session_id in _running:
            info(session_id, "pipeline", "pre-approval already running — skipping duplicate")
            return state
        _running.add(session_id)
    try:
        with stage(session_id, "pre_approval"):
            agents = _agents_done(state)
            if "research" not in agents:
                report_progress(session_id, "Starting Exa market research…")
                state = _save({**state, "status": "researching", "current_step": "Researching market with Exa"})
                state = _save(run_research(state))
            else:
                info(session_id, "pipeline", "skipping research — checkpoint found")

            if "strategy" not in _agents_done(state):
                state = _save({**state, "current_step": "Drafting product strategy with Claude Opus 4.8"})
                state = _save(run_strategy(state))
            else:
                info(session_id, "pipeline", "skipping strategy — checkpoint found")
                if state.get("status") != "awaiting_approval":
                    state = _save({**state, "status": "awaiting_approval"})

            estimate = estimate_after_strategy(state)
            state = _save(
                {
                    **state,
                    "time_estimate": estimate,
                    "complexity": estimate["complexity"],
                    "current_step": estimate["summary"],
                }
            )
            info(
                session_id,
                "pipeline",
                "awaiting approval",
                product=state.get("product_name"),
                complexity=estimate["complexity"],
                est_minutes=estimate["total_minutes"],
            )
            report_progress(session_id, estimate["summary"])
            return _save({**state, "current_step": "Waiting for your approval", "status": "awaiting_approval"})
    except Exception as exc:
        error(session_id, "pipeline", f"failed before approval: {exc}", exc_info=True)
        failed = append_audit(
            {**state, "status": "error", "error": str(exc), "current_step": "Failed"},
            agent="orchestrator",
            decision="Pipeline failed before approval",
            rationale=traceback.format_exc()[-500:],
        )
        return _save(failed)
    finally:
        with _session_lock:
            _running.discard(session_id)


def run_after_approval(session_id: str, *, approved: bool, feedback: str = "") -> AgentState:
    state = get_session(session_id)
    if not state:
        error(session_id, "pipeline", "session not found at run_after_approval")
        raise KeyError(f"Session {session_id} not found")

    with _session_lock:
        if session_id in _running:
            info(session_id, "pipeline", "post-approval already running — skipping duplicate")
            return state
        _running.add(session_id)

    info(session_id, "pipeline", "approval received", approved=approved, feedback_len=len(feedback))

    if not approved:
        retry = state.get("retry_count", 0) + 1
        warning(session_id, "pipeline", "strategy revision requested", retry=retry)
        state = _save(
            {
                **state,
                "human_approved": False,
                "human_feedback": feedback,
                "retry_count": retry,
                "status": "revising_strategy",
                "current_step": "Revising strategy from your feedback",
            }
        )
        if retry > 2:
            warning(session_id, "pipeline", "max retries exceeded — rejected")
            return _save({**state, "status": "rejected"})
        state = _save(run_strategy(state))
        estimate = estimate_after_strategy(state)
        return _save({**state, "time_estimate": estimate, "complexity": estimate["complexity"]})

    estimate = state.get("time_estimate") or estimate_after_strategy(state)
    report_progress(session_id, f"Approved — {estimate.get('summary', 'deploying…')}")

    state = _save(
        {
            **state,
            "human_approved": True,
            "human_feedback": feedback,
            "status": "building",
            "current_step": "Deploying Stripe + AWS in parallel…",
            "error": "",
            "v0_status": "skipped" if _fast_mode() else state.get("v0_status", "pending"),
        }
    )
    try:
        return _finish_post_approval(state)
    finally:
        with _session_lock:
            _running.discard(session_id)


def _maybe_respawn_v0(session_id: str, state: AgentState) -> None:
    """Restart v0 UI generation if it was interrupted (API restart, crash)."""
    if _fast_mode():
        return
    if state.get("v0_status") not in ("pending", "error"):
        return
    if not state.get("human_approved"):
        return
    agents = _agents_done(state)
    if "monetization" not in agents:
        return
    with _session_lock:
        if session_id in _v0_running:
            return
    if state.get("v0_status") == "error" and "builder" in agents:
        return
    info(session_id, "v0_background", "respawning interrupted v0 build")
    report_progress(
        session_id,
        "Resuming product UI build in the background — safe to leave and check History later.",
    )
    _spawn_v0(session_id)


def resume_session(session_id: str) -> AgentState:
    state = get_session(session_id)
    if not state:
        raise KeyError(f"Session {session_id} not found")
    if not is_resumable(state):
        warning(session_id, "resume", "session not resumable", status=state.get("status"))
        return state

    with _session_lock:
        if session_id in _running:
            info(session_id, "resume", "already running — skipping duplicate")
            return state
        _running.add(session_id)

    try:
        agents = _agents_done(state)
        info(
            session_id,
            "resume",
            "resuming from checkpoint",
            status=state.get("status"),
            agents=",".join(sorted(agents)),
            v0_status=state.get("v0_status"),
        )
        report_progress(session_id, "Resuming build from last saved checkpoint…")
        state = _save({**state, "error": ""})

        if state.get("status") == "awaiting_approval":
            return state

        if state.get("human_approved"):
            if state.get("v0_status") in ("pending", "error") and "monetization" in agents:
                ui_missing = not state.get("final_url") and not state.get("vercel_deployment_url")
                builder_failed = any(
                    e.get("agent") == "builder"
                    and "failed" in (e.get("decision") or "").lower()
                    for e in state.get("audit_log") or []
                )
                should_retry_ui = (
                    state.get("v0_status") == "pending"
                    and "builder" not in agents
                ) or (
                    ui_missing
                    and (builder_failed or state.get("v0_status") == "error" or "builder" not in agents)
                )
                if should_retry_ui:
                    state = _save({**state, "v0_status": "pending", "error": "", "background_build": True})
                    _spawn_v0(session_id)
                    report_progress(
                        session_id,
                        "Retrying v0 UI generation with updated API key…"
                        if builder_failed
                        else "Resuming v0 UI generation in the background…",
                    )
                elif state.get("v0_status") == "pending":
                    _maybe_respawn_v0(session_id, state)
                if state.get("status") not in ("complete", "complete_with_warnings"):
                    return _finish_post_approval(state)
                return state

            if "audit" in agents and state.get("v0_status") in ("pending", "error"):
                state = _save({**state, "v0_status": "pending", "background_build": True})
                _maybe_respawn_v0(session_id, state)
                return state

            return _finish_post_approval(state)

        return run_until_approval(session_id)
    finally:
        with _session_lock:
            _running.discard(session_id)


def auto_resume_interrupted() -> int:
    """Resume in-flight sessions after API restart."""
    if os.getenv("DISABLE_AUTO_RESUME", "").strip().lower() in {"1", "true", "yes"}:
        info(None, "store", "auto-resume disabled (DISABLE_AUTO_RESUME)")
        return 0
    count = 0
    for session_id in list_resumable_sessions():
        state = get_session(session_id)
        if not state:
            continue
        status = state.get("status", "")
        if status == "awaiting_approval":
            continue
        if state.get("v0_status") == "error" and "builder" in _agents_done(state):
            continue
        # v0 pending on a "complete" session — respawn UI thread without full pipeline replay
        if (
            status in ("complete", "complete_with_warnings", "generating_ui")
            and state.get("v0_status") == "pending"
            and state.get("human_approved")
            and "builder" not in _agents_done(state)
        ):
            info(session_id, "store", "auto-resuming background v0 build", status=status)
            _maybe_respawn_v0(session_id, state)
            count += 1
            continue
        info(session_id, "store", "auto-resuming interrupted session", status=status)
        threading.Thread(target=resume_session, args=(session_id,), daemon=True).start()
        count += 1
    return count
