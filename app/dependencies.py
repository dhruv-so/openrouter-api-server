"""
Shared dependencies and lifespan management.

Manages the global pooled HTTP session used by both the prompt/image
loaders and the OpenRouter client, plus the application start time used
by the health endpoint.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging

import requests
from fastapi import FastAPI

logger = logging.getLogger(__name__)

http_session: requests.Session | None = None
app_start_time: datetime | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    global http_session, app_start_time

    logger.info("Starting Gemini 3.0 API Server...")
    app_start_time = datetime.now()

    http_session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=3,
    )
    http_session.mount("http://", adapter)
    http_session.mount("https://", adapter)
    logger.info("HTTP session initialized with connection pooling")
    logger.info("Generation routed via OpenRouter chat completions")

    yield

    logger.info("Shutting down Gemini 3.0 API Server...")
    if http_session:
        http_session.close()
        logger.info("HTTP session closed")


def get_http_session() -> requests.Session:
    """Return the global HTTP session."""
    if http_session is None:
        raise RuntimeError("HTTP session not initialized")
    return http_session


def get_app_start_time() -> datetime:
    """Return the application start time."""
    if app_start_time is None:
        raise RuntimeError("Application start time not set")
    return app_start_time
