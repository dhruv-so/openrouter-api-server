"""
/api-cost endpoint.

Reports OpenRouter credit/usage state for the configured key. Combines two
upstream calls:

- GET /credits   → account-wide totals (purchased vs used)
- GET /key       → this key's spending limit and remaining headroom

Both calls go through the shared pooled session and use the same auth as
generation traffic.
"""

import logging

import requests
from fastapi import APIRouter, HTTPException

from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_TIMEOUT
from app.dependencies import get_http_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Cost"])


def _round3(value):
    """Round numeric values to 3 decimals. Pass through None."""
    if value is None:
        return None
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return value


def _get(path: str) -> dict:
    session = get_http_session()
    url = f"{OPENROUTER_BASE_URL.rstrip('/')}{path}"
    try:
        r = session.get(
            url,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            timeout=OPENROUTER_TIMEOUT,
        )
    except requests.Timeout:
        logger.error(f"OpenRouter timeout fetching {path}")
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except requests.RequestException as e:
        logger.error(f"OpenRouter error fetching {path}: {e}")
        raise HTTPException(status_code=502, detail="Upstream unavailable")

    if r.status_code >= 400:
        logger.error(f"OpenRouter HTTP {r.status_code} on {path}: {r.text[:300]}")
        raise HTTPException(status_code=502, detail="Upstream returned error")

    try:
        return r.json().get("data", {})
    except ValueError:
        logger.error(f"OpenRouter non-JSON response on {path}: {r.text[:300]}")
        raise HTTPException(status_code=500, detail="Invalid upstream response")


@router.get("/credits")
def credits() -> dict:
    """Report OpenRouter credit balance + this key's remaining headroom.

    Public — no auth required. Surfaces only non-sensitive aggregate
    USD figures. The key label upstream is already redacted by OpenRouter
    (e.g. "sk-or-v1-ce5...592"); we pass it through verbatim. All numeric
    values are rounded to 3 decimal places.

    Shape:
      {
        "account": { "total_credits", "total_usage", "balance" },
        "key":     { "label", "limit", "limit_remaining", "usage",
                     "usage_daily", "usage_weekly", "usage_monthly",
                     "is_free_tier" },
        "currency": "USD"
      }
    """
    credits_data = _get("/credits")
    key_data = _get("/key")

    total_credits = credits_data.get("total_credits") or 0
    total_usage = credits_data.get("total_usage") or 0
    balance = total_credits - total_usage

    return {
        "account": {
            "total_credits": _round3(total_credits),
            "total_usage": _round3(total_usage),
            "balance": _round3(balance),
        },
        "key": {
            "label": key_data.get("label"),
            "limit": _round3(key_data.get("limit")),
            "limit_remaining": _round3(key_data.get("limit_remaining")),
            "usage": _round3(key_data.get("usage")),
            "usage_daily": _round3(key_data.get("usage_daily")),
            "usage_weekly": _round3(key_data.get("usage_weekly")),
            "usage_monthly": _round3(key_data.get("usage_monthly")),
            "is_free_tier": key_data.get("is_free_tier"),
        },
        "currency": "USD",
    }
