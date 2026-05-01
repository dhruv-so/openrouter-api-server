"""
Pydantic models for request and response validation.
"""

from typing import Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator, HttpUrl


class PromptType(str, Enum):
    """Valid prompt types."""
    TEXT = "text"
    FILE = "file"


class GenerateRequest(BaseModel):
    """Request model for /generate endpoint (JSON)."""
    user_prompt: str = Field(
        ...,
        description="User's prompt (text or file URL)",
        min_length=1,
        max_length=100000,
    )
    user_prompt_type: PromptType = Field(
        PromptType.TEXT,
        description="Type of user_prompt: 'text' or 'file'",
    )
    system_prompt: str | None = Field(
        None,
        description="System instruction (text or file URL)",
        max_length=100000,
    )
    system_prompt_type: PromptType = Field(
        PromptType.TEXT,
        description="Type of system_prompt: 'text' or 'file'",
    )
    image_urls: list[HttpUrl] | None = Field(
        None,
        description="List of image URLs (max 10)",
        max_length=10,
    )
    json_schema: dict | None = Field(
        None,
        description="JSON schema for structured output",
    )
    model: str | None = Field(
        None,
        description="Model name: 'gemini-3-pro-preview' or 'gemini-3-flash-preview' (default: gemini-3-flash-preview)",
    )
    thinking_level: str = Field(
        "high",
        description=(
            "Thinking effort: 'minimal' | 'low' | 'medium' | 'high' "
            "(case-insensitive). Pro currently honors only 'low'/'high'; Flash "
            "honors all four. Unsupported levels are remapped upstream."
        ),
    )

    @field_validator('user_prompt')
    @classmethod
    def validate_user_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError("User prompt cannot be empty or whitespace")
        return v.strip()

    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v):
        if v is not None and not v.strip():
            raise ValueError("System prompt cannot be empty or whitespace")
        return v.strip() if v else None

    @field_validator('model')
    @classmethod
    def validate_model(cls, v):
        if v is not None:
            valid_models = ["gemini-3-pro-preview", "gemini-3-flash-preview"]
            if v not in valid_models:
                raise ValueError(f"Invalid model. Must be one of: {', '.join(valid_models)}")
        return v


class GenerateResponse(BaseModel):
    """Response model for /generate endpoint."""
    output: Union[dict, list, str]
    input_tokens: int
    output_tokens: int
    total_tokens: int


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""
    status: str = Field(..., description="Health status: 'healthy' or 'unhealthy'")
    timestamp: str = Field(..., description="Current server timestamp")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    model: str = Field(..., description="Model name")
    version: str = Field(..., description="API version")
