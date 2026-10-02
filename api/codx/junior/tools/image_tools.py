"""
Image tools for chat interactions.

This module provides tools for image operations:
- explain_image: Detailed image analysis using Vision API
- generate_image: Image generation using DALL-E

Made with ❤️ by codx-junior
"""

import logging
import base64
from typing import Optional

from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine.image_engine import ImageEngine
from codx.junior.model.image_model import ImageAnalysisRequest, ImageGenerationRequest
from codx.junior.model.model import CodxUser

# Configure logging
logger = logging.getLogger(__name__)


def explain_image(image_base64: str, **kwargs) -> str:
    """
    Provide a detailed analysis of an image using Vision API.

    Analyzes the base64-encoded image and returns a comprehensive description
    of its content, visual elements, and context.

    Args:
        image_base64: Base64-encoded image content (PNG, JPG, etc.)
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required)
            - user (CodxUser): User context (optional)

    Returns:
        str: Detailed image analysis and description

    Raises:
        ValueError: If image is invalid or vision is disabled
        Exception: If project settings are not provided

    Example:
        >>> explain_image("iVBORw0KGgoAAAANSUhEUgA...", settings=settings)
        # Returns: "This image shows a futuristic cityscape at sunset..."
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    user: CodxUser = kwargs.get("user", None)

    if not image_base64 or not isinstance(image_base64, str):
        raise ValueError("image_base64 must be a non-empty string")

    # Remove data URI prefix if present
    if image_base64.startswith("data:image"):
        image_base64 = image_base64.split(",", 1)[1]

    try:
        # Validate base64
        base64.b64decode(image_base64, validate=True)
    except Exception as e:
        raise ValueError(f"Invalid base64 image: {str(e)}")

    try:
        # Create analysis request with detailed prompt
        analysis_request = ImageAnalysisRequest(
            image_url=image_base64,
            query="Provide a detailed and comprehensive analysis of this image. Describe: 1) Main subjects and objects visible, 2) Composition and layout, 3) Colors and visual style, 4) Any text or symbols, 5) Context and setting, 6) Notable details and patterns.",
            detail="high"
        )

        image_engine = ImageEngine(settings=settings, user=user)
        response = image_engine.analyze_image(analysis_request)

        logger.info("Image explained successfully")
        return response.analysis

    except ValueError as e:
        logger.warning("Image analysis validation error: %s", e)
        raise ValueError(f"Image analysis failed: {str(e)}")
    except RuntimeError as e:
        logger.error("Image analysis runtime error: %s", e)
        raise RuntimeError(f"Image analysis failed: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error in image explanation: %s", e)
        raise Exception(f"Image analysis failed: {str(e)}")


def generate_image(prompt: str, **kwargs) -> str:
    """
    Generate an image from a text prompt using DALL-E.

    Creates a new image based on the provided prompt and stores it in the project.
    Returns the relative URL path to the generated image.

    Args:
        prompt: Text description of the image to generate
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required)
            - user (CodxUser): User context (optional)
            - size (str): Image size, default "1024x1024"
            - quality (str): "standard" or "hd", default "standard"

    Returns:
        str: Relative URL path to the generated image (e.g., "/images/project-123/abc123.png")

    Raises:
        ValueError: If prompt is invalid or generation is disabled
        Exception: If project settings are not provided

    Example:
        >>> generate_image("A futuristic city at sunset", settings=settings)
        # Returns: "/images/project-123/a1b2c3d4.png"
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    user: CodxUser = kwargs.get("user", None)
    size: str = kwargs.get("size", "1024x1024")
    quality: str = kwargs.get("quality", "standard")

    if not prompt or not isinstance(prompt, str):
        raise ValueError("prompt must be a non-empty string")

    if len(prompt.strip()) == 0:
        raise ValueError("prompt cannot be empty or whitespace only")

    try:
        # Create generation request
        generation_request = ImageGenerationRequest(
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
            style="vivid"
        )

        image_engine = ImageEngine(settings=settings, user=user)
        response = image_engine.generate_image(generation_request)

        # Build relative URL path
        project_id = settings.project_id or "default"
        relative_url = f"/images/{project_id}/{response.image_id}"

        logger.info("Image generated successfully: url=%s", relative_url)
        return relative_url

    except ValueError as e:
        logger.warning("Image generation validation error: %s", e)
        raise ValueError(f"Image generation failed: {str(e)}")
    except RuntimeError as e:
        logger.error("Image generation runtime error: %s", e)
        raise RuntimeError(f"Image generation failed: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error in image generation: %s", e)
        raise Exception(f"Image generation failed: {str(e)}")

# Made with ❤️ by codx-junior