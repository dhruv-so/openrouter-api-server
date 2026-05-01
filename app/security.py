"""
Security utilities for authentication, URL validation, and SSRF protection.
"""

import os
import ipaddress
import logging
from urllib.parse import urlparse
from typing import Optional

from fastapi import Security, HTTPException, Request
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# ============================================================================
# AUTHENTICATION
# ============================================================================

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """Verify API key for authentication.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        str: Validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    server_api_key = os.getenv("SERVER_API_KEY")
    
    if not server_api_key:
        logger.error("SERVER_API_KEY not configured")
        raise HTTPException(
            status_code=500,
            detail="Server authentication not configured"
        )
    
    if not api_key:
        raise HTTPException(
            status_code=403,
            detail="Missing API key. Include X-API-Key header."
        )
    
    if api_key != server_api_key:
        logger.warning(f"Invalid API key attempt from client")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return api_key


# ============================================================================
# SSRF PROTECTION
# ============================================================================

# Allowed URL schemes
ALLOWED_SCHEMES = ["http", "https"]

# Blocked hostnames and IPs
BLOCKED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",  # nosec B104 - This is blocking the IP, not binding to it
    "::1",
    "169.254.169.254",  # AWS/GCP metadata
    "metadata.google.internal",  # GCP metadata
]


def validate_url(url) -> bool:
    """Validate URL to prevent SSRF attacks.
    
    Args:
        url: URL to validate (string or Pydantic HttpUrl)
        
    Returns:
        bool: True if URL is valid and safe
        
    Raises:
        HTTPException: If URL is invalid or potentially malicious
    """
    try:
        # Convert HttpUrl to string if needed (Pydantic HttpUrl objects)
        url_str = str(url)
        
        parsed = urlparse(url_str)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL scheme. Only {', '.join(ALLOWED_SCHEMES)} allowed."
            )
        
        # Check hostname exists
        hostname = parsed.hostname
        if not hostname:
            raise HTTPException(
                status_code=400,
                detail="Invalid URL: missing hostname"
            )
        
        # Check against blocked hosts
        if hostname.lower() in BLOCKED_HOSTS:
            logger.warning(f"Blocked URL attempt: {url_str}")
            raise HTTPException(
                status_code=400,
                detail="Access to this URL is not allowed"
            )
        
        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            
            # Block private, loopback, and link-local IPs
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                logger.warning(f"Blocked private IP attempt: {url_str}")
                raise HTTPException(
                    status_code=400,
                    detail="Access to private IP addresses is not allowed"
                )
            
            # Block multicast and reserved IPs
            if ip.is_multicast or ip.is_reserved:
                logger.warning(f"Blocked reserved IP attempt: {url_str}")
                raise HTTPException(
                    status_code=400,
                    detail="Access to this IP address is not allowed"
                )
                
        except ValueError:
            # Not an IP address, it's a hostname - that's OK
            pass
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL validation error for {url}: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid URL format"
        )


# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses.
    
    Args:
        request: FastAPI request
        call_next: Next middleware in chain
        
    Returns:
        Response with security headers
    """
    response = await call_next(request)
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # XSS protection (legacy browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # HSTS (only if using HTTPS)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Content Security Policy
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class APIError(Exception):
    """Base API error."""
    pass


class ValidationError(APIError):
    """Input validation error."""
    pass


class ExternalServiceError(APIError):
    """External service error."""
    pass


class AuthenticationError(APIError):
    """Authentication error."""
    pass
