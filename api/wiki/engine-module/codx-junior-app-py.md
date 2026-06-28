# CODXJuniorAPI Documentation

The CODXJuniorAPI is a backend engine designed for project management, session handling, and AI-driven development assistance.

## Core Architecture
The API is built using **FastAPI** and integrated with **Socket.IO** for real-time communication via the `sio` manager. It utilizes an asynchronous event system (`APP_STOP_EVENT`) to manage lifecycle events during startup and shutdown.

### Middleware and Lifecycle
- **Startup/Shutdown**: The engine initializes background services on startup and ensures clean termination of these services and the event loop upon shutdown.
- **Request Processing**: 
    - Middleware adds `X-Process-Time` to responses for performance tracking.
    - A custom timeout middleware (`timeout_middleware`) enforces a `GLOBAL_REQUEST_TIMEOUT` of 280 seconds, returning an `HTTP 504 Gateway Timeout` if exceeded.
    - Requests are authenticated and scoped to specific sessions using the `codx_path` header or query parameter, which establishes a `CODXJuniorSession`.

## Project and Session Management
The API manages projects through discovery and session-based interactions.
- **Session Handling**: The `get_codx_junior_session` function resolves the authenticated user and creates a `SessionChannel` using a provided `sid` (session ID).
- **Project Discovery**: Use `api_find_all_projects` to list projects and workspaces. Access control is determined by user roles (e.g., "admin" has full access) and workspace-specific user ID filtering.
- **Project Operations**:
    - Creation/Deletion: Endpoints are available for managing the project lifecycle, including `api_project_create` and `api_project_delete`.
    - Watching/Unwatching: Real-time file system monitoring is controlled via `/api/project/watch` and `/api/project/unwatch`.

## API Endpoints

### File Operations
- **Navigation**: Read directories (`/api/files`) and read individual file content (`/api/files/read`).
- **Editing**: Supports file writing (`/api/files/write`), resetting files to original states, and calculating code diffs/comments (`/api/files/diff`, `/api/files/diff/comments`).
- **Search**: `api_find_files` provides search functionality within the project path.

### AI and Code Improvement
- **Improvement**: `api_run_improve` executes AI-based code improvement on chat contexts.
- **Patching**: `api_run_improve_patch` facilitates the generation of full file content based on partial inputs.
- **Metrics/Models**: Access project metrics, branch commits, and manage AI model configuration via the `AIManager`.

### System and Infrastructure
- **Logs**: The `/api/system/logs` endpoints provide access to both Docker container logs (prefixed with `🐋`) and local application log files (prefixed with `🗃️`).
- **Screen**: Manage display resolution settings via `xrandr` using the `/api/screen` endpoint.
- **Images**: Uploads are processed via `api_image_upload`, which generates an MD5 hash of the file content to ensure unique storage and efficient serving under the `/api/static` route.
- **Maintenance**: Administrative control is provided via `/api/restart` (killing PID 7) and `/api/shutdown` (terminating the process).

## Configuration
- **Global Settings**: Administrative settings are read/written via `/api/global/settings`.
- **Static Assets**: The API mounts a static directory defined by the `CODX_JUNIOR_STATIC_FOLDER` environment variable at `/api/static`.

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py