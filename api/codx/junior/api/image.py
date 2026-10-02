from fastapi import APIRouter, Request, UploadFile, File
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/images/generate")
async def api_generate_image(request: Request):
    """
    Generate an image from a text prompt.
    
    Request body (JSON):
    {
        "prompt": "A futuristic city at sunset",
        "size": "1024x1024",
        "quality": "standard",
        "n": 1,
        "style": "vivid"
    }
    
    Response:
    {
        "status": "success",
        "image_id": "hash123",
        "filename": "hash123.png",
        "path": "images/generated/hash123.png",
        "url": "/api/static/images/generated/hash123.png",
        "model": "dall-e-3",
        "created_at": "2024-01-15T10:30:45Z",
        "metadata": {...}
    }
    """
    from codx.junior.model.model import ImageGenerationRequest
    from codx.junior.engine.image_engine import ImageEngine
    
    codx_junior_session = request.state.codx_junior_session
    
    try:
        body = await request.json()
        gen_request = ImageGenerationRequest(**body)
        
        image_engine = ImageEngine(
            settings=codx_junior_session.settings,
            user=codx_junior_session.user,
        )
        
        response = await image_engine.generate_image(gen_request)
        return response.model_dump(mode="json")
        
    except ValueError as ex:
        logger.warning("Image generation validation error: %s", ex)
        return {
            "status": "error",
            "error": str(ex),
            "error_code": "VALIDATION_ERROR"
        }, 400
        
    except RuntimeError as ex:
        logger.error("Image generation runtime error: %s", ex)
        return {
            "status": "error",
            "error": str(ex),
            "error_code": "GENERATION_FAILED"
        }, 500
        
    except Exception as ex:
        logger.exception("Unexpected error in image generation: %s", ex)
        return {
            "status": "error",
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }, 500


@router.post("/images/analyze")
async def api_analyze_image(request: Request):
    """
    Analyze an image using Vision API.
    
    Request body (JSON):
    {
        "image_url": "https://... or base64 string",
        "query": "What is in this image?",
        "detail": "auto"
    }
    
    Response:
    {
        "status": "success",
        "query": "What is in this image?",
        "analysis": "This image shows...",
        "image_url": "https://...",
        "model": "gpt-4o",
        "timestamp": "2024-01-15T10:30:45Z"
    }
    """
    from codx.junior.model.model import ImageAnalysisRequest
    from codx.junior.engine.image_engine import ImageEngine
    
    codx_junior_session = request.state.codx_junior_session
    
    try:
        body = await request.json()
        analysis_request = ImageAnalysisRequest(**body)
        
        image_engine = ImageEngine(
            settings=codx_junior_session.settings,
            user=codx_junior_session.user,
        )
        
        response = await image_engine.analyze_image(analysis_request)
        return response.model_dump(mode="json")
        
    except ValueError as ex:
        logger.warning("Image analysis validation error: %s", ex)
        return {
            "status": "error",
            "error": str(ex),
            "error_code": "VALIDATION_ERROR"
        }, 400
        
    except RuntimeError as ex:
        logger.error("Image analysis runtime error: %s", ex)
        return {
            "status": "error",
            "error": str(ex),
            "error_code": "ANALYSIS_FAILED"
        }, 500
        
    except Exception as ex:
        logger.exception("Unexpected error in image analysis: %s", ex)
        return {
            "status": "error",
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }, 500


@router.get("/images/list")
async def api_list_images(request: Request):
    """
    List all generated images with metadata.
    
    Response:
    {
        "status": "success",
        "images": [
            {
                "id": "hash123",
                "filename": "hash123.png",
                "path": "images/generated/hash123.png",
                "url": "/api/static/images/generated/hash123.png",
                "model": "dall-e-3",
                "prompt": "A futuristic city at sunset",
                "size": "1024x1024",
                "quality": "standard",
                "created_at": "2024-01-15T10:30:45Z",
                "created_by": "user@example.com",
                "project_id": "project-123",
                "status": "success"
            }
        ],
        "count": 1
    }
    """
    from codx.junior.engine.image_engine import ImageEngine
    
    codx_junior_session = request.state.codx_junior_session
    
    try:
        image_engine = ImageEngine(
            settings=codx_junior_session.settings,
            user=codx_junior_session.user,
        )
        
        images = image_engine.list_generated_images()
        return {
            "status": "success",
            "images": [img.model_dump(mode="json") for img in images],
            "count": len(images),
        }
        
    except Exception as ex:
        logger.exception("Error listing images: %s", ex)
        return {
            "status": "error",
            "error": "Failed to list images",
            "error_code": "LIST_FAILED"
        }, 500


@router.delete("/images/{image_id}")
async def api_delete_image(image_id: str, request: Request):
    """
    Delete a generated image by ID.
    
    URL parameters:
    - image_id: MD5 hash of the image
    
    Response:
    {
        "status": "success",
        "image_id": "hash123"
    }
    """
    from codx.junior.engine.image_engine import ImageEngine
    
    codx_junior_session = request.state.codx_junior_session
    
    try:
        if not image_id or len(image_id.strip()) == 0:
            return {
                "status": "error",
                "error": "Image ID is required",
                "error_code": "MISSING_IMAGE_ID"
            }, 400
        
        image_engine = ImageEngine(
            settings=codx_junior_session.settings,
            user=codx_junior_session.user,
        )
        
        success = image_engine.delete_image(image_id)
        
        if success:
            logger.info("Image deleted: %s", image_id)
            return {
                "status": "success",
                "image_id": image_id
            }
        else:
            logger.warning("Image not found: %s", image_id)
            return {
                "status": "error",
                "error": "Image not found",
                "error_code": "NOT_FOUND"
            }, 404
            
    except Exception as ex:
        logger.exception("Error deleting image %s: %s", image_id, ex)
        return {
            "status": "error",
            "error": "Failed to delete image",
            "error_code": "DELETE_FAILED"
        }, 500


@router.post("/image-to-text")
async def api_image_to_text(file: UploadFile = File(...), request: Request = None):
    """
    Extract text from an image using OCR (Tesseract).
    
    This endpoint uses optical character recognition to extract text
    from uploaded images. It provides a detailed text description of
    what's visible in the image.
    
    Request:
    - Multipart form with 'file' parameter containing image bytes
    
    Response:
    {
        "status": "success",
        "text": "Extracted text from image...",
        "filename": "image.jpg"
    }
    """
    from codx.junior.engine.image_engine import ImageEngine
    
    codx_junior_session = request.state.codx_junior_session
    
    try:
        # Validate file
        if not file or not file.filename:
            return {
                "status": "error",
                "error": "No file provided",
                "error_code": "NO_FILE"
            }, 400
        
        # Read file bytes
        file_bytes = await file.read()
        
        if not file_bytes:
            return {
                "status": "error",
                "error": "File is empty",
                "error_code": "EMPTY_FILE"
            }, 400
        
        # Check file size
        max_size_mb = codx_junior_session.settings.image_max_file_size_mb
        if len(file_bytes) > max_size_mb * 1024 * 1024:
            return {
                "status": "error",
                "error": f"File exceeds maximum size of {max_size_mb}MB",
                "error_code": "FILE_TOO_LARGE"
            }, 413
        
        # Create image engine and extract text
        image_engine = ImageEngine(
            settings=codx_junior_session.settings,
            user=codx_junior_session.user,
        )
        
        text = image_engine.extract_text_ocr(file_bytes)
        
        logger.info(
            "OCR text extraction completed: file=%s, chars=%d",
            file.filename,
            len(text)
        )
        
        return {
            "status": "success",
            "text": text,
            "filename": file.filename,
            "char_count": len(text)
        }
        
    except RuntimeError as ex:
        logger.error("OCR error: %s", ex)
        return {
            "status": "error",
            "error": str(ex),
            "error_code": "OCR_FAILED"
        }, 500
        
    except Exception as ex:
        logger.exception("Unexpected error in image-to-text: %s", ex)
        return {
            "status": "error",
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }, 500

# Made with ❤️ by codx-junior