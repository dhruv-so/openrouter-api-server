# Gemini 3.0 API Server

A FastAPI server that exposes Google's Gemini 3.0 models (Pro and Flash) as a REST API. Generation is routed through **OpenRouter's OpenAI-compatible chat completions endpoint** — one provider key, OpenAI-shape requests, Gemini under the hood.

Supports flexible prompts (text or file URLs), multiple image URLs, JSON-schema-enforced structured output, and per-request configurable model + thinking level.

## Features

- ✅ **Security First** — API key authentication, rate limiting, SSRF protection
- ✅ **Multiple model support** — `gemini-3-pro-preview` or `gemini-3-flash-preview`
- ✅ **Flexible prompts** — pass as text or load from URLs
- ✅ **Multiple images** — image URLs (downloaded server-side and forwarded as base64)
- ✅ **Structured JSON output** — pass a `json_schema`, get back a parsed object
- ✅ **Configurable thinking levels** — `minimal | low | medium | high` (Pro currently honors `low/high`; Flash honors all four)
- ✅ **Dynamic system prompts** — control model behavior per request

## Quick Start

### Local Setup

```bash
# 1. Create + activate a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (copy .env.example then edit)
cp .env.example .env
# Required: OPENROUTER_API_KEY, SERVER_API_KEY, ALLOWED_ORIGINS

# 4. Run the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

Server available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

> **⚠️ Security Warning**: Never commit your `.env` file to version control.

### Docker Setup

```bash
docker build -t gemini-api .
docker run -p 8000:8000 \
  -e OPENROUTER_API_KEY=sk-or-... \
  -e SERVER_API_KEY=your-server-api-key-here \
  -e ALLOWED_ORIGINS=http://localhost:3000 \
  gemini-api
```

## 🔒 Security

### Authentication

**All API endpoints (except `/health`) require authentication** via the `X-API-Key` header.

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-server-api-key-here" \
  -d '{"user_prompt": "Hello, world!"}'
```

### Security Features

- ✅ **API Key Authentication** — secures all generation endpoints
- ✅ **Rate Limiting** — configurable per IP, default `10/minute`
- ✅ **SSRF Protection** — blocks private IPs, localhost, cloud metadata endpoints
- ✅ **Input Validation** — strict Pydantic models with custom validators
- ✅ **Security Headers** — `X-Frame-Options`, CSP, HSTS, etc.
- ✅ **CORS Control** — environment-based origin whitelisting
- ✅ **Error Sanitization** — no internal details exposed to clients
- ✅ **Docker Security** — runs as non-root user

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | ✅ Yes | — | Your OpenRouter API key (`sk-or-...`) |
| `SERVER_API_KEY` | ✅ Yes | — | API key clients must send via `X-API-Key` |
| `ALLOWED_ORIGINS` | ✅ Yes | — | Comma-separated list of allowed CORS origins |
| `OPENROUTER_BASE_URL` | ❌ No | `https://openrouter.ai/api/v1` | OpenRouter base URL |
| `OPENROUTER_REFERER` | ❌ No | empty | Optional `HTTP-Referer` header (helps OpenRouter rank/identify your app) |
| `OPENROUTER_APP_TITLE` | ❌ No | `Gemini-3 API Server` | Optional `X-Title` header |
| `OPENROUTER_TIMEOUT` | ❌ No | `60` | OpenRouter request timeout (seconds) |
| `RATE_LIMIT` | ❌ No | `10/minute` | Per-IP rate limit (e.g. `10/minute`, `100/hour`) |
| `REQUEST_TIMEOUT` | ❌ No | `15` | Timeout for fetching prompt/image URLs (seconds) |
| `DEFAULT_TEMPERATURE` | ❌ No | `1.0` | Default sampling temperature |
| `DEFAULT_TOP_P` | ❌ No | `0.95` | Default top_p |
| `DEFAULT_MAX_OUTPUT_TOKENS` | ❌ No | `12000` | Default max output tokens |

**See [SECURITY.md](SECURITY.md) for detailed security guidelines.**

## API Usage

### Endpoint: `POST /generate`

**Content-Type:** `application/json`

### Request Body Schema

```json
{
  "user_prompt": "string (required)",
  "user_prompt_type": "text" | "file"  (optional, default: "text"),
  "system_prompt": "string"            (optional),
  "system_prompt_type": "text" | "file"(optional, default: "text"),
  "image_urls": ["url1", "url2"]       (optional, max 10),
  "json_schema": { ... }               (optional),
  "model": "gemini-3-pro-preview" | "gemini-3-flash-preview"
                                       (optional, default: "gemini-3-flash-preview"),
  "thinking_level": "minimal" | "low" | "medium" | "high"
                                       (optional, default: "high", case-insensitive)
}
```

### Response Format

```json
{
  "output": "...",
  "input_tokens": 1234,
  "output_tokens": 567,
  "total_tokens": 1801
}
```

`output` is a string by default, or a parsed object/array when `json_schema` is provided.

## CURL Examples

### 1. Simple Text Generation

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-server-api-key-here" \
  -d '{"user_prompt": "Write a haiku about coding"}'
```

### 2. With System Prompt

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-server-api-key-here" \
  -d '{
    "user_prompt": "Explain quantum computing",
    "system_prompt": "You are a physics professor teaching undergraduates. Use simple analogies."
  }'
```

### 3. Load Prompts from URLs

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-server-api-key-here" \
  -d '{
    "user_prompt": "https://yourserver.com/prompts/landing-page-task.txt",
    "user_prompt_type": "file",
    "system_prompt": "https://yourserver.com/prompts/system.txt",
    "system_prompt_type": "file"
  }'
```

### 4. Image URL Inputs

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-server-api-key-here" \
  -d '{
    "user_prompt": "Analyze this landing page",
    "image_urls": [
      "https://example.com/screenshot1.png",
      "https://example.com/screenshot2.png"
    ]
  }'
```

Images are fetched server-side (so SSRF rules and the 20MB cap apply), then forwarded to OpenRouter as base64 data URIs with `image_url.detail = "high"`.

### 5. Using Gemini 3 Flash

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-server-api-key-here" \
  -d '{
    "user_prompt": "Write a short story about AI",
    "model": "gemini-3-flash-preview",
    "thinking_level": "medium"
  }'
```

### 6. Structured JSON Output

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-server-api-key-here" \
  -d '{
    "user_prompt": "Extract product details from this image",
    "image_urls": ["https://example.com/product.jpg"],
    "json_schema": {
      "type": "object",
      "required": ["name", "price"],
      "properties": {
        "name": {"type": "string"},
        "price": {"type": "number"},
        "description": {"type": "string"}
      }
    }
  }'
```

**Response:**

```json
{
  "output": {
    "name": "Premium Headphones",
    "price": 299.99,
    "description": "Noise-cancelling wireless headphones"
  },
  "input_tokens": 1523,
  "output_tokens": 45,
  "total_tokens": 1568
}
```

## Request Parameters

### Model Selection (`model`)

Optional — choose which Gemini 3.0 model to use (default: `gemini-3-flash-preview`).

- **`gemini-3-pro-preview`** — Gemini 3 Pro with advanced reasoning (officially supports `low`/`high` thinking levels)
- **`gemini-3-flash-preview`** — Gemini 3 Flash, speed/efficiency-tuned (officially supports `minimal`/`low`/`medium`/`high`)

The server accepts the public model names; OpenRouter slugs (`google/gemini-3-pro-preview`, `google/gemini-3-flash-preview`) are applied internally.

### Thinking Level (`thinking_level`)

Optional, default `"high"`, case-insensitive. Accepted values: `minimal`, `low`, `medium`, `high`.

If you pass a level that the chosen model doesn't officially support, the server forwards it anyway and OpenRouter remaps to the nearest supported value upstream. A warning is logged server-side.

## Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Coverage
pytest tests/ --cov=app --cov-report=html

# Security tests only
pytest tests/test_security.py -v
```

### Security Scanning

```bash
bandit -r app/ -ll
pipx install safety && safety check
```

## Project Structure

```
.
├── main.py                       # FastAPI application entry point
├── app/
│   ├── __init__.py
│   ├── config.py                 # Env vars, model metadata, slug map
│   ├── dependencies.py           # Lifespan-managed pooled HTTP session
│   ├── models.py                 # Pydantic request/response models
│   ├── openrouter_client.py      # OpenRouter HTTP client + payload helpers
│   ├── security.py               # Auth, SSRF, security headers
│   ├── routes/
│   │   ├── health.py             # Health endpoint
│   │   └── generate.py           # /generate endpoint
│   └── utils/
│       ├── prompts.py            # Text + URL-fetched prompt loading
│       ├── images.py             # Image URL fetcher (SSRF + size guards)
│       └── tokens.py             # Token-count extraction
├── tests/                        # Pytest suite
├── requirements.txt
├── Dockerfile
├── .env.example
└── SECURITY.md
```

## Error Handling

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `400` | Bad request (invalid params, failed URL fetch, SSRF attempt, upstream rejection) |
| `403` | Authentication failed |
| `422` | Validation error (invalid input data) |
| `429` | Rate limit exceeded (or upstream rate limit) |
| `500` | Server error (config issue, malformed upstream response) |
| `502` | Upstream model unavailable |
| `503` | Upstream model temporarily unavailable / out of credits |
| `504` | Upstream model timeout |

Error response shape:

```json
{ "detail": "Error message here" }
```

## Health Check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "timestamp": "2024-03-20T10:00:00.123456",
  "uptime_seconds": 123.45,
  "model": "gemini-3-flash-preview",
  "version": "3.0.0"
}
```

## License

MIT

## Support

- [OpenRouter Docs](https://openrouter.ai/docs)
- [Google AI Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- Interactive API docs: `http://localhost:8000/docs`
