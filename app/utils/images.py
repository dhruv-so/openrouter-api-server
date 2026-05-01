"""
Image loading and processing utilities.

Handles both URL-based image downloads and binary file uploads.
"""

import logging
import mimetypes
import requests
from fastapi import HTTPException, UploadFile

from app.config import MAX_IMAGE_SIZE, REQUEST_TIMEOUT
from app.dependencies import get_http_session
from app.security import validate_url

logger = logging.getLogger(__name__)


def load_image_from_url(url: str) -> tuple[bytes, str]:
    """Download image from URL and return bytes with MIME type.
    
    Args:
        url: Image URL to download
        
    Returns:
        tuple: (image_bytes, mime_type)
        
    Raises:
        HTTPException: If image download fails or exceeds size limit
    """
    # Validate URL to prevent SSRF
    validate_url(url)
    
    try:
        http_session = get_http_session()
        response = http_session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()
        
        # Check content length
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Image size ({content_length} bytes) exceeds maximum of {MAX_IMAGE_SIZE} bytes"
            )
        
        # Read image in chunks
        chunks = []
        total_size = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                total_size += len(chunk)
                if total_size > MAX_IMAGE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Image exceeds maximum size of {MAX_IMAGE_SIZE} bytes"
                    )
                chunks.append(chunk)
        
        image_bytes = b''.join(chunks)
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch image from {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")

    # Determine MIME type
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
    mime_type = content_type if content_type.startswith("image/") else None

    if not mime_type:
        guessed, _ = mimetypes.guess_type(url)
        mime_type = guessed if guessed and guessed.startswith("image/") else "image/jpeg"

    return image_bytes, mime_type


async def process_binary_image(file: UploadFile) -> tuple[bytes, str]:
    """Process uploaded binary image file.
    
    Args:
        file: Uploaded file from FastAPI
        
    Returns:
        tuple: (image_bytes, mime_type)
        
    Raises:
        HTTPException: If file is too large or invalid
    """
    # Validate MIME type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Must be an image."
        )
    
    # Read file in chunks to check size
    chunks = []
    total_size = 0
    
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Image exceeds maximum size of {MAX_IMAGE_SIZE} bytes"
            )
        chunks.append(chunk)
    
    image_bytes = b''.join(chunks)
    return image_bytes, file.content_type
