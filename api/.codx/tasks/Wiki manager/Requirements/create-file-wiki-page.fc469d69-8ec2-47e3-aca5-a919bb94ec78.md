# [[{"id": "fc469d69-8ec2-47e3-aca5-a919bb94ec78", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/wiki/wiki_manager.py", "/shared/codx-junior/api/codx/junior/background.py", "/shared/codx-junior/api/codx/junior/changes/change_manager.py"], "check_lists": [], "profiles": ["software_developer"], "users": ["admin"], "name": "Create file wiki page", "description": "The project uses a system to monitor and manage file changes utilizing background services, asynchronous processing, and AI-generated content updates. Background services continuously check projects for changes, managing them through a quarantine system to handle any processing errors. The Change Manager asynchronously processes file changes, validating and updating knowledge as necessary, including special handling for media files. The Wiki Manager builds and updates project documentation, reflecting recent changes using AI for content creation. This efficient system ensures documentation and project structure are kept up-to-date with file modifications.", "created_at": "2025-08-13 05:51:57.102854", "updated_at": "2025-08-14T05:04:47.111368", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Wiki manager", "column": "Requirements", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Wiki manager/Requirements/create-file-wiki-page.fc469d69-8ec2-47e3-aca5-a919bb94ec78.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "f293f92c-c89c-475b-b44c-480a87898088", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-13 05:51:57.100878", "updated_at": "2025-08-13 05:51:57.100904", "images": [], "files": ["/shared/codx-junior/api/codx/junior/wiki/wiki_manager.py", "/shared/codx-junior/api/codx/junior/background.py", "/shared/codx-junior/api/codx/junior/changes/change_manager.py"], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
@background.py @change_manager.py @wiki_manager.py


Analize how project's file changes are managed. How it work, explain what we do with the files
## [[{"doc_id": "4858fa7f-5483-49ef-acbc-018290037058", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-08-13 05:51:57.100878", "updated_at": "2025-08-13 05:51:57.100904", "images": [], "files": [], "meta_data": {"time_taken": 27.161272764205933, "first_chunk_time_taken": 0.00020647048950195312, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
### Overview

The management of project file changes involves a comprehensive system consisting of background processes, event management, and knowledge updating. This system ensures that any modifications in the project's files are processed and reflected in various systems like the wiki. The code base utilizes threading, asynchronous programming, and AI to intelligently update documentation and handle changes.

### Main Components and Flow

1. **Background Services (`background.py`):**
   - **Initialization:** A function `start_background_services()` initiates background services to continuously monitor and process changes in project files.
   - **Quarantine Management:** Projects can be placed in a "quarantine" if errors occur during processing. Projects in quarantine are checked based on a delay strategy defined by `QUARANTINE_DELAYS`.
   - **Continuous Checking:** The `check_projects()` function continuously monitors all projects. It skips projects in quarantine and runs checks using asyncio to handle concurrency.
   - **Async Processing:** `check_project()` is run asynchronously for each project to handle file changes and update their status in the quarantine system.

2. **Change Management (`change_manager.py`):**
   - **File Change Detection:** The `check_project_changes()` function utilizes a knowledge base to detect changes in project files.
   - **Async Processing:** A major functionality is to process file changes asynchronously using `asyncio.gather()` to handle multiple files concurrently. This is facilitated by the `process_project_changes()` method.
   - **File Validation:** Each file's modification time is checked to verify its validity in terms of recent changes. The decision is based on constants like `MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS`.
   - **Handling Media Files:** Special handling for media files via the `AudioManager` allows transcription and indexing of audio content. Once processed, the file path might be updated to reflect the new text-based transcript.

3. **Wiki Management (`wiki_manager.py`):**
   - **Initial Setup:** The `WikiManager` sets up a documentation platform (VitePress) to display project information.
   - **Building & Updating:** On detecting a change, relevant markdown files are created or updated to reflect the latest project structure and content (methods like `build_file()` and `build_wiki()`).
   - **Content Generation:** Uses AI to generate meaningful content for documentation, automatically adapting changes and possibly adding diagrams or other illustrative content.
   - **Configuration and Structure Management:** The wiki structure is rebuilt as per the detected changes, and configuration files are updated to reflect new files, changes, or deletions.

### Process Workflow

1. **Start Background Services:** Activate the monitoring functions and reload necessary AI models.
2. **Continuous Monitoring:** Projects are continuously checked for changes via `check_projects()`, handling each project's update concurrently.
3. **File Change Processing:**
   - Detect any changes or deletions in files.
   - If new valid files are detected, process them concurrently.
   - Each file is checked for mentions and knowledge is reloaded if necessary.
   - If a media file, convert and index accordingly.
4. **Update Wiki:** Update or rebuild parts of the project's documentation, reflecting the latest file structure and information.
5. **Quarantine Projects:** Manage projects that consistently fail processing by placing them in quarantine, checking upon them with increasing delay intervals until they pass the check successfully.

Through this system, file changes are efficiently managed, ensuring that all relevant documentation is updated, AI models are informed, and errors are handled gracefully in a collaborative development environment.
## [[{"doc_id": "06e0f0cf-26f7-438d-9f66-c16bb6019b26", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-13 05:51:57.100878", "updated_at": "2025-08-13 05:51:57.100904", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
We must call update wiki after file has been reloaded