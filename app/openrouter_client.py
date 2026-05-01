"""
OpenRouter client.

Encapsulates the HTTP call to OpenRouter's OpenAI-compatible chat completions
endpoint plus helpers to assemble request payloads from the server's domain
inputs (system/user prompts, image bytes, JSON schema, thinking level).
"""

import base64
import json
import logging
from typing import Iterable

import requests
from fastapi import HTTPException

from app.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_REFERER,
    OPENROUTER_APP_TITLE,
    OPENROUTER_TIMEOUT,
    THINKING_LEVELS,
)
from app.dependencies import get_http_session

logger = logging.getLogger(__name__)


_CANONICAL_THINKING = {
    "MINIMAL": "minimal",
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
}


def map_thinking_level(level: str, model_public_name: str) -> dict:
    """Normalize thinking level to OpenRouter's reasoning.effort payload.

    Accepts case-insensitive {minimal, low, medium, high}. Unknown values fall
    back to "high" with a warning. If the level isn't in the model's official
    supported set, log a warning but pass through — OpenRouter remaps to the
    nearest supported value upstream.
    """
    raw = (level or "").upper()
    canonical = _CANONICAL_THINKING.get(raw)
    if canonical is None:
        logger.warning(
            f"Unknown thinking_level '{level}', defaulting to 'high'"
        )
        canonical = "high"

    valid_for_model = THINKING_LEVELS.get(model_public_name, [])
    if valid_for_model and canonical not in valid_for_model:
        logger.warning(
            f"thinking_level='{canonical}' not officially supported for "
            f"model '{model_public_name}' (supported: {valid_for_model}); "
            f"OpenRouter will remap to the nearest value"
        )

    return {"effort": canonical}


def build_response_format(json_schema: dict | None) -> dict | None:
    """Wrap a user-supplied JSON Schema dict for OpenRouter structured output."""
    if not json_schema:
        return None
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "response",
            "strict": True,
            "schema": json_schema,
        },
    }


def build_messages(
    *,
    system_prompt: str | None,
    user_prompt: str,
    images: Iterable[tuple[bytes, str]] | None = None,
) -> list[dict]:
    """Assemble OpenAI-style chat messages.

    `images` is an iterable of (bytes, mime_type). When present, the user
    message uses a multimodal content array — images first, text last,
    matching the order used by the previous Gemini SDK call site.
    """
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    image_list = list(images) if images else []
    if image_list:
        content_parts: list[dict] = []
        for img_bytes, mime in image_list:
            b64 = base64.b64encode(img_bytes).decode("ascii")
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{b64}",
                    "detail": "high",
                },
            })
        content_parts.append({"type": "text", "text": user_prompt})
        messages.append({"role": "user", "content": content_parts})
    else:
        messages.append({"role": "user", "content": user_prompt})

    return messages


def _build_headers() -> dict:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": OPENROUTER_APP_TITLE,
    }
    if OPENROUTER_REFERER:
        headers["HTTP-Referer"] = OPENROUTER_REFERER
    return headers


def send_chat_completion(
    *,
    model: str,
    messages: list[dict],
    response_format: dict | None = None,
    reasoning: dict | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    extra: dict | None = None,
) -> dict:
    """POST to OpenRouter chat completions and return parsed JSON.

    Maps upstream errors to FastAPI HTTPException with safe, generic detail.
    Always logs full upstream body on error; never echoes it to clients.
    """
    payload: dict = {"model": model, "messages": messages}
    if response_format is not None:
        payload["response_format"] = response_format
    if reasoning is not None:
        payload["reasoning"] = reasoning
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if extra:
        payload.update(extra)

    session = get_http_session()
    url = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    try:
        r = session.post(
            url,
            json=payload,
            headers=_build_headers(),
            timeout=OPENROUTER_TIMEOUT,
        )
    except requests.Timeout:
        logger.error("OpenRouter timeout")
        raise HTTPException(status_code=504, detail="Upstream model timeout")
    except requests.ConnectionError as e:
        logger.error(f"OpenRouter connection error: {e}")
        raise HTTPException(status_code=502, detail="Upstream model unavailable")
    except requests.RequestException as e:
        logger.error(f"OpenRouter request failed: {e}")
        raise HTTPException(status_code=502, detail="Upstream model error")

    if r.status_code >= 400:
        body_preview = r.text[:1000] if r.text else ""
        logger.error(f"OpenRouter HTTP {r.status_code}: {body_preview}")
        if r.status_code in (401, 403):
            raise HTTPException(status_code=500, detail="Upstream model authentication error")
        if r.status_code == 402:
            raise HTTPException(status_code=503, detail="Upstream model temporarily unavailable")
        if r.status_code in (408, 429):
            raise HTTPException(status_code=429, detail="Upstream rate limit hit, please retry")
        if r.status_code == 400:
            raise HTTPException(status_code=400, detail="Invalid request to upstream model")
        raise HTTPException(status_code=502, detail="Upstream model error")

    try:
        return r.json()
    except (ValueError, json.JSONDecodeError):
        logger.error(f"OpenRouter non-JSON response: {r.text[:500]}")
        raise HTTPException(status_code=500, detail="Invalid response from upstream model")
