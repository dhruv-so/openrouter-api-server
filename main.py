"""
Gemini 3.0 Pro API Server

A FastAPI server that exposes Google's Gemini 3.0 Pro model as a REST API
with support for flexible prompt sources, binary image uploads, structured
JSON outputs, and configurable thinking levels.
"""

import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.dependencies import lifespan
from app.routes import health, generate, curl_examples
from app.config import ALLOWED_ORIGINS
from app.security import add_security_headers

logger = logging.getLogger(__name__)

# ============================================================================
# RATE LIMITING
# ============================================================================

limiter = Limiter(key_func=get_remote_address)

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Gemini 3.0 Pro API Server",
    version="3.0.0",
    description="API server for Gemini 3.0 Pro with thinking capabilities and flexible prompt/image handling",
    lifespan=lifespan
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security headers middleware
app.middleware("http")(add_security_headers)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add CORS middleware with environment-based configuration
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
    logger.info(f"CORS enabled for origins: {', '.join(ALLOWED_ORIGINS)}")
else:
    logger.warning("CORS not configured - no origins allowed")

# Include routers
app.include_router(health.router)
app.include_router(generate.router)
app.include_router(curl_examples.router)

# ============================================================================
# CUSTOM EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom handler for HTTP exceptions with logging."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Custom handler for unexpected exceptions with logging."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )