# File Engine Documentation

## Overview

The File Engine is a core module responsible for handling all file system operations within the codx-junior project. It manages file reading, writing, diffing, and profile application while maintaining security through path validation and git-ignore rule enforcement.

## Key Components

### GitIgnoreManager

A specialized class that efficiently manages `.gitignore` rules across a directory tree without spawning subprocesses for each file check.

#### Features

- **Pre-loading**: Loads all `.gitignore` files once during initialization rather than checking them repeatedly
- **Nested Support**: Correctly handles `.gitignore` files at multiple directory levels
- **Cascade Behavior**: Files inside ignored directories are automatically marked as ignored, matching git's actual behavior
- **Performance**: Uses the `pathspec` library for in-memory pattern matching

#### How It Works

The GitIgnoreManager walks the directory tree to compile all `.gitignore` rules into `PathSpec` objects, storing them mapped by their containing directory. When checking if a path is ignored, it:

1. Checks if the parent directory is ignored (cascade check)
2. Walks up from the file's directory to root, checking each `.gitignore`
3. Caches results to avoid redundant work for child lookups

### FileEngine

The main class handling file system operations with integrated git-ignore awareness.

#### Core Methods

**`read_file(path: str)`**
- Reads a project file and returns its content along with metadata
- Accepts relative or absolute paths
- Returns: Dictionary with `content`, `last_modification`, and `size`

**`write_project_file(file_path: str, content: str, process: bool = True)`**
- Writes content to a project file with optional file profile processing
- Creates parent directories automatically
- Validates path security before writing
- Returns: Metadata including file location and modification time

**`upload_file(file_path: str, file_content: bytes, process: bool = False, max_file_size: int)`**
- Uploads a single file with size validation
- Handles both text and binary files
- Supports file profile application during upload
- Returns: Upload metadata with file information

**`upload_files(file_uploads: List[Tuple[str, bytes]], ...)`**
- Batch uploads multiple files
- Validates total size across all files
- Continues processing even if individual uploads fail
- Returns: Dictionary with successful/failed uploads breakdown

**`diff_file(path: str, content: str)`**
- Creates a diff between a project file and provided content
- Uses git diff --no-index for comparison
- Returns: Dictionary with `diff`, `stats`, and file metadata

**`search_files(search: str, search_path: str = None, ...)`**
- Searches for files whose paths contain the search pattern
- Respects `.gitignore` rules by default
- Supports pagination and raw search mode
- Returns: Paginated file listing with ignore status

**`search_files_content(query: str, search_path: str = None, ...)`**
- Searches within file contents using pattern matching
- Supports case-sensitive and case-insensitive modes
- Excludes git-ignored files unless raw_search is enabled
- Returns: Results sorted by match count with line-level details

**`read_directory(path: str)`**
- Lists directory contents with git-ignore awareness
- Marks all children as ignored if parent directory is ignored
- Returns: Directory structure with ignore flags

## File Validation and Security

### Path Resolution

The `get_valid_project_file_path()` method ensures all file operations stay within allowed project boundaries:

- **Absolute Paths**: Validated against the current project and all user projects
- **Relative Paths**: Resolved within the current project root
- **Traversal Prevention**: Blocks `..` sequences that escape project boundaries
- **Cross-Drive Safety**: Handles Windows drive letter differences

The method has two internal helpers:

- `_resolve_absolute_path()`: Checks absolute paths against all allowed projects
- `_resolve_relative_path()`: Resolves relative paths within project root with traversal detection

## File Profiles

File profiles allow automatic code improvements through AI-powered transformations.

**`process_project_file_before_saving(file_path: str, content: str)`**
- Identifies all matching file profiles for a given file path
- Applies profiles sequentially to the content
- Returns: Content after all profile transformations

**`apply_file_profile(file_path: str, content: str, profile: Profile)`**
- Applies a single profile using AI assistance
- Sends content and profile instructions to the chat system
- Returns: Improved file content without decorations or fences

## File Information and Metadata

**`get_file_info(file_path: str)`**
- Returns metadata for a file: modification time and size
- Modification time is returned in ISO 8601 format
- Returns: Dictionary with `last_modification` and `size` (or None if file not found)

**`parse_file_line(file: str, base_path: str, ...)`**
- Converts a file name into a structured dictionary for directory listings
- Includes name, path, directory flag, ignore status, and metadata
- Supports ignore cascade from parent directories
- Returns: Structured file entry dictionary

## Project Documentation

**`get_wiki_file(file_path: str)`**
- Reads wiki files from the project wiki directory
- Returns: File content with metadata, or not-found message

**`get_readme()`**
- Reads the project's README.md file
- Returns: README content with metadata, or empty content if not found

## Utility Methods

**`api_image_to_text(image_bytes: bytes)`**
- Converts image bytes to text using OCR with pytesseract
- Requires PIL and pytesseract dependencies
- Returns: Extracted text string

## Upload Constraints

The module enforces size limits for uploaded files:

- **Default Max File Size**: 1 GB per file
- **Default Max Total Size**: 4 GB across all files in batch upload

These limits can be customized per operation.

## Performance Considerations

- GitIgnoreManager loads all `.gitignore` files once per search operation, avoiding repeated filesystem reads
- Ignore status is cached for directories to speed up child lookups
- Directory pruning in `os.walk` prevents traversing ignored subtrees
- Pagination support prevents loading large result sets entirely into memory

## Dependencies
**Imports from:** codx/junior/db.py, codx/junior/model/model.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py