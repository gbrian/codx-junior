# Files API Module Documentation

## Overview

This module provides FastAPI endpoints for file management operations within the CODX Junior API. It handles file listing, reading, searching, and uploading capabilities with support for both single and batch operations.

## Endpoints

### List Files

**Endpoint:** `GET /files`

Lists files in a specified directory.

**Query Parameters:**
- `path` (optional): Directory path, either relative or absolute. Defaults to current directory (`"."`)

**Returns:**
- Directory contents via `file_engine.read_directory()`
- HTTP 404 if the specified path is not a directory

### Read File

**Endpoint:** `GET /files/read`

Reads and returns a file's content along with its metadata.

**Query Parameters:**
- `path` (required): File path, either relative or absolute

**Returns:**
- File content and metadata via `file_engine.read_file()`
- HTTP 400 if path parameter is missing
- HTTP 404 if file is not found

### Search Files by Path

**Endpoint:** `GET /files/search`

Searches for files whose paths contain a specified pattern. Performs filesystem search within the project scope with pagination support.

**Query Parameters:**
- `search` (required): Pattern to search for in file paths (case-insensitive)
- `search_path` (optional): Subdirectory to limit search scope (relative to project root)
- `page` (optional): Page number, 0-indexed. Defaults to `0`
- `page_size` (optional): Number of results per page. Defaults to `50`
- `raw_search` (optional): If `"true"`, search all files; if `"false"`, exclude `.git`. Defaults to `"false"`
- `use_regex` (optional): If `"true"`, treat search pattern as regex; if `"false"`, use substring match. Defaults to `"false"`

**Returns:**
- Paginated results containing:
  - `page`: Current page number
  - `total_files`: Total number of matching files
  - `page_size`: Results per page
  - `files`: List of matching files
- Empty results if search parameter is not provided

### Search Files by Content

**Endpoint:** `GET /files/search-content`

Searches for files whose content contains a specified query pattern. Supports pagination and multiple search modes.

**Query Parameters:**
- `q` (required): Pattern to search for in file contents
- `search_path` (optional): Subdirectory to limit search scope (relative to project root)
- `page` (optional): Page number, 0-indexed. Defaults to `0`
- `page_size` (optional): Number of results per page. Defaults to `50`
- `case_sensitive` (optional): Whether search should be case-sensitive. Defaults to `"false"`
- `raw_search` (optional): If `"true"`, search all files; if `"false"`, exclude `.git`. Defaults to `"false"`
- `use_regex` (optional): If `"true"`, treat query as regex pattern; if `"false"`, use substring match. Defaults to `"false"`

**Returns:**
- Paginated results containing:
  - `page`: Current page number
  - `total_files`: Total number of files with matches
  - `total_matches`: Total number of matches found
  - `page_size`: Results per page
  - `results`: List of search results
  - `error`: Error message if query parameter is missing
- Error response with HTTP 400 context if query parameter is not provided

### Upload Single File

**Endpoint:** `POST /files/upload`

Uploads a single file to the project.

**Form Data:**
- `file` (required): File to upload
- `path` (required): Target file path within project (relative to project root)
- `process` (optional): Whether to apply file profiles before saving. Defaults to `false`

**Returns:**
- Upload metadata including file path, size, and modification time
- HTTP 400 if required `path` parameter is missing
- HTTP 413 if file size exceeds limits (ValueError)
- HTTP 500 if an OSError occurs during upload

**Logging:**
- Warning logged if path parameter is missing
- Info logged with file details on successful upload
- Warning logged for validation errors
- Error logged for OSError exceptions

### Upload Multiple Files

**Endpoint:** `POST /files/upload-multiple`

Uploads multiple files to the project in batch operation.

**Form Data:**
- `files` (required): List of files to upload
- `process` (optional): Whether to apply file profiles before saving. Defaults to `false`

**File Naming Convention:**
Files can use filenames or embedded path information using `':'` as a separator to indicate target paths.

**Returns:**
- Batch upload results containing:
  - `successful`: List of successfully uploaded files
  - `failed`: List of failed uploads with error details
  - `total_files`: Total number of files attempted
  - `total_size_uploaded`: Total size of successfully uploaded files
- HTTP 400 if files list is empty
- HTTP 413 if total upload size exceeds limits (ValueError)
- HTTP 500 if an OSError occurs during batch upload

**Logging:**
- Warning logged if no files are provided
- Info logged with batch details on upload start
- Info logged with success/failure counts on completion
- Warning logged for validation errors
- Error logged for OSError exceptions

## Session Integration

All endpoints access the CODX Junior session through `request.state.codx_junior_session` to obtain the file engine instance, which handles the actual file operations.