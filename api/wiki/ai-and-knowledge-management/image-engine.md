# Image Engine Documentation

## Overview

The `ImageEngine` is a centralized module for managing all image operations within the CODX Junior system. It provides capabilities for image generation, vision-based analysis, storage management, and optical character recognition (OCR).

## Key Responsibilities

- **Image Generation**: Create images from text prompts using DALL-E (versions 2 & 3)
- **Vision Analysis**: Analyze images using GPT-4 Vision API
- **Storage Management**: Handle image file storage and lifecycle
- **Metadata Tracking**: Maintain comprehensive metadata for all generated images
- **OCR Support**: Extract text from images using Tesseract OCR

## Initialization

```python
engine = ImageEngine(settings=settings, user=optional_user)
```

**Parameters:**
- `settings`: Project settings containing image configuration
- `user`: Optional user context for analytics and tracking

The engine automatically initializes required folder structures:
- `images/generated/` - Stores generated images
- `images/message/` - Stores message-related images
- `metadata.json` - Tracks all image metadata

## Image Generation

### Generate Images

Generate images from text prompts using DALL-E.

```python
response = await engine.generate_image(
    request=ImageGenerationRequest(
        prompt="A serene mountain landscape",
        size="1024x1024",
        quality="standard",
        style="natural"  # DALL-E 3 only
    ),
    chat_id="optional_chat_id"
)
```

**Request Parameters:**
- `prompt`: Text description (max 4000 characters, required)
- `size`: Image dimensions - `256x256`, `512x512`, `1024x1024`, `1024x1792`, or `1792x1024`
- `quality`: `standard` or `hd` (DALL-E 3)
- `style`: `natural` or `vivid` (DALL-E 3 only)
- `n`: Number of images (1-10)

**Response:**
Returns `ImageGenerationResponse` containing:
- `status`: Success indicator
- `image_id`: Unique identifier (MD5 hash)
- `filename`: Generated file name
- `path`: Relative file path
- `url`: Accessible URL
- `model`: Model used for generation
- `created_at`: Timestamp
- `metadata`: Full image metadata

**Validation Rules:**
- Prompt cannot be empty and must not exceed 4000 characters
- Size must match valid dimensions
- Quality must be `standard` or `hd`
- Number of images must be between 1 and 10

**Exceptions:**
- `ValueError`: If generation is disabled or validation fails
- `RuntimeError`: If image generation API fails

## Image Vision Analysis

### Analyze Images

Analyze images using GPT-4 Vision API to extract information or answer questions about image content.

```python
response = await engine.analyze_image(
    request=ImageAnalysisRequest(
        image_url="https://example.com/image.png",
        query="What objects are visible in this image?",
        detail="auto"
    ),
    chat_id="optional_chat_id"
)
```

**Request Parameters:**
- `image_url`: HTTP URL or base64-encoded image (required)
- `query`: Analysis question or prompt (max 4000 characters, required)
- `detail`: Resolution detail level - `auto`, `low`, or `high`

**Response:**
Returns `ImageAnalysisResponse` containing:
- `status`: Success indicator
- `query`: Original query
- `analysis`: Analysis results text
- `image_url`: Analyzed image URL
- `model`: Vision model used
- `timestamp`: Analysis timestamp

**Validation Rules:**
- Image URL is required
- Query cannot be empty and must not exceed 4000 characters
- Detail level must be `auto`, `low`, or `high`

**Exceptions:**
- `ValueError`: If vision is disabled or validation fails
- `RuntimeError`: If analysis API fails

## Image Storage & Metadata

### Retrieve Image Metadata

Get metadata for a specific image by ID.

```python
metadata = engine.get_image_metadata(image_id="hash_value")
```

Returns `ImageMetadata` object or `None` if not found.

### List Generated Images

Retrieve all successfully generated images.

```python
images = engine.list_generated_images()
```

Returns a list of `ImageMetadata` objects for all generated images.

### Delete Image

Remove an image file and its associated metadata.

```python
success = engine.delete_image(image_id="hash_value")
```

Returns `True` if deletion succeeded, `False` otherwise.

## Optical Character Recognition

### Extract Text from Images

Extract text content from images using Tesseract OCR.

```python
text = engine.extract_text_ocr(image_bytes=bytes_content)
```

**Parameters:**
- `image_bytes`: Raw image file bytes

**Returns:**
Extracted text string

**Exceptions:**
- `RuntimeError`: If OCR processing fails

## Configuration Requirements

The Image Engine requires the following settings to be enabled:

- `is_image_generation_enabled()`: Enable/disable image generation
- `is_image_vision_enabled()`: Enable/disable vision analysis
- `image_generation_model`: Model identifier (e.g., `dall-e-3`)
- `image_vision_model`: Vision model identifier (e.g., `gpt-4-vision-preview`)

## Storage Paths

Generated images are stored following this structure:

```
.codx/static/images/
├── generated/          # Generated images
│   └── metadata.json   # Metadata index
└── message/            # Message-related images
```

Images are identified by MD5 hashes of their content, ensuring deduplication and consistency.

## Error Handling

All async methods provide comprehensive error handling:
- Invalid requests are validated before API calls
- API failures are caught and logged with detailed context
- Metadata operations include fallback handling for missing files
- All exceptions include meaningful error messages for debugging