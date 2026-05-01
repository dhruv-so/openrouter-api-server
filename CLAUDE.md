# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FastAPI server wrapping Google's Gemini 3.0 models (Pro and Flash) as a single authenticated REST endpoint. Generation traffic flows through **OpenRouter's OpenAI-compatible chat completions endpoint** — the server speaks OpenAI shape on the wire, OpenRouter routes to Gemini. Public API contract (`/generate` request and response fields, `X-API-Key` auth, public model names) is independent of that backend choice.

## Common Commands

Setup:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill OPENROUTER_API_KEY, SERVER_API_KEY, ALLOWED_ORIGINS
```

Run server (dev):
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
# interactive docs: http://localhost:8000/docs
```

Tests:
```bash
pytest tests/ -v                          # all tests
pytest tests/test_security.py -v          # security suite only
pytest tests/test_api.py::TestImagePayloadAssembly::test_image_payload_assembled_as_data_uri_with_detail_high -v  # single test
pytest tests/ --cov=app --cov-report=html # coverage
```

Security scans:
```bash
bandit -r app/ -ll
pipx install safety && safety check  # safety pinned out of requirements.txt due to pydantic conflict
```

Docker:
```bash
docker build -t gemini-api .
docker run -p 8000:8000 --env-file .env gemini-api
```

## Architecture

### Request flow
`main.py` → middlewares (security headers, GZip, CORS) → `app/routes/generate.py:generate` → utility loaders (`prompts.py`, `images.py`) → `app/openrouter_client.py:send_chat_completion` → OpenRouter HTTP → response assembly.

Single primary endpoint `POST /generate` (auth required) plus unauthenticated `GET /health`. Auth is `X-API-Key` header validated against `SERVER_API_KEY`. Rate limiting via `slowapi` keyed on remote address (`RATE_LIMIT` env, default `10/minute`).

### Module layout and responsibilities
- `main.py` — FastAPI app construction, middleware wiring (CORS from `ALLOWED_ORIGINS`, security headers, GZip), exception handlers that sanitize errors before returning to clients.
- `app/config.py` — env loading via `python-dotenv`. Defines `SUPPORTED_MODELS`, `THINKING_LEVELS` (per-model official set), and `MODEL_SLUG_MAP` (public name → OpenRouter slug, e.g. `gemini-3-flash-preview` → `google/gemini-3-flash-preview`). `MODEL_NAME` constant is the public-facing default returned by `/health`.
- `app/dependencies.py` — `lifespan` async context manager initializes a pooled `requests.Session` at startup. Module-level globals (`http_session`, `app_start_time`) are mutated by lifespan; tests must seed `app_start_time` (see `tests/conftest.py`). The Gemini SDK client is gone — every external HTTP call goes through this shared session.
- `app/models.py` — Pydantic models for request/response. `GenerateRequest` enforces field length caps, enum-based `PromptType`, and custom validators on `user_prompt` / `system_prompt` / `model`. `GenerateResponse.output` is `Union[dict, list, str]` — string when no schema, parsed JSON when schema provided.
- `app/security.py` — three concerns colocated: API-key auth dependency (`verify_api_key`), SSRF guard (`validate_url` blocks non-http(s) schemes, blocked hostnames including cloud metadata, private/loopback/link-local/multicast/reserved IPs), security-headers middleware (`add_security_headers`).
- `app/openrouter_client.py` — owns all OpenRouter HTTP. `send_chat_completion` POSTs to `OPENROUTER_BASE_URL/chat/completions` via the shared session, maps upstream errors to `HTTPException` with safe generic detail. Helpers: `build_messages` (assembles OpenAI-style multimodal content array — images first as base64 data URIs with `detail: "high"`, then trailing text), `build_response_format` (wraps a JSON-Schema dict for structured output with `strict: true`), `map_thinking_level` (case-insensitive normalize → lowercase `reasoning.effort`; logs warning when level isn't in the model's official supported set but forwards anyway since OpenRouter remaps).
- `app/routes/generate.py` — orchestration. Selects model + slug, loads prompts/images via existing utilities, builds the OpenRouter payload, sends, parses `choices[0].message.content` (json.loads when schema requested, else string), extracts token usage. Catches all exceptions and returns generic 500 — never leak internal details.
- `app/routes/health.py` — uptime + `OPENROUTER_API_KEY`/`http_session` presence check, never calls upstream.
- `app/utils/prompts.py` — `load_content_from_source` handles `text` (size-checked) or `file` (URL fetched via shared session, streamed in chunks with size cap `MAX_PROMPT_SIZE = 10MB`, validated through `validate_url` first).
- `app/utils/images.py` — `load_image_from_url` mirrors prompt loader for `MAX_IMAGE_SIZE = 20MB`, infers MIME from `Content-Type` header then `mimetypes.guess_type`, falls back to `image/jpeg`. Returns `(bytes, mime_type)`. Bytes are base64-encoded when assembled into the OpenRouter payload.
- `app/utils/tokens.py` — token-count extractor tolerant of dicts (OpenAI-style `prompt_tokens` / `completion_tokens` / `total_tokens`) and objects (legacy SDK shape with `prompt_token_count` etc.).

### Cross-cutting invariants
- **Every external URL fetch goes through `validate_url` first.** When adding new fetch paths, never bypass it. This includes images: images are downloaded server-side and forwarded as base64 data URIs rather than passed as raw URLs to OpenRouter — base64 keeps the SSRF + 20MB guards active.
- **Errors returned to clients are generic.** Detailed errors only go to logs. The catch-all in `generate` and the global handlers in `main.py` enforce this. OpenRouter upstream bodies are logged but never echoed.
- **API-key auth is the only auth mechanism**; missing `SERVER_API_KEY` env makes the route return 500 (deliberate — fail closed). Missing `OPENROUTER_API_KEY` makes the app fail to boot (raised in `config.py`).
- **CORS is empty if `ALLOWED_ORIGINS` env is unset** — server logs a warning but does not relax to `*`.
- **Thinking level**: normalize to lowercase canonical `minimal | low | medium | high` before sending as `reasoning.effort`. Per-model official sets live in `THINKING_LEVELS`. Mismatched levels are forwarded with a logged warning — OpenRouter remaps to nearest upstream.
- **Public model names stay stable**. Clients send `gemini-3-pro-preview` / `gemini-3-flash-preview`; the `google/...` slug remap happens only at OpenRouter call time. `/health.model` reports the public name.
- **Image transport**: always base64 data URI with `detail: "high"`. There is no per-request media-resolution knob; high fidelity is the default.

### Tests
`tests/conftest.py` sets test env vars *before* importing `main`, monkeypatches `app.openrouter_client.send_chat_completion` (the `mock_openrouter` fixture returns the captured kwargs dict so tests can assert on outgoing payload shape — model slug, reasoning, response_format, message content), and seeds `app_start_time`. `RATE_LIMIT` is bumped to `100/minute` for tests. New tests should use the `client` and `mock_openrouter` fixtures rather than calling OpenRouter live.

`httpx` is pinned to `<0.28` in `requirements.txt` because `fastapi==0.109.2`'s `TestClient` (via Starlette) is incompatible with the newer httpx Client signature.
