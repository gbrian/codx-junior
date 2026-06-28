# Knowledge Document Loader

The `KnowledgeLoader` class is responsible for discovering, validating, and loading documents from a file system or Git repository structure into searchable document chunks. It supports incremental indexing by checking for recent modifications and updates based on timestamps and file integrity (MD5).

## Initialization

The loader requires configuration settings and optionally accepts a progress callback for tracking long-running processes.

***
**Function Signature:** `KnowledgeLoader(settings: CODXJuniorSettings, callback: Optional[ProgressCallback] = None)`
***

*   `self.path`: The absolute project path used as the source root. [Reference: `__init__`]
*   `self.settings`: Contains global configuration settings necessary for operations (e.g., external folder paths and ignore lists). [Reference: `__init__`]
*   `self.callback`: An optional progress hook that allows real-time tracking of the loading process (start, document processing, completion, errors). [Reference: `load_with_progress`]

## File Discovery and Validation

Before documents can be loaded, the class must identify which files are valid for indexing. The core logic handles both file path resolution within a Git repository and checking if the file needs re-indexing.

### 1. Listing Repository Files
The primary method for locating potential source material is `list_repository_files`. This method determines the list of all files to be processed by combining:

*   **Git Integration:** It first utilizes `git ls-files` and `git ls-files --others --exclude-standard` to gather versioned and unversioned file paths within a specified repository directory. [Reference: `get_git_files`]
*   **External Folders:** If configured, it also includes files from external knowledge folders defined in the settings. [Reference: `list_repository_files`]

### 2. Validity Checks
The class employs robust checks via `is_valid_file` and `should_index_doc` to determine if an already indexed file should be processed again.

**Criteria for Indexing:** A file is considered valid if: [Reference: `should_index_doc`]
1.  It exists as a file on the file system.
2.  (Optional) It matches a specified path or does not contain any ignored substrings.
3.  **Update Check (Incremental):**
    *   If no prior update data (`last_update`) exists, it is indexed by default.
    *   The file size must be within acceptable limits. [Reference: `should_index_doc`]
    *   If the file was modified within the last 10 minutes, or if its last modification time is newer than the stored update timestamp (`last_update`), it will be re-indexed.
4.  **Data Integrity Check (MD5):** If previous sources are known, the current MD5 hash of the file must match the previously recorded hash to proceed with indexing. [Reference: `should_index_doc`]

## Document Loading Methods

### Asynchronous Loading (`load_with_progress`)
This asynchronous method is designed for large-scale or network-intensive loading tasks and integrates progress tracking via an async callback. [Reference: `load_with_progress`]

**Parameters:**
*   `path`: An optional specific path to restrict the loading scope.
*   `last_update`: A timestamp specifying that only files modified after this time should be loaded (incremental).
*   `current_sources`: Dictionary of currently indexed sources.
*   `current_sources_and_updates`: Sources containing metadata for update checks (e.g., last stored update time).

**Process:**
1.  Retrieves the list of files to process using `list_repository_files`.
2.  Iterates through each file, passing it to the internal code splitter.
3.  Generates a document stream and sequentially extends the master document list (`documents`).
4.  Manages progress notifications:
    *   `ProgressEventType.STARTED`: Indicates total files and whether the run is incremental.
    *   `ProgressEventType.DOCUMENT_PROCESSING`: Reports progress per file, including source path and documents count.
    *   `ProgressEventType.BATCH_COMPLETE`: Summarizes the results, reporting total loaded documents, files processed, and invalid/empty documents.

### Synchronous Loading (`load`)
This synchronous method performs equivalent document loading to `load_with_progress` but without progress callback support. [Reference: `load`]

**Parameters:**
*   `current_sources_and_updates`: Metadata used for update checking (optional).
*   `path`: An optional path limit.
*   `current_sources`: Dictionary of currently indexed sources (optional).
*   `ignore_paths`: Paths that must be explicitly ignored during listing.

**Process:** The method executes file listing and document processing iteration, aggregating the results into a list of loaded documents.

## Utilities

### Code Splitting and Document Enrichment
All loading methods rely on an internal `KnowledgeCodeSplitter`. This object is responsible for taking raw source files (like code) and splitting them into structured documents suitable for indexing and retrieval. [Reference: `load_with_progress`, `load`] The resultant documents are filtered to ensure they have non-empty content before being returned.

### Directory Discovery
The method `list_repository_folders` gathers all unique parent directories found among the files that were successfully targeted for loading, providing insight into the organizational structure of the indexed knowledge base. [Reference: `list_repository_folders`]

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/knowledge/knowledge_code_splitter.py, codx/junior/knowledge/knowledge_code_to_dcouments.py, codx/junior/engine/progress_callback.py, codx/junior/utils/utils.py
**Imported by:** codx/junior/engine/session.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/wiki/wiki_manager.py