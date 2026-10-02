# File Engine Module Documentation

## Overview

The File Engine is a comprehensive module that handles all file system operations for the CODX Junior project. It manages reading, writing, diffing files, and applying file profiles while maintaining security and performance through intelligent git-ignore handling.

## Core Components

### GitIgnoreManager

A specialized utility class that efficiently manages `.gitignore` rules without spawning subprocesses for each file check.

**Key Features:**
- Pre-loads all `.gitignore` files from a directory tree during initialization
- Compiles rules into `PathSpec` objects for in-memory matching
- Supports nested `.gitignore` files with proper scope handling
- Implements cascading ignore status: files inside ignored directories are automatically marked as ignored
- Caches ignored directory results to optimize repeated checks

**How It Works:**
1. Scans the entire directory tree once, collecting all `.gitignore` files
2. Stores compiled rules mapped by directory path
3. Checks files by walking up the tree from file location to root
4. Applies parent directory ignore status to all children

### FileEngine

The main class providing file system operations with security checks and git-ignore awareness.

## Key Operations

### Reading Files

**`read_file(path: str)`**
- Reads project files with automatic binary detection
- Binary files (PNG, JPG, PDF, etc.) are returned as base64-encoded strings
- Text files are returned as plain text
- Returns file metadata including modification time and size
- Handles encoding errors gracefully with UTF-8 fallback

**`read_directory(path: str)`**
- Lists directory contents with git-ignore status
- Marks children of ignored directories as ignored
- Returns structured entry data for each file/folder
- Includes file metadata (size, modification time)

### Writing Files

**`write_project_file(file_path: str, content: str, process: bool = True)`**
- Writes content to project files
- Optionally applies file profiles before saving
- Creates parent directories automatically
- Validates file paths for security
- Returns metadata including size and modification time

**`upload_file(file_path: str, file_content: bytes, process: bool = False, max_file_size: int = 1GB)`**
- Uploads single files with size validation
- Handles both text and binary file uploads
- Supports optional file profile processing
- Prevents oversized uploads with configurable limits

**`upload_files(file_uploads: List[Tuple], process: bool = False, ...)`**
- Batch uploads multiple files
- Validates total size across all files (default 4GB limit)
- Continues processing on individual file failures
- Returns success/failure breakdown with error details

### File Searching

**`search_files(search: str, search_path: str = None, page: int = 0, page_size: int = 50, raw_search: bool = False, use_regex: bool = False)`**
- Searches for files by path pattern
- Supports substring and regex matching
- Excludes git-ignored files by default (when `raw_search=False`)
- Provides pagination support
- Loads `.gitignore` rules once for performance

**`search_files_content(query: str, search_path: str = None, case_sensitive: bool = False, ...)`**
- Searches file contents matching a pattern
- Supports both directory and single-file search modes
- Returns line numbers and match counts
- Includes case-sensitive/insensitive options
- Supports regex patterns

**`_search_in_file(...)`**
- Internal helper for pattern matching within a single file
- Handles regex and substring search modes
- Extracts line numbers and match context
- Manages encoding errors gracefully

### File Comparison

**`diff_file(path: str, content: str, from_branch: str = None, to_branch: str = None)`**
- Compares file against provided content using `git diff --no-index`
- Returns diff output and statistics
- Includes file metadata

### Profile Application

**`apply_file_profile(file_path: str, content: str, profile: Profile)`**
- Applies coding style and best practice profiles to files
- Uses AI to refactor code according to profile instructions
- Operates asynchronously
- Returns improved content

**`process_project_file_before_saving(file_path: str, content: str)`**
- Automatically applies all matching file profiles
- Processes content before file is saved
- Supports multiple profiles per file

## Security Features

### Path Validation

**`get_valid_project_file_path(file_path: str)`**
- Validates all file paths for security
- Handles both absolute and relative paths
- Prevents path traversal attacks using `..` sequences
- Restricts access to user's allowed projects
- Raises `ValueError` for unauthorized access attempts

**`_resolve_absolute_path(file_path: str)`**
- Validates absolute paths against all user projects
- Checks current project first (fast path)
- Falls back to checking all accessible projects

**`_resolve_relative_path(norm_input_path: str, original_path: str)`**
- Resolves relative paths within project root
- Prevents escape using normalized path comparison
- Handles cross-drive protection on Windows

## File Metadata

**`get_file_info(file_path: str)`**
- Returns file metadata dictionary
- Includes ISO 8601 formatted modification timestamp
- Provides file size in bytes
- Handles missing files gracefully

**`get_media_type(file_path: str)`**
- Determines MIME type based on file extension
- Covers video, audio, image, and document formats
- Returns `application/octet-stream` for unknown types

## Utility Features

### Binary File Detection

**`_is_binary_file(file_path: str)`**
- Checks file extension against known binary types
- Includes archives, fonts, images, videos, and documents

### Regex Pattern Compilation

**`_compile_regex_pattern(pattern: str, case_sensitive: bool = False)`**
- Compiles regex patterns with error handling
- Enables MULTILINE mode for line-boundary matching
- Supports case-sensitive/insensitive compilation
- Raises `ValueError` for invalid patterns

### Wiki and Documentation

**`get_wiki_file(file_path: str)`**
- Reads wiki files from project wiki directory
- Returns content with metadata

**`get_readme()`**
- Reads project README.md file
- Returns content and metadata

### Image Processing

**`api_image_to_text(image_bytes: bytes)`**
- Converts image bytes to text using OCR
- Uses pytesseract for text extraction
- Supports common image formats

## Configuration

### Upload Constraints

- **DEFAULT_MAX_FILE_SIZE**: 1 GB per file
- **DEFAULT_MAX_TOTAL_SIZE**: 4 GB for batch uploads

### Binary File Extensions

Supported binary extensions: `png`, `jpg`, `jpeg`, `gif`, `webp`, `ico`, `svg`, `zip`, `tar`, `gz`, `woff`, `woff2`, `ttf`, `eot`, `pdf`

### Special Directories

- **.git**: Always skipped during directory walks and searches
- **.gitignore**: Automatically discovered and applied

## Error Handling

All operations include comprehensive error handling:
- **OSError**: File system operation failures
- **ValueError**: Path validation or invalid regex patterns
- **UnicodeDecodeError**: Automatic fallback for binary files
- Logging at debug/warning/error levels for troubleshooting
- Graceful UTF-8 decoding with error ignore mode

## Performance Optimization

- Single `.gitignore` manager instantiation per operation (not per file)
- Directory caching for ignore status to avoid redundant checks
- In-memory pattern matching instead of subprocess calls
- Fast-path checks for current project before searching all projects
- Pagination support for large result sets
- Early pruning of ignored directories during tree walks

## Dependencies
**Imports from:** codx/junior/db.py, codx/junior/model/model.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py