import logging
import os
import json
import hashlib
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import base64
import requests
from io import BytesIO

from PIL import Image
import pytesseract

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai.ai import AI
from codx.junior.model.model import (
    ImageGenerationRequest,
    ImageAnalysisRequest,
    ImageMetadata,
    ImageGenerationResponse,
    ImageAnalysisResponse,
)
from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)


class ImageEngine:
    """
    Centralized engine for all image operations: generation and vision analysis.
    
    Responsibilities:
    - Image generation via DALL-E (3 & 2)
    - Image vision analysis via GPT-4 Vision
    - Image storage and lifecycle management
    - Metadata tracking
    - OCR (kept as-is from FileEngine)
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        user: Optional[CodxUser] = None,
    ):
        """
        Initialize the Image Engine.

        Args:
            settings: Project settings containing image configuration.
            user: Optional user context for analytics.
        """
        self.settings = settings
        self.user = user
        self.ai = self._build_ai()
        self.images_folder = self._init_images_folder()
        self.metadata_file = os.path.join(
            self.images_folder, "generated", "metadata.json"
        )
        
        logger.info(
            "ImageEngine initialized: folder=%s, generation=%s, vision=%s",
            self.images_folder,
            settings.is_image_generation_enabled(),
            settings.is_image_vision_enabled(),
        )

    def _build_ai(self) -> AI:
        """Build an AI instance for image operations."""
        from codx.junior import build_ai
        return build_ai(settings=self.settings, user=self.user)

    def _init_images_folder(self) -> str:
        """Initialize and return the images folder path."""
        # Determine storage folder based on settings or environment
        storage_folder = getattr(
            self.settings, 
            "CODX_JUNIOR_STATIC_FOLDER", 
            os.path.join(self.settings.abs_project_path, ".codx", "static")
        )
        images_path = os.path.join(storage_folder, "images")
        
        # Create necessary subdirectories
        os.makedirs(os.path.join(images_path, "generated"), exist_ok=True)
        os.makedirs(os.path.join(images_path, "message"), exist_ok=True)
        
        return images_path

    # ────────────────────────────────────────────────────────────────────────
    # IMAGE GENERATION
    # ────────────────────────────────────────────────────────────────────────

    async def generate_image(
        self,
        request: ImageGenerationRequest,
        chat_id: Optional[str] = None,
    ) -> ImageGenerationResponse:
        """
        Generate an image from a text prompt using DALL-E.

        Args:
            request: ImageGenerationRequest with prompt, size, quality, etc.
            chat_id: Optional chat identifier for analytics.

        Returns:
            ImageGenerationResponse with generated image details.

        Raises:
            ValueError: If generation is disabled or validation fails.
            RuntimeError: If image generation API fails.
        """
        if not self.settings.is_image_generation_enabled():
            raise ValueError("Image generation is disabled in project settings")

        # Validate request
        self._validate_generation_request(request)

        try:
            logger.info(
                "Generating image: model=%s, size=%s, prompt_length=%d",
                self.settings.image_generation_model,
                request.size,
                len(request.prompt),
            )

            # Call OpenAI DALL-E via AI module
            image_url = await self._call_dalle(
                prompt=request.prompt,
                size=request.size,
                quality=request.quality,
                style=request.style,
            )

            # Download and save image locally
            image_bytes, image_hash = await self._download_and_hash_image(
                image_url
            )

            # Save image file
            filename = f"{image_hash}.png"
            image_path = os.path.join(
                self.images_folder, "generated", filename
            )
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # Create metadata
            metadata = ImageMetadata(
                id=image_hash,
                filename=filename,
                path=f"images/generated/{filename}",
                url=f"/api/static/images/generated/{filename}",
                model=self.settings.image_generation_model,
                prompt=request.prompt,
                size=request.size,
                quality=request.quality,
                created_at=datetime.now(),
                created_by=self.user.username if self.user else "system",
                project_id=self.settings.project_id or "",
                status="success",
            )

            # Save metadata
            self._save_metadata(metadata)

            logger.info(
                "Image generated successfully: id=%s, file=%s",
                image_hash,
                filename,
            )

            return ImageGenerationResponse(
                status="success",
                image_id=image_hash,
                filename=filename,
                path=metadata.path,
                url=metadata.url,
                model=metadata.model,
                created_at=metadata.created_at,
                metadata=metadata,
            )

        except Exception as ex:
            logger.exception("Error generating image: %s", ex)
            raise RuntimeError(f"Image generation failed: {ex}")

    async def _call_dalle(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: Optional[str] = None,
    ) -> str:
        """
        Call DALL-E API via OpenAI client.

        Returns:
            URL of generated image.
        """
        openai_client = self.ai.get_openai_chat_client(
            llm_model=self.settings.image_generation_model
        )

        params = {
            "model": self.settings.image_generation_model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": 1,
        }

        # Add style only for DALL-E 3
        if self.settings.image_generation_model == "dall-e-3" and style:
            params["style"] = style

        response = openai_client.images.generate(**params)
        return response.data[0].url

    async def _download_and_hash_image(
        self,
        image_url: str,
    ) -> tuple:
        """
        Download image from URL and compute MD5 hash.

        Returns:
            Tuple of (image_bytes, md5_hash).
        """
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        image_bytes = response.content
        image_hash = hashlib.md5(image_bytes).hexdigest()

        return image_bytes, image_hash

    def _validate_generation_request(self, request: ImageGenerationRequest) -> None:
        """Validate image generation request parameters."""
        if not request.prompt or len(request.prompt.strip()) == 0:
            raise ValueError("Prompt cannot be empty")

        if len(request.prompt) > 4000:
            raise ValueError("Prompt exceeds maximum length (4000 characters)")

        valid_sizes = ["256x256", "512x512", "1024x1024", "1024x1792", "1792x1024"]
        if request.size not in valid_sizes:
            raise ValueError(f"Invalid size. Must be one of: {valid_sizes}")

        if request.quality not in ["standard", "hd"]:
            raise ValueError("Quality must be 'standard' or 'hd'")

        if request.n < 1 or request.n > 10:
            raise ValueError("Number of images must be between 1 and 10")

    # ────────────────────────────────────────────────────────────────────────
    # IMAGE VISION (ANALYSIS)
    # ────────────────────────────────────────────────────────────────────────

    async def analyze_image(
        self,
        request: ImageAnalysisRequest,
        chat_id: Optional[str] = None,
    ) -> ImageAnalysisResponse:
        """
        Analyze an image using GPT-4 Vision API.

        Args:
            request: ImageAnalysisRequest with image_url and query.
            chat_id: Optional chat identifier for analytics.

        Returns:
            ImageAnalysisResponse with analysis results.

        Raises:
            ValueError: If vision is disabled or validation fails.
            RuntimeError: If analysis API fails.
        """
        if not self.settings.is_image_vision_enabled():
            raise ValueError("Image vision is disabled in project settings")

        # Validate request
        self._validate_analysis_request(request)

        try:
            logger.info(
                "Analyzing image: model=%s, detail=%s, query_length=%d",
                self.settings.image_vision_model,
                request.detail,
                len(request.query),
            )

            # Build vision API request
            analysis = await self._call_vision_api(
                image_url=request.image_url,
                query=request.query,
                detail=request.detail,
            )

            logger.info(
                "Image analysis completed: model=%s, response_length=%d",
                self.settings.image_vision_model,
                len(analysis),
            )

            return ImageAnalysisResponse(
                status="success",
                query=request.query,
                analysis=analysis,
                image_url=request.image_url,
                model=self.settings.image_vision_model,
                timestamp=datetime.now(),
            )

        except Exception as ex:
            logger.exception("Error analyzing image: %s", ex)
            raise RuntimeError(f"Image analysis failed: {ex}")

    async def _call_vision_api(
        self,
        image_url: str,
        query: str,
        detail: str = "auto",
    ) -> str:
        """
        Call GPT-4 Vision API via OpenAI client.

        Returns:
            Analysis text from the model.
        """
        openai_client = self.ai.get_openai_chat_client(
            llm_model=self.settings.image_vision_model
        )

        # Build vision message with image
        message = {
            "type": "text",
            "text": query,
        }

        # Handle both URLs and base64-encoded images
        if image_url.startswith("http"):
            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                    "detail": detail,
                },
            }
        else:
            # Assume base64 encoded
            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_url}",
                    "detail": detail,
                },
            }

        response = openai_client.chat.completions.create(
            model=self.settings.image_vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [message, image_content],
                }
            ],
            max_tokens=2048,
        )

        return response.choices[0].message.content

    def _validate_analysis_request(self, request: ImageAnalysisRequest) -> None:
        """Validate image analysis request parameters."""
        if not request.image_url:
            raise ValueError("Image URL is required")

        if not request.query or len(request.query.strip()) == 0:
            raise ValueError("Query cannot be empty")

        if len(request.query) > 4000:
            raise ValueError("Query exceeds maximum length (4000 characters)")

        if request.detail not in ["auto", "low", "high"]:
            raise ValueError("Detail must be 'auto', 'low', or 'high'")

    # ────────────────────────────────────────────────────────────────────────
    # IMAGE STORAGE & METADATA
    # ────────────────────────────────────────────────────────────────────────

    def _save_metadata(self, metadata: ImageMetadata) -> None:
        """Save image metadata to JSON file."""
        try:
            # Load existing metadata
            all_metadata = self._load_all_metadata()

            # Add new metadata
            all_metadata["images"].append(metadata.model_dump(mode="json"))

            # Save back to file
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            with open(self.metadata_file, "w") as f:
                json.dump(all_metadata, f, indent=2)

        except Exception as ex:
            logger.warning("Failed to save image metadata: %s", ex)

    def _load_all_metadata(self) -> Dict[str, Any]:
        """Load all image metadata from JSON file."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            except Exception as ex:
                logger.warning("Failed to load metadata: %s", ex)

        return {"images": []}

    def get_image_metadata(self, image_id: str) -> Optional[ImageMetadata]:
        """Retrieve metadata for a specific image."""
        all_data = self._load_all_metadata()
        for img in all_data.get("images", []):
            if img.get("id") == image_id:
                return ImageMetadata(**img)
        return None

    def list_generated_images(self) -> List[ImageMetadata]:
        """List all generated images with metadata."""
        all_data = self._load_all_metadata()
        return [
            ImageMetadata(**img)
            for img in all_data.get("images", [])
            if img.get("status") == "success"
        ]

    def delete_image(self, image_id: str) -> bool:
        """Delete an image file and its metadata."""
        try:
            metadata = self.get_image_metadata(image_id)
            if not metadata:
                logger.warning("Image not found: %s", image_id)
                return False

            # Delete file
            image_path = os.path.join(self.settings.abs_project_path, metadata.path)
            if os.path.exists(image_path):
                os.remove(image_path)
                logger.info("Deleted image file: %s", image_path)

            # Remove from metadata
            all_data = self._load_all_metadata()
            all_data["images"] = [
                img for img in all_data.get("images", [])
                if img.get("id") != image_id
            ]

            with open(self.metadata_file, "w") as f:
                json.dump(all_data, f, indent=2)

            return True

        except Exception as ex:
            logger.exception("Error deleting image %s: %s", image_id, ex)
            return False

    # ────────────────────────────────────────────────────────────────────────
    # OCR (KEPT AS-IS)
    # ────────────────────────────────────────────────────────────────────────

    def extract_text_ocr(self, image_bytes: bytes) -> str:
        """
        Extract text from image using Tesseract OCR.

        Args:
            image_bytes: Image file bytes.

        Returns:
            Extracted text string.
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            logger.debug("OCR extracted %d characters", len(text))
            return text
        except Exception as ex:
            logger.exception("Error extracting text from image: %s", ex)
            raise RuntimeError(f"OCR failed: {ex}")