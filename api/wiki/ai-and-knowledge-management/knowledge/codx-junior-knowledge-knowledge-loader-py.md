# Knowledge Loader Documentation

## Overview

The `KnowledgeLoader` class is responsible for loading documents from a filesystem and preparing them for knowledge indexing. It handles file validation, incremental loading, progress tracking, and integration with code splitting utilities.

## Initialization

```python
KnowledgeLoader(settings: CODXJuniorSettings, callback: Optional[ProgressCallback] = None)
```

Creates a new instance with project settings and optional progress callback for tracking loading operations.

**Parameters:**
- `settings`: Configuration object containing project paths and knowledge settings
- `callback`: Optional callback for progress event notifications

## File Validation

### should_index_doc

Determines whether a file should be indexed based on multiple criteria:

- **Size constraints**: Files must be between 0 and 50KB
- **Modification recency**: Files modified within the last 10 minutes are excluded
- **Content changes**: Uses MD5 hash comparison to detect file modifications
- **Update timestamp**: Compares file modification time against the last update timestamp

Returns `True` if the file meets all indexing criteria, `False` otherwise.

### is_valid_file

Validates whether a file is eligible for indexing by checking:

- File existence and type validation
- Path matching (if a specific path is provided)
- Ignore pattern matching against configured exclusion patterns
- Historical update checks using `should_index_doc`

Returns `True` if the file passes all validation checks.

## Document Loading

### load_with_progress

Asynchronously loads documents with progress event callbacks:

```python
async def load_with_progress(
    path: Optional[str] = None,
    last_update: Optional[float] = None,
    current_sources: Optional[Dict] = None,
    ignore_paths: Optional[List[str]] = None,
    current_sources_and_updates: Optional[Dict] = None,
) -> List
```

**Parameters:**
- `path`: Optional specific path to load
- `last_update`: Only load files modified after this timestamp
- `current_sources`: Currently indexed sources dictionary
- `ignore_paths`: List of paths to exclude from loading
- `current_sources_and_updates`: Sources with update metadata

**Progress Events:**
- `STARTED`: Initial event with total file count
- `DOCUMENT_PROCESSING`: Per-file progress updates
- `BATCH_COMPLETE`: Final summary with document statistics

Filters out empty documents and returns only documents with valid content.

### load

Synchronous version of document loading:

```python
def load(
    current_sources_and_updates: datetime = None,
    path: str = None,
    current_sources=None,
    ignore_paths=[]
) -> List
```

Loads documents without progress callbacks. Applies the same filtering logic to return only documents with valid page content.

## Repository File Discovery

### get_git_files

Retrieves all tracked and untracked files from a Git repository:

- Executes `git ls-files` to get versioned files
- Executes `git ls-files --others --exclude-standard` to get unversioned files
- Returns full file paths filtered to the current project path

### list_repository_files

Compiles a comprehensive list of files to process:

```python
def list_repository_files(
    current_sources_and_updates = None,
    path: str = None,
    current_sources=None,
    ignore_paths=[]
) -> List[str]
```

**Behavior:**
- If `path` is specified: Returns files from that path
- If no path: Uses Git repository files
- Includes external folders from `knowledge_external_folders` setting
- Applies ignore patterns from configuration and parameters
- Validates each file using `is_valid_file`

### list_repository_folders

Returns a deduplicated list of all folders containing valid documents.

## Git Integration

### run_git_command

Executes Git commands and returns stdout/stderr:

```python
def run_git_command(command, cwd: str = None) -> Tuple[List[str], Optional[str]]
```

Splits command output by newlines for file path processing.

### fix_repo

Resolves Git dubious ownership errors by executing the suggested `git config` fix command from error messages.

## Ignore Patterns

File exclusion is controlled through the `knowledge_file_ignore` setting, which accepts comma-separated patterns. Files matching any pattern are excluded from indexing.

## Error Handling

- File loading errors are logged and skipped during batch processing
- Invalid documents (empty content) are filtered out with debug logging
- Progress callbacks receive error details when exceptions occur
- Git command errors are captured and processed for repository repair

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/knowledge/knowledge_code_splitter.py, codx/junior/knowledge/knowledge_code_to_dcouments.py, codx/junior/engine/progress_callback.py, codx/junior/utils/utils.py
**Imported by:** codx/junior/engine/session.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/wiki/wiki_manager.py