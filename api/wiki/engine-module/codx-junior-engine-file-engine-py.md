# File Engine Module Documentation

## Overview

The File Engine is a comprehensive subsystem for managing file operations within the codx-junior project. It handles reading, writing, diffing files, and manages git-ignore rules efficiently through the `GitIgnoreManager` class. The engine integrates with the session management system and provides file profile application capabilities.

## Core Components

### GitIgnoreManager

The `GitIgnoreManager` class provides efficient checking of whether files are git-ignored by pre-loading all `.gitignore` rules found within a directory tree.

#### Key Features

- **In-Memory Rule Processing**: Reads every `.gitignore` file once and performs all checks in memory using the `pathspec` library instead of spawning subprocesses
- **Nested .gitignore Support**: Each `.gitignore` applies to its own directory and all subdirectories, matching git's actual behavior
- **Directory Cascade Handling**: Correctly handles the case where a parent directory is ignored - any file or directory inside an ignored directory is also considered ignored

#### Main Methods

**`__init__(root_path: str)`**
- Initializes and pre-loads all `.gitignore` rules under the specified root path
- Stores directory-to-PathSpec mappings and maintains an ignored directories cache

**`is_ignored(abs_path: str) -> bool`**
- Checks whether a file or directory is matched by any `.gitignore` rule
- Handles both direct pattern matches and cascade from parent directories
- Returns `False` for paths outside the root tree

**`_is_dir_ignored(abs_dir_path: str) -> bool`**
- Checks whether a directory itself is matched by any `.gitignore` rule
- Results are cached to avoid redundant work
- Bounded by two base cases: reaching the root or escaping the root path

### FileEngine

The `FileEngine` class serves as the main interface for file system operations within the project scope.

#### Initialization

**`__init__(session: "CODXJuniorSession")`**
- Initializes with a reference to the parent session
- Provides access to session settings and profile management

## Core Methods

### Reading Files

**`read_file(path: str) -> dict`**
- Reads a project file and returns its content along with metadata
- Accepts relative or absolute paths
- Returns dictionary containing `content`, `last_modification`, and `size`

**`read_directory(path: str) -> dict`**
- Lists the contents of a directory, flagging git-ignored entries
- Automatically cascades ignored status to children
- Returns directory metadata and sorted file list with ignore flags

**`get_file_info(file_path: str) -> dict`**
- Returns metadata for a file: `last_modification` (ISO 8601) and `size` in bytes
- Handles both relative and absolute paths
- Returns `None` values if file doesn't exist

### Writing Files

**`write_project_file(file_path: str, content: str, process: bool = True) -> dict`**
- Writes content to a project file
- Optionally processes content through file profiles before writing
- Creates parent directories as needed
- Returns file and project metadata including modification time and size

**`process_project_file_before_saving(file_path: str, content: str) -> str`**
- Applies all matching file profiles to content before saving
- Retrieves profiles from the session's profile manager
- Returns processed file content

**`apply_file_profile(file_path: str, content: str, profile: Profile) -> str`**
- Applies a single file profile to content using AI
- Uses the chat system with project knowledge disabled
- Returns improved file content without decorations

### File Comparison

**`diff_file(path: str, content: str, from_branch: str = None, to_branch: str = None) -> dict`**
- Diffs a project file against provided content using `git diff --no-index`
- Returns dictionary with `diff`, `stats`, `last_modification`, and `size`
- Branch parameters reserved for future use

**`diff_file_comments(path: str, content: str, comments: dict = None) -> None`**
- Placeholder for diffing files with inline comments (not yet implemented)

### File Search Operations

**`search_files(search: str, search_path: str = None, page: int = 0, page_size: int = 50, raw_search: bool = False) -> dict`**
- Searches for files whose paths contain the search pattern
- Performs filesystem search within the project
- Respects `.gitignore` rules unless `raw_search=True`
- Returns paginated results with ignore flags

**`search_files_content(query: str, search_path: str = None, page: int = 0, page_size: int = 50, case_sensitive: bool = False, raw_search: bool = False) -> dict`**
- Searches for file content matching a query pattern
- Supports case-sensitive and case-insensitive searches
- Respects `.gitignore` rules unless `raw_search=True`
- Returns paginated results with match metadata including line numbers and match counts

### Path Validation

**`get_valid_project_file_path(file_path: str) -> Tuple[str, any]`**
- Validates and resolves a file path within allowed user projects
- Handles both absolute and relative paths
- Prevents path traversal attacks using `..` sequences
- Returns tuple of `(absolute_path, project_settings)`

**`get_project_file_path(path: str) -> str`**
- Convenience method that resolves a path to absolute project path
- Returns only the absolute path string

**`_resolve_absolute_path(file_path: str) -> Tuple[str, any]`**
- Resolves and validates absolute file paths
- Checks current project first, then falls back to all user projects
- Raises `ValueError` if path is outside all allowed projects

**`_resolve_relative_path(norm_input_path: str, original_path: str) -> Tuple[str, any]`**
- Resolves and validates relative paths within current project root
- Ensures path doesn't escape project using `..` sequences
- Raises `ValueError` if traversal is attempted

### Project Documentation

**`get_readme() -> dict`**
- Reads the project `README.md` file
- Returns dictionary with `content`, `last_modification`, and `size`
- Returns empty content if README doesn't exist

**`get_wiki_file(file_path: str) -> dict`**
- Reads a wiki file from the project wiki directory
- Accepts relative paths within wiki structure
- Returns file content with metadata or "not found" message

### Utility Methods

**`get_file_info(file_path: str) -> dict`**
- Returns file metadata with last modification time (ISO 8601 format) and size in bytes

**`parse_file_line(file: str, base_path: str, gitignore_manager: Optional[GitIgnoreManager] = None, parent_is_ignored: bool = False) -> dict`**
- Parses a file name into a structured dictionary for directory listings
- Supports cascade of ignored status from parent directories
- Returns entry with name, path, directory flag, ignored flag, and file metadata

**`_build_gitignore_manager(search_root: str) -> GitIgnoreManager`**
- Creates a GitIgnoreManager pre-loaded with all `.gitignore` rules under the search root
- Ensures `.gitignore` files are read once per search operation

**`_resolve_search_root(search_path: Optional[str]) -> Optional[str]`**
- Resolves the root directory for search operations
- Returns `None` if the specified path is not a directory

**`_search_in_file(...) -> Optional[dict]`**
- Searches for a pattern inside a single file
- Returns match metadata including line numbers and match counts per line
- Returns `None` if no matches found

### Image Processing

**`api_image_to_text(image_bytes: bytes) -> str`**
- Converts image bytes to text using OCR (pytesseract)
- Accepts raw image bytes
- Returns extracted text string

## Performance Considerations

- **GitIgnore Efficiency**: The `GitIgnoreManager` loads all `.gitignore` files once at initialization, reducing overhead from O(files) to O(directories)
- **Directory Pruning**: In search operations, ignored directories are pruned in-place during tree walks, preventing traversal of irrelevant subtrees
- **Caching**: Ignored directory results are cached to avoid redundant checks when processing children
- **Early Termination**: Path searches stop climbing the directory tree once the root is reached

## Security Features

- **Path Traversal Prevention**: Validates that paths don't escape project boundaries using `..` sequences
- **Drive Boundary Handling**: Prevents path operations across different drives on Windows
- **Access Control**: Absolute paths are validated against all user-allowed projects
- **Normalization**: All paths are normalized before comparison

## Dependencies
**Imports from:** codx/junior/db.py, codx/junior/model/model.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py