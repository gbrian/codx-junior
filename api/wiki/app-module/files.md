# Files API Module

## Overview

This module provides FastAPI endpoints for file management operations within the CODX Junior API. It enables listing, reading, searching, and uploading files with support for media preview and content search capabilities.

## Endpoints

### GET `/files`

Lists files in a specified directory.

**Query Parameters:**
- `path` (string): Directory path, relative or absolute (default: `"."`)

**Response:**
- Success: Directory contents from `file_engine.read_directory()`
- 404: If path is not a directory

**Example:**
```
GET /files?path=src
```

---

### GET `/files/read`

Reads a file and returns its content with metadata.

**Query Parameters:**
- `path` (string, required): File path to read

**Response:**
- Success: File content and metadata from `file_engine.read_file()`
- 400: If path parameter is missing
- 404: If file is not found

**Example:**
```
GET /files/read?path=src/main.py
```

---

### GET `/files/preview`

Streams a file's binary content for preview or playback of media files (video, audio, images).

**Query Parameters:**
- `path` (string, required): File path to preview

**Response:**
- Success: FileResponse with appropriate Content-Type header
- 400: If path parameter is missing
- 403: If file path is invalid
- 404: If file does not exist

**Notes:**
- Returns binary streaming instead of base64 encoding
- Automatically determines media type based on file extension

**Example:**
```
GET /files/preview?path=assets/video.mp4
```

---

### GET `/files/search`

Searches for files whose paths contain the search pattern.

**Query Parameters:**
- `search` (string, required): Pattern to search for (case-insensitive)
- `search_path` (string): Optional subdirectory to limit search scope
- `page` (integer): Page number, 0-indexed (default: `0`)
- `page_size` (integer): Results per page (default: `50`)
- `raw_search` (boolean): Include `.git` and other excluded directories (default: `false`)
- `use_regex` (boolean): Treat search pattern as regex (default: `false`)

**Response:**
```json
{
  "page": 0,
  "total_files": 0,
  "page_size": 50,
  "files": []
}
```

**Notes:**
- Returns empty results if search parameter is empty
- Supports both substring and regex pattern matching

**Example:**
```
GET /files/search?search=config&page=0&page_size=25
```

---

### GET `/files/search-content`

Searches for files whose content contains the search query.

**Query Parameters:**
- `q` (string, required): Pattern to search for in file contents
- `search_path` (string): Optional subdirectory to limit search scope
- `page` (integer): Page number, 0-indexed (default: `0`)
- `page_size` (integer): Results per page (default: `50`)
- `case_sensitive` (boolean): Enable case-sensitive search (default: `false`)
- `raw_search` (boolean): Include `.git` and other excluded directories (default: `false`)
- `use_regex` (boolean): Treat query as regex pattern (default: `false`)

**Response:**
```json
{
  "page": 0,
  "total_files": 0,
  "total_matches": 0,
  "page_size": 50,
  "results": [],
  "error": "Missing (q)uery parameter"
}
```

**Notes:**
- Returns error message if query parameter is empty
- Includes match count in results

**Example:**
```
GET /files/search-content?q=TODO&case_sensitive=false
```

---

### POST `/files/upload`

Uploads a single file to the project.

**Form Data:**
- `file` (UploadFile, required): File to upload
- `path` (string, required): Target file path within project (relative to project root)
- `process` (boolean): Apply file profiles before saving (default: `false`)

**Response:**
```json
{
  "file_path": "path/to/file",
  "size": 1024,
  "modified_time": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- 200: File uploaded successfully
- 400: Missing required parameters
- 413: File size exceeds limits
- 500: Server error during upload

**Notes:**
- Leading slashes in path are automatically removed
- File is appended to the provided path
- Logging includes file size and process flag

**Example:**
```
POST /files/upload
Content-Type: multipart/form-data

file: [binary data]
path: src/
process: false
```

---

### POST `/files/upload-multiple`

Uploads multiple files to the project in batch.

**Form Data:**
- `files` (list[UploadFile], required): List of files to upload
- `process` (boolean): Apply file profiles before saving (default: `false`)

**Response:**
```json
{
  "successful": ["file1.py", "file2.py"],
  "failed": [{"file": "file3.py", "error": "error message"}],
  "total_files": 3,
  "total_size_uploaded": 5120
}
```

**Status Codes:**
- 200: Batch upload completed (with per-file results)
- 400: No files provided
- 413: Total upload size exceeds limits
- 500: Server error during batch upload

**Notes:**
- Each file's uploaded filename is used as target path
- Returns separate success/failure lists per file
- Logging includes count and process flag

**Example:**
```
POST /files/upload-multiple
Content-Type: multipart/form-data

files: [binary data 1, binary data 2]
process: false
```

---

## Authentication & Session

All endpoints require:
- Active `codx_junior_session` attached to request state
- Access to file engine via `request.state.codx_junior_session.get_file_engine()`

## Error Handling

Common error codes:
- **400**: Invalid or missing required parameters
- **403**: Invalid file path (security violation)
- **404**: File or directory not found
- **413**: File size exceeds upload limits
- **500**: Internal server error during file operations

All errors are logged with appropriate severity levels (warning/error).