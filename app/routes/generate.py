"""
Generate content endpoint.

Routes generation requests through OpenRouter's OpenAI-compatible chat
completions endpoint while keeping the public API contract identical to
the previous direct-Gemini implementation.
"""

import json
import logging

from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import (
    MODEL_NAME,
    MAX_PROMPT_SIZE,
    SUPPORTED_MODELS,
    MODEL_SLUG_MAP,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_OUTPUT_TOKENS,
    RATE_LIMIT,
)
from app.models import GenerateRequest, GenerateResponse
from app.security import verify_api_key
from app.utils import (
    load_content_from_source,
    load_image_from_url,
    extract_token_counts,
)
from app import openrouter_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Generation"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit(RATE_LIMIT)
async def generate(
    request: Request,
    data: GenerateRequest,
    api_key: str = Depends(verify_api_key),
):
    """Generate response via OpenRouter chat completions.

    Requires authentication via X-API-Key header. Rate limited per-IP.
    """
    try:
        # 1. Validate and select model
        selected_model = data.model if data.model else MODEL_NAME
        if selected_model not in SUPPORTED_MODELS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model '{selected_model}'. Supported models: {', '.join(SUPPORTED_MODELS)}",
            )
        slug = MODEL_SLUG_MAP[selected_model]
        logger.info(f"Using model: {selected_model} (slug={slug})")

        # 2. Load user prompt (REQUIRED)
        user_prompt_text = load_content_from_source(
            data.user_prompt,
            data.user_prompt_type,
            max_size=MAX_PROMPT_SIZE,
        )
        logger.info(f"Loaded user prompt ({data.user_prompt_type}): {len(user_prompt_text)} chars")

        # 3. Load system prompt (OPTIONAL)
        system_prompt_text = None
        if data.system_prompt:
            system_prompt_text = load_content_from_source(
                data.system_prompt,
                data.system_prompt_type,
                max_size=MAX_PROMPT_SIZE,
            )
            logger.info(
                f"Loaded system prompt ({data.system_prompt_type}): "
                f"{len(system_prompt_text)} chars"
            )

        # 4. Download images (SSRF + size guards live in load_image_from_url)
        loaded_images: list[tuple[bytes, str]] = []
        if data.image_urls:
            for img_url in data.image_urls:
                img_bytes, mime_type = load_image_from_url(img_url)
                loaded_images.append((img_bytes, mime_type))
                logger.info(
                    f"Loaded image from URL: {img_url} ({mime_type}, {len(img_bytes)} bytes)"
                )

        # 5. Build OpenRouter payload
        messages = openrouter_client.build_messages(
            system_prompt=system_prompt_text,
            user_prompt=user_prompt_text,
            images=loaded_images,
        )
        response_format = openrouter_client.build_response_format(data.json_schema)
        reasoning = openrouter_client.map_thinking_level(data.thinking_level, selected_model)

        if response_format:
            logger.info("Using structured JSON output with schema")

        # 6. Call OpenRouter
        logger.info(f"Sending chat completion request: model={slug}")
        response_json = openrouter_client.send_chat_completion(
            model=slug,
            messages=messages,
            response_format=response_format,
            reasoning=reasoning,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
        )

        # 7. Extract content
        try:
            content_str = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Unexpected OpenRouter response shape: {e}; body={response_json}")
            raise HTTPException(status_code=500, detail="Invalid response from upstream model")

        if not content_str:
            finish_reason = None
            try:
                finish_reason = response_json["choices"][0].get("finish_reason")
            except (KeyError, IndexError, TypeError):
                pass
            logger.error(
                f"Empty content from upstream model. finish_reason={finish_reason} "
                f"body={response_json}"
            )
            raise HTTPException(
                status_code=500,
                detail="Upstream model returned empty response (content filtering or safety block)",
            )

        # 8. Parse JSON when schema requested; otherwise leave as string
        if data.json_schema:
            try:
                parsed_output = json.loads(content_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse structured JSON output: {e}; content={content_str[:500]}")
                raise HTTPException(status_code=500, detail="Failed to parse structured response")
        else:
            try:
                parsed_output = json.loads(content_str)
            except (json.JSONDecodeError, TypeError):
                parsed_output = content_str

        # 9. Token usage
        input_tokens, output_tokens, total_tokens = extract_token_counts(
            response_json.get("usage")
        )

        # 10. Log
        has_schema = "structured" if data.json_schema else "natural"
        model_short = selected_model.replace("-preview", "").replace("gemini-", "")
        logger.info(
            f"[{model_short}] mode={has_schema} "
            f"thinking_level={reasoning['effort']} "
            f"tokens={input_tokens}/{output_tokens}/{total_tokens}"
        )

        return GenerateResponse(
            output=parsed_output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please contact support if this persists.",
        )
