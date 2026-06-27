### ChangeManager Overview

The `ChangeManager` class is responsible for detecting and processing changes in source files within a registered project, ensuring that associated knowledge components, mentions, and internal documentation are kept current. It coordinates updates across various managers, including `MentionManager`, `Knowledge` repository, and `WikiManager`.

#### Initialization

The manager requires settings information (`self.settings`) which point to the project directory (`self.settings.codx_path`). Upon initialization, it sets up the following managed components:
*   `EventManager`: For tracking events related to knowledge loading.
*   `MentionManager`: To check files for mentions.
*   `Knowledge`: The core repository manager used for detecting changes and reloading content.
*   `WikiManager`: To handle building project wiki pages when configured (`self.settings.project_wiki`).
*   `AudioManager`: For handling audio transcription processes.

#### Core Functionality

##### `process_project_changes(self)`

This asynchronous method is the primary entry point for handling file changes within a single project. It executes the following sequence of updates:

1.  **Detect Changes:** Retrieves all current sources and updates, using `self.knowledge.detect_changes()` to identify new or modified files (`new_files`).
2.  **Check Mentions:** Processes mentions immediately for every file found in `new_files` by calling `process_project_mentions()`. These checks run concurrently.
3.  **Cleanup (Partial):** Calls `self.knowledge.clean_deleted_documents()` to handle indexing cleanup.
4.  **Filter Valid Paths:** Filters the list of new files, keeping only those whose modification time (`st_mtime`) is less than the defined constant `MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS`. This generates the list of truly *new* or recent files to process.
5.  **Process Files:** Runs all validated file paths through `process_project_change()` concurrently using `asyncio.gather()`.

##### `check_mentions_on_all_projects(cls, all_projects)` (Class Method)

This method is designed for checking mentions across multiple projects (`all_projects`). It iterates through each project:
1.  Initializes a fresh `ChangeManager` instance for the current project.
2.  Fetches and detects all changes in the project's sources.
3.  Filters these changes to find recent files (modification time within `MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS`).
4.  For every recent file, it appends an asynchronous task calling `process_project_mentions()`.
5.  Finally, it runs all collected tasks across all projects concurrently using `asyncio.gather()`.

##### `process_project_mentions(self, file_path: str)`

This method is a wrapper that delegates the mention checking task to the dedicated `MentionManager`, ensuring the provided `file_path` is checked for document mentions.
*   **Action:** Calls `self.mention_manager.check_file_for_mentions()` on the given path.

##### `process_project_change(self, file_path: str)`

This detailed processing method handles a single file update and performs several sequential tasks:

1.  **Media Handling Check:** Determines if the file is a valid media file using `self.audio_manager.is_valid_media_file()`.
2.  **Audio Transcription (If applicable):** If it is a media file, it initiates transcription via `self.audio_manager.transcribe_from_file()`.
    *   The knowledge base index is updated with document metadata indicating the source and language ("audio" type).
    *   If transcription confirms new content (`transcript_info["is_new"]`), the `file_path` is replaced with the generated transcript path. Otherwise, processing halts for this file.
3.  **Knowledge Reload:** The core knowledge base tracks the updated path by calling `self.knowledge.reload_path()`.
4.  **Event Emission:** An event of type `"loaded"` is sent via `self.event_manager` and passed with the `file_path`.
5.  **Wiki Update (If configured):** If `self.settings.project_wiki` is enabled, it asynchronously calls `self.wiki_manager.build_file(file_path)` to update the project's wiki page structure.

#### Metrics Management

The `update_project_metrics()` method initializes the `CODXJuniorMetrics` system and executes `project_metrics()`. This function is responsible for updating internal tracking metrics related to the project's activity.

## Dependencies
**Imports from:** codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/globals.py, codx/junior/mentions/mention_manager.py, codx/junior/profiling/profiler.py, codx/junior/wiki/wiki_manager.py, codx/junior/whisper/audio_manager.py, codx/junior/metrics/codx_junior_metrics.py
**Imported by:** codx/junior/background.py, tests/test_change_manager.py