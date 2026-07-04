## CODXJuniorSession API Reference

The `CODXJuniorSession` class acts as the primary orchestration layer for the entire codx-junior engine. It manages settings, initializes core sub-engines (Knowledge, Code, Git, File, Chat), and provides unified methods for interacting with project context, AI services, and file operations.

### Initialization and Configuration

**`__init__(self, settings: CODXJuniorSettings = None, codx_path: str = None, channel: SessionChannel = None, user: CodxUser = None)`**
Initializes the session, loading configuration from `project.json` or provided settings. It instantiates all required sub-engines, including `KnowledgeEngine`, `CodeEngine`, `GitEngine`, etc., using the given project context.

### Core Session Methods

**`update_last_access_time() -> None`**
Updates the system settings with the current timestamp for tracking last access activity.

**`switch_project(self, project_id: str) -> "CODXJuniorSession"`**
Switches the operational session context to a different project using its unique ID. Returns a new `CODXJuniorSession` instance if a matching project is found.

**`log_info(self, msg: str, *args) -> None`**
Logs an informational message, automatically prepending the current project name for context.

**`log_error(self, msg: str, *args) -> None`**
Logs an error message, automatically prepending the current project name for context.

**`log_exception(self, msg: str, *args) -> None`**
Logs a full stack trace exception, automatically prepending the current project name for context.

**`coder_open_file(self, file_name: str) -> dict`**
Opens a specified file in an external code server editor command.

**`chat_action(self, chat: Chat, event: str)`**
A context manager (`@contextmanager`) used to wrap complex chat actions. It notifies the system about the start and completion (or error) of an action within the `EventManager`.

**`delete_project(self) -> None`**
Deletes the entire project directory associated with the current session settings using `shutil.rmtree()`.

### Manager Factories

These methods provide controlled access points to specialized manager classes, ensuring proper dependency injection (e.g., passing the `EventManager` and `settings`).

*   **`get_mention_manager(self) -> MentionManager`**: Returns an instance of `MentionManager` for handling `@mentions`.
*   **`get_chat_manager(self) -> ChatManager`**: Returns an instance of `ChatManager` responsible for chat history management.
*   **`get_profile_manager(self, settings: CODXJuniorSettings = None) -> ProfileManager`**: Returns an instance of `ProfileManager` for handling user/AI profiles.
*   **`get_ai(self, llm_model: str = None) -> AI`**: Returns an `AI` instance configured with the session's settings and optionally a specific LLM model.
*   **`get_knowledge(self) -> Knowledge`**: Returns the primary `Knowledge` management instance.
*   **`get_wiki(self)`**: Returns a dedicated `WikiManager`.
*   **`get_browser(self) -> Browser`**: Returns an instance of `Browser` for web interaction tasks.

### Chat Management Operations

These methods wrap `ChatManager` functionality and are crucial for persistent conversations.

**`load_chat(self, board: str, chat_name: str)`**
Loads a specific chat history based on the board identifier and name. (Uses `@profile_function`).

**`list_chats(self, from_date: str = None) -> list`**
Retrieves a list of all existing chats. Optionally filters the results by `from_date`.

**`save_chat(self, chat: Chat, chat_only: bool = False) -> Chat`**
Persists or updates an existing chat object in the database. Ensures data integrity and availability for later context retrieval.

**`delete_chat(self, chat_id: str) -> None`**
Deletes a specific chat thread given its unique ID.

### Profile Management Operations

These methods utilize `ProfileManager` to read, write, and manage user or system profiles.

**`list_profiles() -> list`**: Lists all available saved profiles (e.g., "project", "developer"). (Uses `@profile_function`).
**`save_profile(self, profile: Profile) -> Profile`**: Persists a `Profile` object to be used in the session's configuration or context. (Async, Uses `@profile_function`).
**`watch_project(self, watching: bool) -> None`**: Changes and saves the project settings watch status (`watching`).
**`read_profile(self, profile_name: str) -> Profile`**: Retrieves a specific `Profile` by name.
**`delete_profile(self, profile_name: str) -> None`**: Removes a saved profile by its name.

### Utilities and Helper Methods

**`extract_query_mentions(self, query: str) -> list`**
Parses an input string (`query`) to identify all `@mention` references (e.g., `@user`, `@project`).

**`get_query_mentions(self, query: str) -> list`**
A generalized function that retrieves *all* types of mentions (User, Project, etc.) from a given query string.

### Knowledge Base Operations (`KnowledgeEngine`)

These methods handle indexing, searching, and managing contextual knowledge documents. They delegate core logic to the `KnowledgeEngine`.

*   **`knowledge_search(self, knowledge_search: KnowledgeSearch) -> dict`**: Executes a comprehensive search across all indexed project knowledge bases using criteria defined in `KnowledgeSearch`. (Async, Uses `@profile_function`).
*   **`delete_knowledge_source(self, sources: list) -> dict`**: Removes documents from the index based on their filesystem paths.
*   **`index_knowledge_source(self, sources: list) -> dict`**: Processes and indexes new knowledge by ingesting document content from specified source paths.
*   **`find_project_documents(self, query: str) -> list`**: Finds documents within the context of a specific project relevant to the search `query`. (Uses `@profile_function`).
*   **`select_afefcted_documents_from_knowledge(...) -> tuple`**: Advanced selection method used to determine the most pertinent knowledge documents based on chat history, AI state, and query constraints. (Uses `@profile_function`).

### Code and File System Operations (`CodeEngine`, `FileEngine`)

These methods are responsible for physical file interaction and code generation/modification within the project structure.

**`excute_bash_code(self, chat: Chat, code_block_info: dict) -> None`**: Executes a bash code block provided by the AI or user in a sandbox environment. (Async).
**`generate_code(self, chat: Chat, code_block_info: dict) -> None`**: Requests and applies generated code content based on an instruction set (`code_block_info`). (Async).
**`improve_existing_code_patch(...) -> tuple`**: Applies a targeted patch to improve existing source code. (Async).

**`apply_improve_code_changes(...) -> None`**: Takes structured `AICodeGenerator` output and writes the changes back into the local file system. (Sends the actual code diffs). (Async, Uses `@profile_function`).

**`change_file(self, context_documents: list, query: str, file_path: str, org_content: str, save_changes: bool = False) -> str`**: The primary mechanism for complex file rewriting. It takes existing content (`org_content`), relevant knowledge documents, and a rewriting `query`, then optionally saves the resulting file. (Async, Uses `@profile_function`).

**`read_file(self, path: str) -> str`**: Reads the raw text content of any project file given its path.
**`write_project_file(self, file_path: str, content: str, process: bool = True) -> dict`**: Writes new `content` to a specified file. If `process=True`, it runs configured file profiles and hooks before committing the change. (Async).

### Git Operations (`GitEngine`)

A comprehensive set of methods for interacting with version control history.

*   **`get_repo_branches() -> list`**: Lists all accessible git branches in the repository.
*   **`get_project_changes(self, parent_branch: str = None) -> dict`**: Calculates and returns file differences (`diff`) between the project's current state and a specified `parent_branch`.
*   **`get_pr_review_details(self, from_branch: str, to_branch: str) -> list`**: Retrieves detailed review information, typically used for Pull Requests, comparing changes between two branches.
*   **`build_code_changes_summary(self, force: bool = False) -> object`**: Generates a high-level summary of all code file changes, often useful for reporting or PR descriptions.

### Chat Flow Operations (`ChatEngineActions`)

These methods facilitate complex interactions between chat history and system context.

**`chat_search(self, chat_id: str, query: str) -> tuple`**: Executes a search while maintaining the conversational context of a specific chat ID. (Async, Uses `@profile_function`).
**`api_chat_with_project(...) -> Chat`**: Initiates a sophisticated chat session treating the project itself as an API endpoint for interaction. (Async, Uses `@profile_function`).
**`chat_with_project(self, ...)`**: The core chat interaction method. Manages state by using AI, leveraging knowledge bases (`disable_knowledge`), and maintaining conversation context over multiple iterations. (Async, Uses `@profile_function`).

### Wiki Operations (`WikiEngine`)

Methods related to managing internal project documentation systems.

*   **`process_wiki_changes() -> None`**: Handles asynchronous processing of changes detected in wiki documentation sources.
*   **`update_wiki(self, file_path: str) -> None`**: Triggers the system to update or regenerate parts of the wiki based on external file changes.

### Misc Utility Methods

**`check_project() -> None`**: Runs a self-diagnostic check to validate and fix the underlying project knowledge loading mechanism.
**`run_app(self, app_name: str) -> None`**: Executes predefined command sequences or tools associated with the project (e.g., running specific build scripts).

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_keywords.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/mentions/mention_manager.py, codx/junior/model/model.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/project/project_discover.py, codx/junior/settings.py, codx/junior/sio/session_channel.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/whisper/audio_manager.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/code_engine.py, codx/junior/engine/git_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/wiki_engine.py, codx/junior/wiki/wiki_manager.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/globals.py
**Imported by:** codx/junior/api/knowledge.py, codx/junior/engine.py, codx/junior/engine/__init__.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/git_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/wiki_engine.py