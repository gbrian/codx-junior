# CODXJunior API - Application Module Documentation

## Overview

The application module (`app.py`) serves as the main entry point for the CODXJunior API backend. It is built using **FastAPI** and integrates **Socket.IO** for real-time communication. This module wires together all routers, middleware, session management, and background services into a unified application.

---

## Application Initialization

The FastAPI application is configured with the following metadata:

```python
app = FastAPI(
    title="CODXJuniorAPI",
    description="API for CODXJunior",
    version="1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    ssl_context='adhoc'
)
```

### API Documentation Endpoints
| URL | Description |
|-----|-------------|
| `/api/docs` | Swagger UI documentation |
| `/api/redoc` | ReDoc documentation |
| `/api/openapi.json` | OpenAPI schema |

---

## Socket.IO Integration

The application integrates Socket.IO via an ASGI wrapper mounted at `/api/socket.io`:

```python
sio_asgi_app = socketio.ASGIApp(sio, app, socketio_path="/api/socket.io")
app.mount("/api/socket.io", sio_asgi_app)
```

Session channels are established per request using a `sid` header (`x-sid`) for real-time event communication.

---

## Registered Routers

All feature-specific routers are included under the `/api` prefix:

| Router | Module |
|--------|--------|
| ChatGPT-like API | `codx.junior.api.chatGPTLikeApi` |
| Users | `codx.junior.api.users` |
| Wiki | `codx.junior.api.wiki` |
| GitHub | `codx.junior.api.github` |
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

## Middleware

### 1. Request Timeout Middleware
Enforces a global request timeout of **280 seconds** (`GLOBAL_REQUEST_TIMEOUT`). Returns an HTTP `504 Gateway Timeout` response if the limit is exceeded.

### 2. Process Time Header Middleware
Tracks and appends the processing duration to the response header as `X-Process-Time`. Logs each request URL and its duration in milliseconds.

### 3. CODXJunior Settings Middleware
Resolves the `codx_path` from query parameters or the `x-codx-path` header, creates a `CODXJuniorSession`, and attaches it to `request.state.codx_junior_session`. Also updates the session's last access time.

```python
request.state.codx_junior_session = get_codx_junior_session(request, codx_path)
request.state.codx_junior_session.update_last_access_time()
```

---

## Session Management

The `get_codx_junior_session` function creates a `CODXJuniorSession` using:
- `codx_path` – resolved from query params or headers
- `channel` – a `SessionChannel` built from the Socket.IO `sid`
- `user` – authenticated via `get_authenticated_user`

---

## Lifecycle Events

### Startup
- Starts background services via `start_background_services(APP_STOP_EVENT)`
- Logs application startup information

### Shutdown
- Sets the `APP_STOP_EVENT` to signal background service termination
- Calls `stop_background_services()`

---

## API Endpoints

### Health Check
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Returns `"ok"` to confirm the service is running |

### Code Improvement
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/run/improve` | Runs AI-based code improvement on a chat object |
| `POST` | `/api/run/improve/patch` | Generates full file content from partial content |
| `GET` | `/api/run/changes/summary` | Returns a summary of code changes |

### Settings
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/settings` | Retrieves project settings |
| `PUT` | `/api/settings` | Saves updated project settings |

### Profiles
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/profiles` | Lists all profiles |
| `GET` | `/api/profiles/tools` | Lists available profile tools |
| `POST` | `/api/profiles` | Creates a new profile |
| `GET` | `/api/profiles/{profile_name}` | Reads a specific profile |
| `DELETE` | `/api/profiles/{profile_name}` | Deletes a profile |

### Projects
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/projects` | Lists all user-accessible projects and workspaces |
| `POST` | `/api/projects` | Creates a new project |
| `DELETE` | `/api/projects` | Deletes the current project |
| `GET` | `/api/projects/metrics` | Returns project metrics |
| `GET` | `/api/projects/readme` | Returns the project README as HTML |
| `GET` | `/api/projects/ai/models` | Lists available AI models for the project |
| `POST` | `/api/projects/ai/models/reload` | Reloads a specific AI model |
| `GET` | `/api/project/watch` | Enables project file watching |
| `GET` | `/api/project/unwatch` | Disables project file watching |

### File Operations
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/files` | Lists files in a directory |
| `GET` | `/api/files/read` | Reads a file's content |
| `POST` | `/api/files/write` | Writes content to a file |
| `GET` | `/api/files/reset` | Resets a file to its previous state |
| `GET` | `/api/files/find` | Searches for files by name/pattern |
| `POST` | `/api/files/diff` | Returns a diff of file content |
| `POST` | `/api/files/diff/comments` | Returns diff with inline comments |

### Image Handling
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/images` | Uploads an image and stores it using an MD5 hash as the filename. Returns the relative URL path. |
| `POST` | `/api/image-to-text` | Converts an uploaded image to text |

The image upload endpoint deduplicates files by content — if the MD5 hash already exists on disk, the file is not written again.

### Applications
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/apps` | Lists project apps |
| `GET` | `/api/apps/run` | Runs a specified app |

### Global Settings
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/global/settings` | Returns global settings (admin only) |
| `POST` | `/api/global/settings` | Saves global settings and reloads AI models |

### System & Utilities
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/system/logs` | Lists available log sources (Docker containers and log files) |
| `GET` | `/api/system/logs/{log_name}` | Tails logs from a Docker container or file |
| `POST` | `/api/run/script` | Executes a shell script in the project directory |
| `GET` | `/api/test/sio` | Tests Socket.IO event emission |
| `GET` | `/api/code-server/file/open` | Opens a file in the code server |
| `GET` | `/api/screen` | Returns the current screen resolution |
| `POST` | `/api/screen` | Sets the screen resolution |
| `POST` | `/api/restart` | Restarts the API process |
| `POST` | `/api/shutdown` | Shuts down the server immediately |

---

## Access Control

### Workspace and Project Access
The `/api/projects` endpoint applies role-based access control:
- **Admin** users have access to all workspaces.
- **Non-admin** users only see workspaces where either `user_ids` is empty or their username is listed.
- App-level access within workspaces is filtered by the user's role if `roles` is defined on the app.

---

## Static Files

Static files are served from the directory specified by `CODX_JUNIOR_STATIC_FOLDER`:

```python
app.mount("/api/static", StaticFiles(directory=CODX_JUNIOR_STATIC_FOLDER, html=True), name="static")
```

Uploaded images are stored in `{CODX_JUNIOR_STATIC_FOLDER}/images`.

---

## Logging Configuration

The following loggers are suppressed to `WARNING` level to reduce noise:

- `httpx`
- `httpcore.http11`
- `httpcore.connection`
- `openai._base_client`
- `watchfiles.main`
- `asyncio`
- `codx.junior.project_watcher`
- `selenium.webdriver.common.selenium_manager`

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CODX_JUNIOR_API_BACKGROUND` | Indicates if the API runs as a background process |
| `CODX_JUNIOR_STATIC_FOLDER` | Path to the static file serving directory |
| `CODX_JUNIOR_DISPLAY` | Display identifier used for screen resolution commands |

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py