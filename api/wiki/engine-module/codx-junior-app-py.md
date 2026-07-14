# CODXJunior API Documentation

## Overview

The CODXJunior API is a FastAPI-based backend service that provides session management, project creation, AI integration, file management, and various other backend functionalities. It uses Socket.IO for real-time communication and supports multiple routers for modular API organization.

---

## Application Setup

### FastAPI Instance

The application is initialized with the following configuration:

- **Title**: CODXJuniorAPI
- **Version**: 1.0
- **OpenAPI URL**: `/api/openapi.json`
- **Docs URL**: `/api/docs`
- **ReDoc URL**: `/api/redoc`
- **SSL**: `adhoc`

### Socket.IO Integration

Socket.IO is mounted at `/api/socket.io` using an ASGI adapter, enabling real-time bidirectional communication between clients and the server.

---

## Routers

The following modular routers are registered under the `/api` prefix:

| Router | Module |
|---|---|
| ChatGPT-like API | `codx.junior.api.chatGPTLikeApi` |
| Users | `codx.junior.api.users` |
| Wiki | `codx.junior.api.wiki` |
| Git | `codx.junior.api.git` |
| File Finder | `codx.junior.api.file_finder` |
| Database | `codx.junior.api.db_router` |
| Global Settings | `codx.junior.api.global_settings` |
| Project Search | `codx.junior.api.project_search` |
| Knowledge | `codx.junior.api.knowledge` |
| Chat | `codx.junior.api.chat` |
| Views | `codx.junior.api.views` |
| Analytics | `codx.junior.api.analytics` |
| Logs | `codx.junior.api.logs` |
| Projects | `codx.junior.api.projects` |

---

## Lifecycle Events

### Startup

On application startup:
- Background services are started via `start_background_services(APP_STOP_EVENT)`.
- An `asyncio.Event` (`APP_STOP_EVENT`) is used to coordinate shutdown.

### Shutdown

On application shutdown:
- `APP_STOP_EVENT` is set to signal background tasks.
- `stop_background_services()` is awaited to cleanly stop all background processes.

---

## Middleware

### Request Timing (`add_process_time_header`)

Records the processing time for each HTTP request and adds it as the `X-Process-Time` header in the response. Also logs each request URL and duration.

### Session Injection (`add_codx_junior_settings`)

For requests containing a `codx_path` query parameter or `x-codx-path` header, this middleware:
- Resolves the authenticated user via `get_authenticated_user`.
- Creates a `CODXJuniorSession` and attaches it to `request.state.codx_junior_session`.
- Updates the session's last access time.

### Request Timeout (`timeout_middleware`)

Enforces a global request timeout of **280 seconds**. If exceeded, returns an HTTP `504 Gateway Timeout` response with processing time details.

---

## Session Management

Sessions are created via the `get_codx_junior_session` helper function, which:
- Authenticates the user from the request.
- Extracts the Socket.IO session ID (`x-sid` header).
- Instantiates a `SessionChannel` for real-time communication.
- Returns a `CODXJuniorSession` bound to the project path, channel, and user.

---

## API Endpoints

### Health Check

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Returns `"ok"` to confirm the API is running. |

---

### Code Improvement

| Method | Path | Description |
|---|---|---|
| POST | `/api/run/improve` | Runs AI-powered code improvement on a chat session and saves the result. |
| POST | `/api/run/improve/patch` | Generates full file content from a partial content input. |
| GET | `/api/run/changes/summary` | Returns a summary of code changes. Accepts optional `refresh=true` query parameter. |

---

### Settings

| Method | Path | Description |
|---|---|---|
| GET | `/api/settings` | Retrieves the current project settings. |
| PUT | `/api/settings` | Saves updated project settings and refreshes the project list. |

---

### Profiles

| Method | Path | Description |
|---|---|---|
| GET | `/api/profiles` | Lists all profiles for the current project. |
| GET | `/api/profiles/tools` | Lists available profile tools. |
| POST | `/api/profiles` | Creates or saves a profile. |
| GET | `/api/profiles/{profile_name}` | Reads a specific profile by name. |
| DELETE | `/api/profiles/{profile_name}` | Deletes a specific profile by name. |

---

### Projects

| Method | Path | Description |
|---|---|---|
| GET | `/api/projects` | Returns all projects accessible by the authenticated user, along with applicable workspaces. Filters workspace apps by user role. |
| POST | `/api/projects` | Creates a new project at the specified `project_path`. |
| DELETE | `/api/projects` | Deletes the current project. |
| GET | `/api/projects/metrics` | Returns project metrics. |
| GET | `/api/projects/readme` | Returns the project README as HTML. |
| GET | `/api/projects/ai/models` | Lists AI models configured for the project. |
| POST | `/api/projects/ai/models/reload` | Reloads a specific AI model. |
| GET | `/api/project/watch` | Enables file watching for the project. |
| GET | `/api/project/unwatch` | Disables file watching for the project. |

#### Workspace Access Logic

Access to workspaces is determined as follows:
- **Admin users** always have access to all workspaces.
- If `workspace.user_ids` is empty, all users have access.
- Otherwise, only users whose username appears in `user_ids` have access.
- Non-admin users only see workspace apps matching their role.

---

### File Management

| Method | Path | Description |
|---|---|---|
| GET | `/api/files` | Lists files at a given `path`. |
| GET | `/api/files/read` | Reads the content of a file at `path`. |
| POST | `/api/files/write` | Writes content to a file. |
| GET | `/api/files/reset` | Resets a project file to its original state. |
| GET | `/api/files/find` | Searches for files matching a `search` query. |
| POST | `/api/files/diff` | Returns a diff for a file given its path, content, and optional branch parameters. |
| POST | `/api/files/diff/comments` | Returns diff comments for a file. |

---

### Image Upload

| Method | Path | Description |
|---|---|---|
| POST | `/api/images` | Uploads an image file. The file is stored using its MD5 hash as the filename under `{STATIC_FOLDER}/images/message/`. Returns the relative URL path `/images/message/{md5_hash}`. |
| POST | `/api/image-to-text` | Converts an uploaded image to text using the session's AI capabilities. |

---

### Applications

| Method | Path | Description |
|---|---|---|
| GET | `/api/apps` | Lists all project applications. |
| GET | `/api/apps/run` | Runs a specified project application by name (`app` query parameter). |

---

### Global Settings

| Method | Path | Description |
|---|---|---|
| GET | `/api/global/settings` | Returns global settings. **Admin only.** |
| POST | `/api/global/settings` | Saves global settings and reloads AI models. |

---

### System & Utilities

| Method | Path | Description |
|---|---|---|
| GET | `/api/test/sio` | Tests Socket.IO communication by sending a test event. |
| POST | `/api/run/script` | Executes a shell script in the project directory. |
| GET | `/api/system/logs` | Lists available log sources (Docker containers prefixed with `🐋:` and file logs prefixed with `🗃️:`). |
| GET | `/api/system/logs/{log_name}` | Returns the tail of a specific log. Supports Docker and file-based logs. Default size is 100 lines. Filters out entries related to the logs endpoint itself. |
| GET | `/api/code-server/file/open` | Opens a file in the code server. |
| GET | `/api/screen` | Returns the current screen resolution. |
| POST | `/api/screen` | Sets the screen resolution. |
| POST | `/api/restart` | Restarts the API process. |
| POST | `/api/shutdown` | Immediately shuts down the server using `os._exit(0)`. |

---

## Error Handling

| Handler | Description |
|---|---|
| `RequestValidationError` | Returns HTTP `422` with a sanitized error message. |
| Generic `Exception` | Returns HTTP `500` with a formatted traceback. |

---

## Static Files

Static files are served from the directory defined by the `CODX_JUNIOR_STATIC_FOLDER` environment variable, mounted at `/api/static`.

Uploaded images are stored in `{CODX_JUNIOR_STATIC_FOLDER}/images/`.

---

## Logging Configuration

The following loggers are set to `WARNING` level to reduce noise:

- `httpx`
- `httpcore.http11`
- `httpcore.connection`
- `openai._base_client`
- `watchfiles.main`
- `asyncio`
- `codx.junior.project_watcher`
- `selenium.webdriver.common.selenium_manager`

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py