from __future__ import annotations

import json
import os
from typing import Any, Literal

import httpx

from orchestrator.stage_log import info, warning

ModelTier = Literal["fast", "strategy", "builder"]

_DEFAULTS: dict[ModelTier, str] = {
    "fast": "anthropic/claude-haiku-4.5",
    "strategy": "anthropic/claude-opus-4.8",
    "builder": "openai/gpt-5.5",
}

_ENV_KEYS: dict[ModelTier, str] = {
    "fast": "LLM_MODEL_FAST",
    "strategy": "LLM_MODEL_STRATEGY",
    "builder": "LLM_MODEL_BUILDER",
}

_MAX_TOKENS: dict[ModelTier, int] = {
    "fast": 2000,
    "strategy": 3000,
    "builder": 4000,
}


def model_for_tier(tier: ModelTier = "fast") -> str:
    env_key = _ENV_KEYS[tier]
    return os.getenv(env_key, _DEFAULTS[tier]).strip() or _DEFAULTS[tier]


def _is_openai_model(model: str) -> bool:
    normalized = model.lower()
    return "gpt" in normalized or normalized.startswith("openai/")


def _is_anthropic_model(model: str) -> bool:
    normalized = model.lower()
    return "claude" in normalized or normalized.startswith("anthropic/")


def _openai_model_id(model: str) -> str:
    if "/" in model:
        return model.split("/", 1)[1]
    return model


def _anthropic_model_id(model: str) -> str:
    if "/" in model:
        return model.split("/", 1)[1]
    return model


def chat_json(
    system: str,
    user: str,
    *,
    tier: ModelTier = "fast",
    model: str | None = None,
    session_id: str | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    resolved = model or model_for_tier(tier)
    token_limit = max_tokens or _MAX_TOKENS[tier]
    gateway_key = os.getenv("AI_GATEWAY_API_KEY", "").strip()
    gateway_url = os.getenv("VERCEL_AI_GATEWAY_URL", "https://ai-gateway.vercel.sh").rstrip("/")
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    prefer_openai_direct = os.getenv("LLM_PREFER_OPENAI_DIRECT", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    info(session_id, "llm", "request", tier=tier, model=resolved)

    # Optional: skip gateway for OpenAI models when user has their own key
    if prefer_openai_direct and _is_openai_model(resolved) and openai_key:
        try:
            result = _openai_chat(
                system,
                user,
                model=_openai_model_id(resolved),
                openai_key=openai_key,
                max_tokens=token_limit,
                session_id=session_id,
            )
            info(session_id, "llm", "openai direct ok", tier=tier, model=_openai_model_id(resolved))
            return result
        except Exception as exc:
            warning(session_id, "llm", f"openai direct failed: {exc}", tier=tier, model=resolved)

    if gateway_key:
        try:
            result = _gateway_chat(
                system,
                user,
                model=resolved,
                gateway_url=gateway_url,
                gateway_key=gateway_key,
                max_tokens=token_limit,
                session_id=session_id,
            )
            info(session_id, "llm", "gateway ok", tier=tier, model=resolved)
            return result
        except Exception as exc:
            warning(
                session_id,
                "llm",
                f"gateway failed: {exc}",
                tier=tier,
                model=resolved,
            )

    if _is_openai_model(resolved) and openai_key:
        try:
            result = _openai_chat(
                system,
                user,
                model=_openai_model_id(resolved),
                openai_key=openai_key,
                max_tokens=token_limit,
                session_id=session_id,
            )
            info(session_id, "llm", "openai direct ok", tier=tier, model=_openai_model_id(resolved))
            return result
        except Exception as exc:
            warning(session_id, "llm", f"openai direct failed: {exc}", tier=tier, model=resolved)

    if _is_anthropic_model(resolved) or _is_openai_model(resolved):
        fallback = _anthropic_fallback(resolved)
        result = _anthropic_chat(system, user, model=fallback, session_id=session_id)
        info(session_id, "llm", "anthropic fallback ok", tier=tier, model=fallback)
        return result

    raise RuntimeError(f"No LLM provider available for model {resolved}")


def chat_text(
    system: str,
    user: str,
    *,
    tier: ModelTier = "fast",
    model: str | None = None,
    session_id: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Return raw model text (no JSON parsing)."""
    resolved = model or model_for_tier(tier)
    token_limit = max_tokens or _MAX_TOKENS[tier]
    gateway_key = os.getenv("AI_GATEWAY_API_KEY", "").strip()
    gateway_url = os.getenv("VERCEL_AI_GATEWAY_URL", "https://ai-gateway.vercel.sh").rstrip("/")
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    prefer_openai_direct = os.getenv("LLM_PREFER_OPENAI_DIRECT", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    info(session_id, "llm", "text request", tier=tier, model=resolved)

    if prefer_openai_direct and _is_openai_model(resolved) and openai_key:
        try:
            return _openai_chat_text(
                system,
                user,
                model=_openai_model_id(resolved),
                openai_key=openai_key,
                max_tokens=token_limit,
                session_id=session_id,
            )
        except Exception as exc:
            warning(session_id, "llm", f"openai direct text failed: {exc}")

    if gateway_key:
        try:
            return _gateway_chat_text(
                system,
                user,
                model=resolved,
                gateway_url=gateway_url,
                gateway_key=gateway_key,
                max_tokens=token_limit,
                session_id=session_id,
            )
        except Exception as exc:
            warning(session_id, "llm", f"gateway text failed: {exc}")

    if _is_openai_model(resolved) and openai_key:
        return _openai_chat_text(
            system,
            user,
            model=_openai_model_id(resolved),
            openai_key=openai_key,
            max_tokens=token_limit,
            session_id=session_id,
        )

    if _is_anthropic_model(resolved) and os.getenv("ANTHROPIC_API_KEY", "").strip():
        return _anthropic_chat_text(
            system,
            user,
            model=_anthropic_model_id(resolved),
            session_id=session_id,
            max_tokens=token_limit,
        )

    raise RuntimeError(f"No LLM provider available for text model {resolved}")


def _supports_temperature(model: str) -> bool:
    """GPT 5.x models reject the temperature parameter."""
    normalized = model.lower()
    return "gpt-5" not in normalized and "gpt5" not in normalized


def _anthropic_fallback(model: str) -> str:
    if "opus" in model:
        return "claude-opus-4-6"
    if _is_openai_model(model):
        return "claude-sonnet-4-6"
    return "claude-haiku-4-5-20251001"


def _gateway_chat(
    system: str,
    user: str,
    *,
    model: str,
    gateway_url: str,
    gateway_key: str,
    max_tokens: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
    }
    if _supports_temperature(model):
        payload["temperature"] = 0.2

    response = httpx.post(
        f"{gateway_url}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {gateway_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    if response.status_code >= 400:
        warning(
            session_id,
            "llm",
            "gateway HTTP error",
            status=response.status_code,
            body=response.text[:300],
        )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _parse_json(content)


def _gateway_chat_text(
    system: str,
    user: str,
    *,
    model: str,
    gateway_url: str,
    gateway_key: str,
    max_tokens: int,
    session_id: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
    }
    if _supports_temperature(model):
        payload["temperature"] = 0.3

    response = httpx.post(
        f"{gateway_url}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {gateway_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _openai_chat_text(
    system: str,
    user: str,
    *,
    model: str,
    openai_key: str,
    max_tokens: int,
    session_id: str | None = None,
) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    payload: dict[str, Any] = {"model": model, "messages": messages}
    if _supports_temperature(model):
        payload["temperature"] = 0.3
        payload["max_tokens"] = max_tokens
    else:
        payload["max_completion_tokens"] = max_tokens

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    choice = data["choices"][0]
    content = (choice.get("message") or {}).get("content") or ""
    text = content.strip() if isinstance(content, str) else ""
    if not text and choice.get("finish_reason") == "length":
        warning(
            session_id,
            "llm",
            "openai returned empty content — increase max_completion_tokens",
            model=model,
        )
    return text


def _anthropic_chat_text(
    system: str,
    user: str,
    *,
    model: str,
    session_id: str | None = None,
    max_tokens: int = 8000,
) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0.3,
    )
    return message.content[0].text.strip()


def _openai_chat(
    system: str,
    user: str,
    *,
    model: str,
    openai_key: str,
    max_tokens: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    payload: dict[str, Any] = {"model": model, "messages": messages}
    if _supports_temperature(model):
        payload["temperature"] = 0.2
        payload["max_tokens"] = max_tokens
    else:
        payload["max_completion_tokens"] = max_tokens

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    if response.status_code >= 400:
        warning(
            session_id,
            "llm",
            "openai HTTP error",
            status=response.status_code,
            body=response.text[:300],
        )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _parse_json(content)


def _anthropic_chat(
    system: str,
    user: str,
    *,
    model: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=_anthropic_model_id(model),
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0.2,
    )
    content = message.content[0].text
    return _parse_json(content)


def _parse_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
