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
from fastapi import APIRouter, Depends, HTTPException

from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_TIMEOUT
from app.dependencies import get_http_session
from app.security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Cost"])


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
def credits(api_key: str = Depends(verify_api_key)) -> dict:
    """Report OpenRouter credit balance + this key's remaining headroom.

    Auth: requires X-API-Key (same as /generate).

    Returns combined snapshot:
      {
        "account": { "total_credits", "total_usage", "balance" },
        "key":     { "limit", "limit_remaining", "usage", "usage_daily",
                     "usage_weekly", "usage_monthly", "label" },
        "currency": "USD"
      }
    """
    credits_data = _get("/credits")
    key_data = _get("/key")

    total_credits = credits_data.get("total_credits") or 0
    total_usage = credits_data.get("total_usage") or 0
    balance = round(total_credits - total_usage, 6)

    return {
        "account": {
            "total_credits": total_credits,
            "total_usage": round(total_usage, 6),
            "balance": balance,
        },
        "key": {
            "label": key_data.get("label"),
            "limit": key_data.get("limit"),
            "limit_remaining": key_data.get("limit_remaining"),
            "usage": key_data.get("usage"),
            "usage_daily": key_data.get("usage_daily"),
            "usage_weekly": key_data.get("usage_weekly"),
            "usage_monthly": key_data.get("usage_monthly"),
            "is_free_tier": key_data.get("is_free_tier"),
        },
        "currency": "USD",
    }
