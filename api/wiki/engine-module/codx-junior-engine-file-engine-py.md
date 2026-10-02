# File Engine Documentation

## Overview

The File Engine is a core component of codx-junior that handles all file system operations including reading, writing, diffing, and profile application. It provides secure file access with built-in path validation, git-ignore support, and batch operations.

## Core Components

### GitIgnoreManager

The `GitIgnoreManager` class efficiently checks whether files are git-ignored by pre-loading all `.gitignore` rules found within a directory tree. Instead of spawning subprocess calls per file, it reads every `.gitignore` file once and performs checks in-memory using the `pathspec` library.

#### Key Features

- **Nested .gitignore Support**: Each `.gitignore` applies to its own directory and all subdirectories, matching git's actual behavior
- **Directory Cascade Checking**: Files inside ignored directories are correctly marked as ignored regardless of whether they match a pattern directly
- **Caching**: Results are cached to avoid redundant work when checking many children of the same directory

#### Methods

- `__init__(root_path: str)`: Initialize and pre-load all .gitignore rules under root_path
- `is_ignored(abs_path: str)`: Check whether a file or directory is matched by any .gitignore rule
- `_load_all_gitignore_files()`: Walk the directory tree once and load every .gitignore found
- `_parse_gitignore(gitignore_path: str)`: Parse a single .gitignore file into a PathSpec object
- `_is_dir_ignored(abs_dir_path: str)`: Check whether a directory itself is matched by any .gitignore rule

### FileEngine

The main `FileEngine` class orchestrates all file system operations for the project.

#### Initialization

```python
def __init__(self, session: "CODXJuniorSession") -> None
```

Initializes the engine with a reference to the parent session.

## File Operations

### Reading Files

#### read_file()

```python
def read_file(self, path: str) -> dict
```

Reads a project file and returns its content along with file metadata including last modification time and size.

**Returns**: Dictionary with:
- `content`: File content as string
- `last_modification`: ISO 8601 formatted timestamp (or None)
- `size`: File size in bytes (or None)

#### read_directory()

```python
def read_directory(self, path: str) -> dict
```

Lists the contents of a directory, flagging git-ignored entries. If the directory being listed is itself git-ignored, all children are marked as ignored (cascade behavior).

**Returns**: Dictionary with:
- `path`: Directory path
- `full_path`: Full directory path
- `is_ignored`: Whether the directory is git-ignored
- `files`: List of file entries with metadata

### Writing Files

#### write_project_file()

```python
async def write_project_file(self, file_path: str, content: str, process: bool = True) -> dict
```

Writes content to a project file, optionally processing through file profiles before writing.

**Parameters**:
- `file_path`: Target file path
- `content`: Content to write
- `process`: Whether to run file profiles before writing (default: True)

**Returns**: Dictionary with file and project metadata including last_modification and size

**Raises**: OSError if writing fails

#### upload_file()

```python
async def upload_file(
    self,
    file_path: str,
    file_content: bytes,
    process: bool = False,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> dict
```

Uploads a single file to the project with validation of file size and path security.

**Parameters**:
- `file_path`: Target file path (relative to project root)
- `file_content`: Raw file bytes to write
- `process`: Whether to apply file profiles before writing
- `max_file_size`: Maximum allowed file size in bytes (default: 1 GB)

**Returns**: Dictionary with upload metadata including file path, size, and modification time

**Raises**: ValueError if file size exceeds limit or path is invalid; OSError if file write fails

#### upload_files()

```python
async def upload_files(
    self,
    file_uploads: List[Tuple[str, bytes]],
    process: bool = False,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    max_total_size: int = DEFAULT_MAX_TOTAL_SIZE,
) -> dict
```

Uploads multiple files to the project in batch, validating total size across all files.

**Parameters**:
- `file_uploads`: List of (file_path, file_content) tuples
- `process`: Whether to apply file profiles before writing
- `max_file_size`: Maximum allowed size for individual files
- `max_total_size`: Maximum allowed total size for all files (default: 4 GB)

**Returns**: Dictionary with:
- `successful`: List of successfully uploaded files
- `failed`: List of failed uploads with error details
- `total_files`: Total number of files attempted
- `total_size_uploaded`: Total size of successfully uploaded files

## File Comparison and Profiling

### diff_file()

```python
def diff_file(
    self,
    path: str,
    content: str,
    from_branch: str = None,
    to_branch: str = None,
) -> dict
```

Diffs a project file against provided content using `git diff --no-index`.

**Returns**: Dictionary with:
- `diff`: Unified diff output
- `stats`: Diff statistics
- `last_modification`: File's last modification time
- `size`: File size

### apply_file_profile()

```python
async def apply_file_profile(self, file_path: str, content: str, profile: Profile) -> str
```

Applies a single file profile to content using AI to improve the code according to best practices defined in the profile.

**Parameters**:
- `file_path`: File path for context
- `content`: Current file content
- `profile`: Profile with instructions to apply

**Returns**: Improved file content

### process_project_file_before_saving()

```python
async def process_project_file_before_saving(self, file_path: str, content: str) -> str
```

Applies all matching file profiles to content before saving.

**Returns**: Processed file content

## Search Operations

### search_files()

```python
def search_files(
    self,
    search: str,
    search_path: str = None,
    page: int = 0,
    page_size: int = 50,
    raw_search: bool = False,
    use_regex: bool = False,
) -> dict
```

Searches for files whose paths contain the search pattern. Performs filesystem search within the project and optionally limits search to a specific subdirectory.

**Parameters**:
- `search`: Substring or regex pattern to search for in file paths
- `search_path`: Optional subdirectory path (relative to project root)
- `page`: Page number (0-indexed, default 0)
- `page_size`: Number of results per page (default 50)
- `raw_search`: If True, include git-ignored files; if False, exclude them
- `use_regex`: If True, treat search as regex pattern; if False, use substring match

**Returns**: Dictionary with:
- `page`: Current page number
- `total_files`: Total number of matching files
- `page_size`: Results per page
- `files`: List of matching file entries
- `error`: Error message if an error occurred

### search_files_content()

```python
def search_files_content(
    self,
    query: str,
    search_path: str = None,
    page: int = 0,
    page_size: int = 50,
    case_sensitive: bool = False,
    raw_search: bool = False,
    use_regex: bool = False,
) -> dict
```

Searches for file content matching a query pattern within the project scope with pagination support.

**Parameters**:
- `query`: Substring or regex pattern to search for in file contents
- `search_path`: Optional directory or file path (relative to project root)
- `page`: Page number (0-indexed, default 0)
- `page_size`: Number of results per page (default 50)
- `case_sensitive`: Whether search should be case-sensitive (default False)
- `raw_search`: If True, include git-ignored files; if False, exclude them
- `use_regex`: If True, treat query as regex pattern; if False, use substring match

**Returns**: Dictionary with:
- `page`: Current page number
- `total_files`: Total number of files with matches
- `total_matches`: Total number of matches found
- `page_size`: Results per page
- `results`: List of matching results with match details
- `error`: Error message if an error occurred

## File Information and Utilities

### get_file_info()

```python
def get_file_info(self, file_path: str) -> dict
```

Returns metadata for a file including last modification time (ISO 8601) and size in bytes.

**Returns**: Dictionary with:
- `last_modification`: ISO 8601 formatted timestamp (or None)
- `size`: File size in bytes (or None)

### get_project_file_path()

```python
def get_project_file_path(self, path: str) -> str
```

Resolves a possibly relative path to an absolute project path.

### get_valid_project_file_path()

```python
def get_valid_project_file_path(self, file_path: str) -> Tuple[str, any]
```

Validates and resolves a file path within the user's allowed projects. Prevents path traversal attacks using '..' sequences.

**Parameters**:
- `file_path`: The path to validate (absolute or relative)

**Returns**: Tuple of (absolute_path, project_settings)

**Raises**: ValueError if path is outside user projects or traversal is attempted

### get_readme()

```python
def get_readme(self) -> dict
```

Reads the project README.md and returns its content along with file metadata.

### get_wiki_file()

```python
def get_wiki_file(self, file_path: str) -> dict
```

Reads a wiki file and returns its content along with file metadata.

## Security Features

### Path Validation

The engine implements strict path validation through `get_valid_project_file_path()` to:
- Prevent path traversal attacks using '..' sequences
- Ensure all file operations stay within user's allowed projects
- Support both absolute and relative path resolution
- Handle cross-drive scenarios on Windows systems

### Git-Ignore Handling

All search and directory listing operations respect `.gitignore` files:
- Single scan of all `.gitignore` files per operation for performance
- Support for nested `.gitignore` files
- Cascade behavior: children of ignored directories are also ignored
- Optional `raw_search` parameter to include ignored files when needed

## Constants

- `GITIGNORE_FILE`: ".gitignore" - Name of the gitignore file
- `GIT_DIR`: ".git" - Name of the git directory (always skipped)
- `DEFAULT_MAX_FILE_SIZE`: 1 GB - Maximum file size for uploads
- `DEFAULT_MAX_TOTAL_SIZE`: 4 GB - Maximum total size for batch uploads

## Dependencies
**Imports from:** codx/junior/db.py, codx/junior/model/model.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py