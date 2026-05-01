"""
Configuration module for Gemini 3.0 API Server.

Generation traffic flows through OpenRouter's OpenAI-compatible chat
completions endpoint; this file owns env loading and model metadata.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

# ============================================================================
# OPENROUTER CONFIGURATION
# ============================================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set in env or .env")

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_REFERER = os.getenv("OPENROUTER_REFERER", "")
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "Gemini-3 API Server")
OPENROUTER_TIMEOUT = int(os.getenv("OPENROUTER_TIMEOUT", "60"))

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

SERVER_API_KEY = os.getenv("SERVER_API_KEY")
if not SERVER_API_KEY:
    logger.warning("SERVER_API_KEY not set - API will be unauthenticated!")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []
if not ALLOWED_ORIGINS:
    logger.warning("ALLOWED_ORIGINS not set - CORS will block all origins")

RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Public-facing default model name (clients send this; server remaps to OpenRouter slug at call time).
MODEL_NAME = "gemini-3-flash-preview"

SUPPORTED_MODELS = [
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
]

# Per-model thinking levels officially honored by Google. Client may pass any
# of {minimal, low, medium, high}; if the level isn't in this list for the
# selected model, OpenRouter remaps to the nearest supported value.
THINKING_LEVELS = {
    "gemini-3-pro-preview": ["low", "high"],
    "gemini-3-flash-preview": ["minimal", "low", "medium", "high"],
}

# Public model name → OpenRouter slug. Remap happens only at OpenRouter call time
# so the public API contract (and /health.model) stays unchanged.
MODEL_SLUG_MAP = {
    "gemini-3-pro-preview": "google/gemini-3-pro-preview",
    "gemini-3-flash-preview": "google/gemini-3-flash-preview",
}

# ============================================================================
# FILE SIZE LIMITS
# ============================================================================

MAX_PROMPT_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_SIZE = 20 * 1024 * 1024   # 20MB

# ============================================================================
# GENERATION DEFAULTS
# ============================================================================

DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "1.0"))
DEFAULT_TOP_P = float(os.getenv("DEFAULT_TOP_P", "0.95"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("DEFAULT_MAX_OUTPUT_TOKENS", "12000"))
