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
from openai import OpenAI

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

# Sub folders created inside the project images folder
GENERATED_IMAGES_SUB_FOLDER = "generated"
MESSAGE_IMAGES_SUB_FOLDER = "message"


class ImageEngine:
    """
    Centralized engine for all image operations: generation and vision analysis.
    
    Responsibilities:
    - Image generation via DALL-E (3 & 2) or Gemini/Nano Banana
    - Image vision analysis via the configured vision model
    - Image storage and lifecycle management
    - Metadata tracking
    - OCR (kept as-is from FileEngine)

    Both image models are resolved by the settings (project value, or the global
    default when the project leaves it empty), so the engine never picks one
    capability's model for the other.

    Images are project resources: they are stored inside the project folder
    (``settings.images_folder``, ``.codx/images`` by default) and served by the
    images router (``/api/images/...``).
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
            self.images_folder, GENERATED_IMAGES_SUB_FOLDER, "metadata.json"
        )
        
        logger.info(
            "ImageEngine initialized: folder=%s, image_generation_model=%s, "
            "image_vision_model=%s",
            self.images_folder,
            settings.get_image_generation_model() or "<none>",
            settings.get_image_vision_model() or "<none>",
        )

    def _build_ai(self) -> AI:
        """
        Build an AI instance for image operations.

        ``build_ai`` is not always exported by the ``codx.junior`` package
        depending on the assembly, so the factory is resolved defensively and
        the ``AI`` class constructor is used as the fallback.
        """
        try:
            from codx.junior.ai.ai import build_ai  # type: ignore
            return build_ai(settings=self.settings, user=self.user)
        except Exception:
            logger.debug("build_ai factory not available, using AI()", exc_info=True)

        return AI(settings=self.settings, user=self.user)

    def _init_images_folder(self) -> str:
        """
        Initialize and return the project images folder path.

        The folder comes from the project settings (``images_folder``,
        ``.codx/images`` by default), so generated images are stored in the
        project itself and not in the global ``CODX_JUNIOR_STATIC_FOLDER``
        static mount shared by every project.

        Returns:
            Absolute path of the project images folder.
        """
        images_path = self.settings.get_images_folder_path()

        for sub_folder in (GENERATED_IMAGES_SUB_FOLDER, MESSAGE_IMAGES_SUB_FOLDER):
            os.makedirs(os.path.join(images_path, sub_folder), exist_ok=True)

        return images_path

    # ────────────────────────────────────────────────────────────────────────
    # IMAGE GENERATION
    # ────────────────────────────────────────────────────────────────────────

    def _resolve_chat_target(self, llm_model: str) -> tuple:
        """
        Resolve an OpenAI-compatible chat client and model name for a model.

        Args:
            llm_model: Configured model name (AIModel.name).

        Returns:
            Tuple of (OpenAI client, provider model name).
        """
        ai_settings = self.settings.get_llm_settings(llm_model=llm_model)
        client = OpenAI(api_key=ai_settings.api_key, base_url=ai_settings.api_url)
        return client, ai_settings.model

    def _is_gemini_image_model(self) -> bool:
        """
        Return True when the resolved image generation model is Gemini/Nano Banana.

        Nano Banana models (``gemini-*-image``) generate images through Google's
        ``models.generate_content`` endpoint, not through the OpenAI-compatible
        ``images.generate`` route used by DALL-E/Imagen.
        """
        model_name = (self.settings.get_image_generation_model() or "").lower()
        if "gemini" in model_name and "image" in model_name:
            return True
        if "nano banana" in model_name:
            return True

        try:
            image_settings = self.settings.get_image_generation_settings()
        except Exception:
            return False

        provider_type = (image_settings.provider_type or "").lower()
        model_type = getattr(image_settings.model_type, "value", None)
        return provider_type in ("google", "gemini", "vertex", "vertex_ai") and model_type == "image"

    async def _call_gemini_image(
        self,
        prompt: str,
        size: str = "1024x1024",
    ) -> tuple:
        """
        Generate an image with Gemini/Nano Banana via ``generateContent``.

        Returns:
            Tuple of (image_bytes, mime_type).
        """
        image_settings = self.settings.get_image_generation_settings()
        model_name = self.settings.get_image_generation_model()

        url = self._build_gemini_generate_content_url(image_settings, model_name)
        headers = self._build_gemini_headers(image_settings)
        payload = self._build_gemini_image_payload(prompt=prompt, size=size)

        logger.info(
            "Calling Gemini image generation: model=%s, url=%s",
            model_name,
            url,
        )

        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        return self._extract_gemini_image(response.json())

    @staticmethod
    def _build_gemini_generate_content_url(image_settings: Any, model_name: str) -> str:
        """
        Build the Google-native ``:generateContent`` URL.

        Supports both Google's direct Gemini API and a LiteLLM-compatible proxy:
        the latter exposes ``POST {proxy_root}/v1beta/models/{model}:generateContent``.
        """
        base_url = (getattr(image_settings, "api_url", "") or "").rstrip("/")
        if not base_url:
            base_url = "https://generativelanguage.googleapis.com"

        # Direct Google Gemini API.
        if "generativelanguage.googleapis.com" in base_url:
            if base_url.endswith("/v1beta"):
                return f"{base_url}/models/{model_name}:generateContent"
            if base_url.endswith("/v1"):
                base_url = base_url[:-3].rstrip("/")
            return f"{base_url}/v1beta/models/{model_name}:generateContent"

        # LiteLLM / OpenAI-compatible gateway. Resolve the Google-native route
        # from the proxy root, stripping any OpenAI-style version prefix such
        # as ``/v1`` or ``/v1main``.
        for prefix in ("/v1beta", "/v1main", "/v1"):
            if base_url.endswith(prefix):
                base_url = base_url[: -len(prefix)].rstrip("/")
                break

        return f"{base_url}/v1beta/models/{model_name}:generateContent"

    @staticmethod
    def _build_gemini_headers(image_settings: Any) -> Dict[str, str]:
        """Build request headers for the Gemini ``generateContent`` call."""
        headers = {"Content-Type": "application/json"}
        api_key = (getattr(image_settings, "api_key", "") or "").strip()
        api_url = (getattr(image_settings, "api_url", "") or "").lower()

        if api_key and "generativelanguage.googleapis.com" in api_url:
            headers["x-goog-api-key"] = api_key
        elif api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        return headers

    @staticmethod
    def _build_gemini_image_payload(prompt: str, size: str) -> Dict[str, Any]:
        """Build the ``GenerateContentRequest`` body for Nano Banana image generation."""
        aspect_ratio = {
            "256x256": "1:1",
            "512x512": "1:1",
            "1024x1024": "1:1",
            "1024x1792": "9:16",
            "1792x1024": "16:9",
        }.get(size)

        generation_config: Dict[str, Any] = {
            "responseModalities": ["IMAGE", "TEXT"],
        }
        if aspect_ratio:
            generation_config["imageConfig"] = {"aspectRatio": aspect_ratio}

        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": generation_config,
        }

    @staticmethod
    def _extract_gemini_image(data: Dict[str, Any]) -> tuple:
        """Extract the first inline image returned by Gemini ``generateContent``."""
        for candidate in data.get("candidates") or []:
            content = candidate.get("content") or {}
            for part in content.get("parts") or []:
                inline_data = part.get("inlineData") or part.get("inline_data") or {}
                image_data = inline_data.get("data")
                if not image_data:
                    continue

                padding = "=" * (-len(image_data) % 4)
                image_bytes = base64.b64decode(image_data + padding)
                mime_type = (
                    inline_data.get("mimeType")
                    or inline_data.get("mime_type")
                    or "image/png"
                )
                return image_bytes, mime_type

        raise RuntimeError(f"Gemini image generation returned no image data: {data}")

    @staticmethod
    def _extension_for_mime_type(mime_type: str) -> str:
        """Return the file extension used for a generated image MIME type."""
        return {
            "image/jpeg": "jpg",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/png": "png",
        }.get(mime_type or "", "png")

    async def adapt_image_prompt(self, prompt: str) -> str:
        """
        Review and adapt a user request into an optimized image prompt.

        The prompt is rewritten by the resolved image generation model
        (``settings.get_image_generation_model()``). Text rewriting is not
        supported by every image model, so the project's RAG/text model is used
        as a fallback and, if every model fails, the original prompt is
        returned.

        Args:
            prompt: Raw user request.

        Returns:
            The adapted prompt, or the original prompt when adaptation fails.
        """
        prompt = (prompt or "").strip()
        if not prompt:
            return prompt

        system_prompt = (
            "You are an expert prompt engineer for AI image generation. "
            "Review the user's request and rewrite it as a single, self-contained, "
            "highly descriptive image-generation prompt. Preserve the original intent. "
            "Add useful concrete details (subject, composition, framing, style, "
            "lighting, colors, mood) and avoid instructions, markdown or commentary. "
            "Return ONLY the final prompt."
        )

        candidates = [
            self.settings.get_image_generation_model(),
            self.settings.get_rag_model(),
        ]
        seen = set()
        for llm_model in candidates:
            if not llm_model or llm_model in seen:
                continue
            seen.add(llm_model)
            try:
                client, model_name = self._resolve_chat_target(llm_model)
                response = client.chat.completions.create(
                    model=model_name,
                    temperature=0.7,
                    max_tokens=600,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                )
                adapted = (
                    response.choices[0].message.content or ""
                ).strip().strip('"').strip()
                if adapted:
                    logger.info(
                        "Image prompt adapted with model '%s' (%d -> %d chars)",
                        llm_model,
                        len(prompt),
                        len(adapted),
                    )
                    return adapted
            except Exception as ex:
                logger.warning(
                    "adapt_image_prompt: model '%s' could not adapt the prompt, "
                    "trying fallback: %s",
                    llm_model,
                    ex,
                )

        logger.warning("adapt_image_prompt: using the original prompt")
        return prompt

    async def generate_image(
        self,
        request: ImageGenerationRequest,
        chat_id: Optional[str] = None,
    ) -> ImageGenerationResponse:
        """
        Generate an image from a text prompt using the configured image model.

        The model is resolved by the settings (project override, or the global
        default when the project leaves it empty). The image is downloaded and
        saved in the project images folder (``settings.images_folder``), and the
        returned metadata holds the project-relative path plus the URL served by
        the images router.

        Args:
            request: ImageGenerationRequest with prompt, size, quality, etc.
            chat_id: Optional chat identifier for analytics.

        Returns:
            ImageGenerationResponse with generated image details.

        Raises:
            ValueError: If generation is disabled or validation fails.
            RuntimeError: If image generation API fails.
        """
        image_generation_model = self.settings.get_image_generation_model()

        if not image_generation_model:
            raise ValueError(
                "Image generation is disabled: no image generation model "
                "configured. Set `image_generation_model` in the project "
                "settings or in the global settings (an AI model registered "
                "with model_type 'image')."
            )

        # Validate request
        self._validate_generation_request(request)

        try:
            logger.info(
                "Generating image: model=%s, size=%s, prompt_length=%d",
                image_generation_model,
                request.size,
                len(request.prompt),
            )

            if self._is_gemini_image_model():
                image_bytes, mime_type = await self._call_gemini_image(
                    prompt=request.prompt,
                    size=request.size,
                )
                image_hash = hashlib.md5(image_bytes).hexdigest()
                extension = self._extension_for_mime_type(mime_type)
            else:
                # OpenAI-compatible image generation (DALL-E or equivalent)
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
                extension = "png"

            # Save image file inside the project images folder
            filename = f"{image_hash}.{extension}"
            image_path = os.path.join(
                self.images_folder, GENERATED_IMAGES_SUB_FOLDER, filename
            )
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # Metadata keeps the project-relative path and the served URL
            relative_path = self.settings.get_image_relative_path(image_path)
            served_url = self.settings.get_image_url(
                f"{GENERATED_IMAGES_SUB_FOLDER}/{filename}"
            )

            # Create metadata
            metadata = ImageMetadata(
                id=image_hash,
                filename=filename,
                path=relative_path,
                url=served_url,
                model=image_generation_model,
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
                relative_path,
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
        Call the configured image generation API via an OpenAI compatible client.

        Returns:
            URL of the generated image.
        """
        image_generation_model = self.settings.get_image_generation_model()
        if not image_generation_model:
            raise ValueError("No image generation model configured")

        openai_client = self.ai.get_openai_chat_client(
            llm_model=image_generation_model
        )

        # The configured value is the AIModel name; the provider expects the
        # real model id, which the settings resolve for us (ai_model or name).
        model_name = self.settings.get_image_generation_settings().model

        params = {
            "model": model_name,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": 1,
        }

        # Add style only for DALL-E 3
        if model_name == "dall-e-3" and style:
            params["style"] = style

        response = openai_client.images.generate(**params)

        image = response.data[0]
        if getattr(image, "url", None):
            return image.url

        raise RuntimeError(
            "Image provider returned no url (b64_json responses are not supported yet)"
        )

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
        Analyze an image using the configured vision model.

        The model is resolved by the settings (project override, or the global
        default when the project leaves it empty) and is independent from the
        image generation model.

        Args:
            request: ImageAnalysisRequest with image_url and query.
            chat_id: Optional chat identifier for analytics.

        Returns:
            ImageAnalysisResponse with analysis results.

        Raises:
            ValueError: If vision is disabled or validation fails.
            RuntimeError: If analysis API fails.
        """
        image_vision_model = self.settings.get_image_vision_model()

        if not image_vision_model:
            raise ValueError(
                "Image vision is disabled: no image vision model configured. "
                "Set `image_vision_model` in the project settings or in the "
                "global settings."
            )

        # Validate request
        self._validate_analysis_request(request)

        try:
            logger.info(
                "Analyzing image: model=%s, detail=%s, query_length=%d",
                image_vision_model,
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
                image_vision_model,
                len(analysis),
            )

            return ImageAnalysisResponse(
                status="success",
                query=request.query,
                analysis=analysis,
                image_url=request.image_url,
                model=image_vision_model,
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
        Call the configured vision API via an OpenAI compatible client.

        Returns:
            Analysis text from the model.
        """
        image_vision_model = self.settings.get_image_vision_model()
        if not image_vision_model:
            raise ValueError("No image vision model configured")

        openai_client = self.ai.get_openai_chat_client(
            llm_model=image_vision_model
        )

        # The configured value is the AIModel name; the provider expects the
        # real model id, which the settings resolve for us (ai_model or name).
        model_name = self.settings.get_image_vision_settings().model

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
            model=model_name,
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

    def _resolve_metadata_path(self, metadata: ImageMetadata) -> str:
        """
        Return the absolute file path of an image from its metadata.

        Metadata stores project-relative paths. Older metadata stored paths
        relative to the images folder, so both forms are resolved.

        Args:
            metadata: Image metadata entry.

        Returns:
            Absolute path of the image file.
        """
        path = metadata.path or ""
        if path.startswith("/"):
            return path

        project_path = os.path.join(self.settings.abs_project_path or "", path)
        if os.path.exists(project_path):
            return project_path

        return os.path.join(self.images_folder, path)

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
            image_path = self._resolve_metadata_path(metadata)
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