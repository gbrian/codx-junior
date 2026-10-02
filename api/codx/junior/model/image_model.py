"""
Image generation and vision model types.

This module defines Pydantic models for all image-related operations:
- Image generation requests and responses
- Image vision/analysis requests and responses
- Image metadata storage and tracking
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""
    prompt: str = Field(description="Text prompt for image generation")
    size: str = Field(default="1024x1024", description="Image size: 256x256, 512x512, 1024x1024, 1024x1792, 1792x1024")
    quality: str = Field(default="standard", description="standard or hd")
    n: int = Field(default=1, ge=1, le=10, description="Number of images (1-10)")
    style: Optional[str] = Field(default="vivid", description="vivid or natural (DALL-E 3 only)")


class ImageAnalysisRequest(BaseModel):
    """Request model for image analysis/vision."""
    image_url: str = Field(description="URL or base64 encoded image")
    query: str = Field(description="Question or analysis request about the image")
    detail: str = Field(default="auto", description="auto, low, or high image detail level")


class ImageMetadata(BaseModel):
    """Metadata for a generated image."""
    id: str = Field(description="Unique image identifier (MD5 hash)")
    filename: str = Field(description="Saved filename")
    path: str = Field(description="Relative path from project root")
    url: str = Field(description="Accessible URL")
    model: str = Field(description="Model used for generation")
    prompt: str = Field(description="Original prompt")
    size: str = Field(description="Image dimensions")
    quality: str = Field(description="Quality setting")
    created_at: datetime = Field(description="Generation timestamp")
    created_by: str = Field(description="User who generated")
    project_id: str = Field(description="Associated project")
    status: str = Field(description="success, failed, or processing")
    error_message: Optional[str] = Field(default=None, description="Error if status=failed")


class ImageGenerationResponse(BaseModel):
    """Response from image generation."""
    status: str = Field(description="success or error")
    image_id: str = Field(description="Unique identifier")
    filename: str = Field(description="Saved filename")
    path: str = Field(description="Relative path")
    url: str = Field(description="Accessible URL")
    model: str = Field(description="Model used")
    created_at: datetime = Field(description="Timestamp")
    metadata: ImageMetadata = Field(description="Full metadata")


class ImageAnalysisResponse(BaseModel):
    """Response from image analysis."""
    status: str = Field(description="success or error")
    query: str = Field(description="Original query")
    analysis: str = Field(description="Analysis result")
    image_url: str = Field(description="Analyzed image URL")
    model: str = Field(description="Model used")
    timestamp: datetime = Field(description="Analysis timestamp")

# Made with ❤️ by codx-junior