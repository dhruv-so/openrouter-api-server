"""
Health check endpoint.

Reports server status, uptime, and configured default model. No live upstream
network call — too expensive for a /health probe.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.config import MODEL_NAME, OPENROUTER_API_KEY
from app.models import HealthResponse
from app import dependencies as deps
from app.dependencies import get_app_start_time

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Verify server is running and required state is initialized."""
    try:
        app_start_time = get_app_start_time()
        uptime = (datetime.now() - app_start_time).total_seconds()

        api_status = "healthy"
        if not OPENROUTER_API_KEY:
            api_status = "degraded"
            logger.warning("OPENROUTER_API_KEY missing")
        elif deps.http_session is None:
            api_status = "degraded"
            logger.warning("HTTP session not initialized")

        return HealthResponse(
            status=api_status,
            timestamp=datetime.now().isoformat(),
            uptime_seconds=uptime,
            model=MODEL_NAME,
            version="3.0.0",
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}",
        )
