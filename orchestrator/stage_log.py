from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any

_configured = False
_logger = logging.getLogger("ideaforge")


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_file = os.getenv("LOG_FILE", "").strip()

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    _configured = True


def _prefix(session_id: str | None, stage: str) -> str:
    sid = (session_id or "nosession")[:8]
    return f"[{sid}] [{stage}]"


def _fields_suffix(fields: dict[str, Any]) -> str:
    if not fields:
        return ""
    parts = [f"{key}={value}" for key, value in fields.items()]
    return " | " + " ".join(parts)


def info(session_id: str | None, stage: str, message: str, **fields: Any) -> None:
    setup_logging()
    _logger.info("%s %s%s", _prefix(session_id, stage), message, _fields_suffix(fields))


def warning(session_id: str | None, stage: str, message: str, **fields: Any) -> None:
    setup_logging()
    _logger.warning("%s %s%s", _prefix(session_id, stage), message, _fields_suffix(fields))


def error(
    session_id: str | None,
    stage: str,
    message: str,
    *,
    exc_info: bool = False,
    **fields: Any,
) -> None:
    setup_logging()
    _logger.error("%s %s%s", _prefix(session_id, stage), message, _fields_suffix(fields), exc_info=exc_info)


@contextmanager
def stage(session_id: str, name: str, **start_fields: Any):
    info(session_id, name, "started", **start_fields)
    started = time.perf_counter()
    try:
        yield
        duration_ms = int((time.perf_counter() - started) * 1000)
        info(session_id, name, "completed", duration_ms=duration_ms)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        error(
            session_id,
            name,
            f"failed: {exc}",
            duration_ms=duration_ms,
            exc_info=True,
        )
        raise
