# Deployment & Docker Guide

## Docker Deployment

### Building the Image

```bash
docker build -t gemini-api .
```

### Running the Container

**Basic:**

```bash
docker run -p 8000:8000 \
  -e OPENROUTER_API_KEY=sk-or-... \
  -e SERVER_API_KEY=your-server-api-key \
  -e ALLOWED_ORIGINS=http://localhost:3000 \
  gemini-api
```

**With env file:**

```bash
docker run -p 8000:8000 --env-file .env gemini-api
```

### Docker Compose (Optional)

```yaml
version: "3.8"

services:
  gemini-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - SERVER_API_KEY=${SERVER_API_KEY}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    restart: unless-stopped
```

```bash
docker-compose up -d
```

## Cloud Deployment

Any Docker host works:

- Google Cloud Run
- AWS ECS / Fargate
- Azure Container Instances
- DigitalOcean App Platform
- Railway
- Render

### Example: Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/gemini-api

gcloud run deploy gemini-api \
  --image gcr.io/YOUR_PROJECT_ID/gemini-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENROUTER_API_KEY=sk-or-...,SERVER_API_KEY=...,ALLOWED_ORIGINS=https://your-frontend.example
```

## Files Included in Docker Image

- `main.py` — FastAPI entry point
- `app/` — full application package (config, dependencies, models, routes, utils, openrouter_client, security)

## Files Excluded (.dockerignore)

- `__pycache__/` and compiled Python files
- `.env` and environment files (pass via `-e` / `--env-file`)
- Test files (`tests/`, `test_*.py`)
- Documentation (`*.md`)
- IDE / Git files

## Health Check

```bash
curl https://your-deployment-url.com/health
```

## Production Recommendations

1. **Use secrets management** for `OPENROUTER_API_KEY` and `SERVER_API_KEY` rather than plain env vars.
2. **Set tight `ALLOWED_ORIGINS`** — never `*` in production.
3. **Tune `RATE_LIMIT`** for your traffic profile.
4. **Monitor token usage** via OpenRouter dashboard to control cost.
5. **Set up logging** and error tracking (Sentry, etc.).
6. **Enforce HTTPS** at your reverse proxy (HSTS header is set automatically when the request scheme is `https`).
