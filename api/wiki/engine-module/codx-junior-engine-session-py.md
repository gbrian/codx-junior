# CODXJuniorSession Engine Module

The `CODXJuniorSession` class serves as the central orchestration hub for the `codx-junior` engine. It acts as a facade, coordinating various sub-engine modules and managers to handle project creation, session management, and backend logic.

## Architecture and Orchestration
The session class manages the lifecycle of a project and delegates specialized tasks to dedicated engine components:

*   **KnowledgeEngine**: Handles knowledge indexing, search operations, and project document retrieval.
*   **CodeEngine**: Manages code generation, patching, file-based improvements, and shell execution.
*   **GitEngine**: Oversees version control operations, branch management, and change tracking.
*   **FileEngine**: Performs file system operations, including reading, writing, and path resolution.
*   **ChatEngineActions**: Manages chat flows, API interactions, and conversation context.
*   **WikiEngine**: Coordinates documentation updates and wiki management.

## Core Session Functionality
The session provides methods for managing the state of the active environment:

*   **Project Management**: Includes `switch_project`, `delete_project`, `watch_project`, and `check_project` to maintain and repair the project environment.
*   **Session Lifecycle**: Tracks access times via `update_last_access_time` and handles event logging and exception tracking.
*   **Editor Integration**: The `coder_open_file` method facilitates opening project files directly in the `code-server` editor.

## Sub-engine Delegations
Functionality is categorized by the specific engine responsible for execution:

### Knowledge Operations
Located in the **Knowledge operations (delegated)** section, these methods provide the ability to:
*   Perform semantic searches using `knowledge_search` and `project_search`.
*   Maintain the knowledge base through `reload_knowledge`, `index_knowledge_source`, and `delete_knowledge`.
*   Process background tasks like `process_project_changes` and `process_project_mentions`.

### Code Operations
Defined in the **Code operations (delegated)** section, these methods allow for:
*   AI-driven code modification via `generate_code`, `improve_existing_code`, and `change_file`.
*   System command execution using `excute_bash_code`.
*   Applying standardized patches and testing through `apply_patch` and `project_script_test`.

### Git Operations
Managed under the **Git operations (delegated)** section, these methods enable:
*   Branch inspection using `get_repo_branches` and `get_project_branches`.
*   Tracking history via `get_branch_commits` and `get_branch_details`.
*   Analyzing changes between branches via `get_repo_changes` and `get_project_changes`.

### File Operations
Handled in the **File operations (delegated)** section, these methods provide:
*   Safe interaction with the file system including `read_file`, `write_project_file`, and `read_directory`.
*   Content transformation and validation through `process_project_file_before_saving` and `get_valid_project_file_path`.
*   Utilities for diffing files and OCR processing via `api_image_to_text`.

## Chat and Context Management
The session provides several factory methods and utilities to manage user interactions:
*   **Managers**: Provides access to `MentionManager`, `ChatManager`, and `ProfileManager` for granular control over user-specific data.
*   **Chat Processing**: Uses `chat_with_project` to orchestrate AI responses with knowledge context, while `summarize_chat` and `generate_tasks` assist in maintaining conversation structure.
*   **Mention Utilities**: Extracts and identifies references to projects or profiles from raw text strings using `extract_query_mentions`.

## Critical Operational Instructions
When interacting with AI, the engine enforces strict protocols defined in `GLOBAL_CHAT_INSTRUCTIONS`:
*   **Formatting**: Code blocks must specify the file name (e.g., ` ```js /path/file.js `).
*   **Content Handling**: The system enforces a policy against guessing missing file content. It requires the use of a `patch` language block for partial updates or a `file-request` block to signal missing context to the user.

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_keywords.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/mentions/mention_manager.py, codx/junior/model/model.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/project/project_discover.py, codx/junior/settings.py, codx/junior/sio/session_channel.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/whisper/audio_manager.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/code_engine.py, codx/junior/engine/git_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/wiki_engine.py, codx/junior/wiki/wiki_manager.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/globals.py
**Imported by:** codx/junior/api/knowledge.py, codx/junior/engine.py, codx/junior/engine/__init__.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/git_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/wiki_engine.py