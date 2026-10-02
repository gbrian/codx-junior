# Image Tools Documentation

## Overview

The `image_tools` module provides utilities for image operations within chat interactions. It enables detailed image analysis and image generation capabilities through integration with Vision APIs and DALL-E.

## Features

- **Image Analysis**: Comprehensive image examination using Vision API
- **Image Generation**: Create new images from text prompts using DALL-E

## Functions

### explain_image()

Provides a detailed analysis of an image using Vision API.

**Purpose**: Analyzes base64-encoded images and returns comprehensive descriptions of visual content, elements, and context.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image_base64` | str | Yes | Base64-encoded image content (PNG, JPG, etc.) |
| `settings` | CODXJuniorSettings | Yes | Project settings (passed via kwargs) |
| `user` | CodxUser | No | User context (passed via kwargs) |

**Returns**:
- `str`: Detailed image analysis and description

**Raises**:
- `ValueError`: If image is invalid or vision is disabled
- `Exception`: If project settings are not provided

**Supported Formats**: PNG, JPG, and other standard image formats

**Processing Details**:
- Automatically removes data URI prefixes if present
- Validates base64 encoding
- Provides analysis of: main subjects, composition, colors, text/symbols, context, and notable details

**Example**:
```python
result = explain_image("iVBORw0KGgoAAAANSUhEUgA...", settings=settings)
# Returns: "This image shows a futuristic cityscape at sunset..."
```

---

### generate_image()

Generates an image from a text prompt using DALL-E.

**Purpose**: Creates new images based on text descriptions and stores them in the project.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | str | Yes | — | Text description of the image to generate |
| `settings` | CODXJuniorSettings | Yes | — | Project settings (passed via kwargs) |
| `user` | CodxUser | No | — | User context (passed via kwargs) |
| `size` | str | No | "1024x1024" | Image dimensions |
| `quality` | str | No | "standard" | Quality level: "standard" or "hd" |

**Returns**:
- `str`: Relative URL path to the generated image (e.g., "/images/project-123/abc123.png")

**Raises**:
- `ValueError`: If prompt is invalid or generation is disabled
- `Exception`: If project settings are not provided

**Processing Details**:
- Validates prompt is non-empty and not whitespace-only
- Generates vivid style images by default
- Stores images in project-specific directory structure
- Returns relative URL for easy access

**Example**:
```python
url = generate_image("A futuristic city at sunset", settings=settings)
# Returns: "/images/project-123/a1b2c3d4.png"
```

## Error Handling

Both functions implement comprehensive error handling:

| Error Type | Condition | Handler |
|-----------|-----------|---------|
| `ValueError` | Invalid input parameters | Logged as warning, raised with context |
| `RuntimeError` | API runtime issues | Logged as error, raised with context |
| `Exception` | Unexpected failures | Logged with full exception trace |

## Integration

Both functions require:
- `CODXJuniorSettings`: Project configuration object
- `ImageEngine`: Internal processing engine for API interactions
- `ImageAnalysisRequest` / `ImageGenerationRequest`: Request model objects

Optional context:
- `CodxUser`: User information for audit and personalization

## Dependencies

- `logging`: For operation tracking and debugging
- `base64`: For image encoding validation
- `typing`: For type hints and optional parameters