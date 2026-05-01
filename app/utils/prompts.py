"""
Prompt loading and processing utilities.

Handles loading prompts from text or file URLs with size validation.
"""

import logging
import requests
from fastapi import HTTPException

from app.config import MAX_PROMPT_SIZE, REQUEST_TIMEOUT
from app.dependencies import get_http_session
from app.security import validate_url

logger = logging.getLogger(__name__)


def load_content_from_source(content: str, content_type: str, max_size: int = MAX_PROMPT_SIZE) -> str:
    """Load content from text or file URL.
    
    Args:
        content: Either plain text or a URL
        content_type: "text" or "file"
        max_size: Maximum allowed size in bytes
    
    Returns:
        str: The content
        
    Raises:
        HTTPException: If loading fails or content exceeds max_size
    """
    if content_type == "text":
        if len(content.encode('utf-8')) > max_size:
            raise HTTPException(
                status_code=400, 
                detail=f"Text content exceeds maximum size of {max_size} bytes"
            )
        return content
    
    elif content_type == "file":
        # Validate URL to prevent SSRF
        validate_url(content)
        
        try:
            http_session = get_http_session()
            
            # Stream the response to check size before loading
            response = http_session.get(content, timeout=REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Check content length
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size ({content_length} bytes) exceeds maximum of {max_size} bytes"
                )
            
            # Read content in chunks to avoid memory issues
            chunks = []
            total_size = 0
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    total_size += len(chunk.encode('utf-8'))
                    if total_size > max_size:
                        raise HTTPException(
                            status_code=400,
                            detail=f"File content exceeds maximum size of {max_size} bytes"
                        )
                    chunks.append(chunk)
            
            return ''.join(chunks)
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch file from {content}: {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to fetch file from URL: {str(e)}"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content_type: {content_type}. Must be 'text' or 'file'"
        )
