# KnowledgeLoader API Documentation

The `KnowledgeLoader` class is responsible for orchestrating the process of discovering, filtering, validating, and loading documents from a project's filesystem while supporting incremental updates based on source changes.

## Initialization

The loader requires an instance of settings (`CODXJuniorSettings`) upon initialization. It optionally accepts a progress callback object (`ProgressCallback`).

```python
__init__(self, settings: CODXJuniorSettings, callback: Optional[ProgressCallback] = None)
```

## File Discovery and Validation

The class utilizes several internal methods to determine which files are eligible for indexing.

### `should_index_doc(file_path, last_update, current_sources)`

This method evaluates whether a given file should be indexed based on several criteria:

*   **Initial Pass:** If no `last_update` timestamp is provided, the file is considered indexable (`True`).
*   **Size Check:** The file must have a size greater than zero bytes and less than 50 KB. Files failing this check return `False`.
*   **Time Sensitivity:** If the file was modified within the last 10 minutes of the current runtime, it is considered *not* indexable for incremental runs (`False`).
*   **Content Check (MD5):** If tracking sources (`current_sources`) is active, the function compares the current MD5 hash of the file against the previously stored one. If they match, indexing is skipped (`False`).
*   **Metadata Check:** Finally, the physical last modification time (`st_mtime`) must be newer than the provided historical `last_update` timestamp to proceed with indexing.

### `is_valid_file(file, current_sources_and_updates=None, path=None, current_sources=None, knowledge_file_ignore: [str] =[])`

This comprehensive validation function verifies a file against multiple constraints:

1.  Checks if the provided `file` is an actual existing file on disk.
2.  If a specific resource `path` is required, it ensures the file matches that path.
3.  It checks if the file name or path matches any configured ignore patterns (`knowledge_file_ignore`). If matched, the file is ignored.
4.  It attempts to retrieve a historical `last_update` timestamp from metadata.
5.  Crucially, it calls `should_index_doc`. The file is marked as invalid if this internal check returns `False` (due to size, time, or content stability).

### `list_repository_files(...)`

This main directory listing method generates a list of file paths that are valid and eligible for indexing.

*   **Functionality:** It collects files from the repository using Git tracking (`git ls-files`, including unversioned files) and also integrates any configured external knowledge folders.
*   **Filtering:** Every identified file path is passed through `is_valid_file` to ensure only current, meaningful sources are returned.

## Loading Operations

### `load_with_progress(...)` (Asynchronous API)

This asynchronous method facilitates the loading of documents from disk while providing detailed progress updates via an optional callback mechanism.

**Arguments:**

*   `path` (Optional[str]): Specific path to load if not searching the whole repository.
*   `last_update` (Optional[float]): Limits loading to files modified after this timestamp for incremental runs.
*   `current_sources` (Optional[Dict]): The currently indexed sources map used for content checks.
*   `ignore_paths` (Optional[List[str]]): Explicit paths to ignore during the run.
*   `current_sources_and_updates` (Optional[Dict]): Sources containing metadata necessary for tracking updates, including historical `last_update` times.

**Process Flow:**
1.  Retrieves all files using `list_repository_files`.
2.  For each file, it uses the internal splitter (`KnowledgeCodeSplitter`) to generate documents.
3.  During processing, if a callback is provided, progress events are emitted for `STARTED`, individual `DOCUMENT_PROCESSING` steps (showing source and document count), and finally, `BATCH_COMPLETE`.

**Returns:**
A list of processed documents (`List[Document]`), filtered to exclude those with empty page content.

### `load(...)` (Synchronous API)

This synchronous method provides a standard way to load and process files from the repository without progress reporting.

**Arguments:**

*   `current_sources_and_updates` (Optional[datetime]): Metadata map for tracking source updates needed for incremental runs.
*   `path` (Optional[str]): Specific path to limit loading scope.
*   `current_sources` (Optional[Dict]): The currently indexed sources map used for content checks.
*   `ignore_paths` (List[str]): Paths that should be ignored during the run.

**Returns:**
A list of loaded documents (`List[Document]`) with empty-content documents filtered out.

## Utilities and Helpers

### `get_git_files()`

This method executes Git commands to identify all files within the configured path:

*   It determines the repository's parent folder by querying `.git/dir`.
*   It uses `git ls-files` to retrieve both versioned files and files that are unversioned but tracked (`--others --exclude-standard`).
*   The resulting file paths are filtered to ensure they start with the root project path.

### `list_repository_folders()`

Delegates internal calls to `list_repository_files()` and extracts all top-level directories found among the valid source files, returning a set of unique folder paths.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/knowledge/knowledge_code_splitter.py, codx/junior/knowledge/knowledge_code_to_dcouments.py, codx/junior/engine/progress_callback.py, codx/junior/utils/utils.py
**Imported by:** codx/junior/engine/session.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/wiki/wiki_manager.py