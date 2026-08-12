# Files API Module

## Overview

This module provides FastAPI endpoints for file management operations within the CODX Junior project. It handles file listing, reading, searching, and uploading through RESTful API endpoints.

## Endpoints

### List Files

**Endpoint:** `GET /files`

Lists all files in a specified directory.

**Query Parameters:**
- `path` (optional): Directory path, relative or absolute. Defaults to current directory (`.`)

**Response:**
- Returns directory contents on success
- HTTP 404: If the specified path is not a directory

### Read File

**Endpoint:** `GET /files/read`

Reads and returns the content of a specific file along with its metadata.

**Query Parameters:**
- `path` (required): File path to read, relative or absolute

**Response:**
- Returns file content with metadata on success
- HTTP 400: If path parameter is missing
- HTTP 404: If file is not found

### Search Files by Path

**Endpoint:** `GET /files/search`

Performs a filesystem search for files whose paths contain the specified pattern.

**Query Parameters:**
- `search` (required): Pattern to search for in file paths (case-insensitive)
- `search_path` (optional): Subdirectory to limit search scope, relative to project root
- `page` (optional): Page number, 0-indexed. Default: `0`
- `page_size` (optional): Number of results per page. Default: `50`
- `raw_search` (optional): If `true`, searches all files. If `false`, excludes `.git` directory. Default: `false`

**Response:**
Returns paginated results with:
- `page`: Current page number
- `total_files`: Total number of matching files
- `page_size`: Results per page
- `files`: List of matching file paths

Returns empty results if search pattern is empty.

### Search Files by Content

**Endpoint:** `GET /files/search-content`

Performs a filesystem content search for files containing the specified query pattern.

**Query Parameters:**
- `q` (required): Pattern to search for in file contents
- `search_path` (optional): Subdirectory to limit search scope, relative to project root
- `page` (optional): Page number, 0-indexed. Default: `0`
- `page_size` (optional): Number of results per page. Default: `50`
- `case_sensitive` (optional): Whether search should be case-sensitive. Default: `false`
- `raw_search` (optional): If `true`, searches all files. If `false`, excludes `.git` directory. Default: `false`

**Response:**
Returns paginated results with:
- `page`: Current page number
- `total_files`: Total number of files containing matches
- `total_matches`: Total number of matches found
- `page_size`: Results per page
- `results`: List of search results

Returns empty results if query is empty.

### Upload Single File

**Endpoint:** `POST /files/upload`

Uploads a single file to the project.

**Form Data:**
- `file` (required): File to upload
- `path` (required): Target file path within the project, relative to project root
- `process` (optional): Whether to apply file profiles before saving. Default: `false`

**Response:**
Returns upload metadata including:
- File path
- File size
- Modification time

**Error Responses:**
- HTTP 400: Missing or invalid required parameters
- HTTP 413: File size exceeds limits
- HTTP 500: Internal server error during upload

### Upload Multiple Files

**Endpoint:** `POST /files/upload-multiple`

Uploads multiple files to the project in batch.

**Form Data:**
- `files` (required): List of files to upload
- `process` (optional): Whether to apply file profiles before saving. Default: `false`

**File Path Convention:**
Files should have path information in their filename using `:` as separator. Example: `src/app.py`

**Response:**
Returns batch upload results with:
- `successful`: List of successfully uploaded files
- `failed`: List of failed uploads with error details
- `total_files`: Total number of files attempted
- `total_size_uploaded`: Total size of successfully uploaded files

**Error Responses:**
- HTTP 400: No files provided
- HTTP 413: Total upload size exceeds limits
- HTTP 500: Internal server error during batch upload

## Dependencies

- **FastAPI**: Web framework for building the API
- **CODXJuniorSession**: Session object accessed via `request.state` containing:
  - `get_file_engine()`: Returns the file engine for file operations
- **UploadFile**: FastAPI utility for handling file uploads
- **Request/Response**: FastAPI request and response handling

## Logging

The module uses Python's logging module with level-based logging:
- `INFO`: File operation successes and batch operation summaries
- `WARNING`: Validation errors and missing parameters
- `ERROR`: File operation failures