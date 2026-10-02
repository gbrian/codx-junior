# Image Model Documentation

## Overview

The image model module defines Pydantic models for all image-related operations, including image generation requests and responses, image vision/analysis requests and responses, and image metadata storage and tracking.

## Models

### ImageGenerationRequest

Request model for image generation operations.

**Fields:**
- `prompt` (string, required): Text prompt for image generation
- `size` (string, default: "1024x1024"): Image size options include 256x256, 512x512, 1024x1024, 1024x1792, or 1792x1024
- `quality` (string, default: "standard"): Quality level - either standard or hd
- `n` (integer, default: 1): Number of images to generate, between 1 and 10
- `style` (string, optional, default: "vivid"): Style preference - vivid or natural (DALL-E 3 only)

### ImageAnalysisRequest

Request model for image analysis and vision operations.

**Fields:**
- `image_url` (string, required): URL or base64 encoded image data
- `query` (string, required): Question or analysis request about the image
- `detail` (string, default: "auto"): Image detail level - auto, low, or high

### ImageMetadata

Metadata storage model for generated images.

**Fields:**
- `id` (string): Unique image identifier (MD5 hash)
- `filename` (string): Saved filename
- `path` (string): Relative path from project root
- `url` (string): Accessible URL for the image
- `model` (string): Model used for generation
- `prompt` (string): Original generation prompt
- `size` (string): Image dimensions
- `quality` (string): Quality setting used
- `created_at` (datetime): Generation timestamp
- `created_by` (string): User who generated the image
- `project_id` (string): Associated project identifier
- `status` (string): Current status - success, failed, or processing
- `error_message` (string, optional): Error details if status is failed

### ImageGenerationResponse

Response model returned after image generation.

**Fields:**
- `status` (string): Operation status - success or error
- `image_id` (string): Unique image identifier
- `filename` (string): Saved filename
- `path` (string): Relative path to the image
- `url` (string): Accessible URL
- `model` (string): Model used for generation
- `created_at` (datetime): Generation timestamp
- `metadata` (ImageMetadata): Full metadata object containing complete image information

### ImageAnalysisResponse

Response model returned after image analysis.

**Fields:**
- `status` (string): Operation status - success or error
- `query` (string): Original analysis query
- `analysis` (string): Analysis result or findings
- `image_url` (string): URL of the analyzed image
- `model` (string): Model used for analysis
- `timestamp` (datetime): Analysis operation timestamp

## Usage

These models are used to structure and validate:
- Image generation requests with specific parameters
- Image analysis queries for vision operations
- Response data and metadata tracking
- Error handling and status reporting