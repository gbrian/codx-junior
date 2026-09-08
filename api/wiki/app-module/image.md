# Image API Module

## Overview

This module provides FastAPI endpoints for image processing operations, including generation, analysis, text extraction, and management. It handles requests through a RESTful API interface with comprehensive error handling and logging.

## Endpoints

### POST `/images/generate`

Generates an image from a text prompt using DALL-E-3.

**Request Body:**
- `prompt` (string): Text description of the desired image
- `size` (string): Image dimensions (e.g., "1024x1024")
- `quality` (string): Quality level ("standard" or similar)
- `n` (integer): Number of images to generate
- `style` (string): Style preference (e.g., "vivid")

**Response:**
- `status`: Operation status
- `image_id`: Unique hash identifier
- `filename`: Generated filename
- `path`: Local file path
- `url`: API accessible URL
- `model`: Model used ("dall-e-3")
- `created_at`: Timestamp
- `metadata`: Additional image information

**Error Codes:**
- `VALIDATION_ERROR` (400): Invalid request parameters
- `GENERATION_FAILED` (500): Image generation error
- `INTERNAL_ERROR` (500): Unexpected server error

---

### POST `/images/analyze`

Analyzes image content using Vision API (GPT-4O).

**Request Body:**
- `image_url` (string): Image URL or base64-encoded image string
- `query` (string): Question or analysis request
- `detail` (string): Detail level ("auto" or similar)

**Response:**
- `status`: Operation status
- `query`: Original query string
- `analysis`: Analysis results
- `image_url`: Image source URL
- `model`: Model used ("gpt-4o")
- `timestamp`: Processing timestamp

**Error Codes:**
- `VALIDATION_ERROR` (400): Invalid parameters
- `ANALYSIS_FAILED` (500): Analysis processing error
- `INTERNAL_ERROR` (500): Unexpected server error

---

### GET `/images/list`

Retrieves a list of all generated images with metadata.

**Response:**
- `status`: Operation status
- `images`: Array of image objects containing:
  - `id`: Image hash
  - `filename`: File name
  - `path`: File path
  - `url`: Accessible URL
  - `model`: Generation model
  - `prompt`: Original prompt
  - `size`: Image dimensions
  - `quality`: Quality setting
  - `created_at`: Creation timestamp
  - `created_by`: User email
  - `project_id`: Associated project
  - `status`: Image status
- `count`: Total number of images

**Error Codes:**
- `LIST_FAILED` (500): Failed to retrieve images

---

### DELETE `/images/{image_id}`

Deletes a specific generated image.

**URL Parameters:**
- `image_id` (string): MD5 hash of the image

**Response:**
- `status`: Operation status
- `image_id`: Deleted image identifier

**Error Codes:**
- `MISSING_IMAGE_ID` (400): Image ID not provided
- `NOT_FOUND` (404): Image does not exist
- `DELETE_FAILED` (500): Deletion error

---

### POST `/image-to-text`

Extracts text from uploaded images using OCR (Tesseract).

**Request:**
Multipart form data with `file` parameter containing image bytes.

**Response:**
- `status`: Operation status
- `text`: Extracted text content
- `filename`: Original filename
- `char_count`: Number of characters extracted

**Error Codes:**
- `NO_FILE` (400): No file provided
- `EMPTY_FILE` (400): File contains no data
- `FILE_TOO_LARGE` (413): File exceeds size limit
- `OCR_FAILED` (500): Text extraction error
- `INTERNAL_ERROR` (500): Unexpected server error

---

## Architecture

### Dependencies

- **FastAPI**: Web framework for routing and request handling
- **ImageEngine**: Core processing engine for all image operations
- **ImageGenerationRequest/ImageAnalysisRequest**: Request validation models
- **Session Management**: Uses `request.state.codx_junior_session` for user context and settings

### Error Handling

All endpoints implement consistent error handling with:
- Specific HTTP status codes (400, 404, 413, 500)
- Structured error responses with status, error message, and error code
- Comprehensive logging at appropriate levels (warning, error, exception)

### Validation

Request validation occurs at multiple layers:
- Model validation through Pydantic request models
- File size validation for uploads
- Image ID validation for deletions

---

## Session Management

All endpoints require an authenticated session available through `request.state.codx_junior_session`, which provides:
- User information
- Application settings
- Configuration parameters (e.g., `image_max_file_size_mb`)