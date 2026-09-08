# CODX Junior API - Engine Module Documentation

## Overview

The `app.py` file serves as the core engine module for the CODX Junior API, implementing a FastAPI-based backend that manages project creation, session management, and real-time communication through Socket.IO. It handles HTTP routing, middleware processing, and background service orchestration.

## Core Architecture

### Application Initialization

The FastAPI application is configured with OpenAPI documentation and SSL support:
- **Base URL**: `/api/`
- **Documentation**: Available at `/api/docs` and `/api/redoc`
- **WebSocket**: Socket.IO integration at `/api/socket.io`

### Session Management

Sessions are managed through the `CODXJuniorSession` class, which is instantiated per request via the `get_codx_junior_session()` function. Each session includes:
- User authentication context
- Socket.IO communication channel
- Project-specific settings and state

## Middleware Pipeline

### Request Processing Flow

1. **Timeout Middleware**: Enforces a global request timeout of 280 seconds (HTTP 504 response on exceeded)
2. **Settings Middleware**: Loads project-specific CODX Junior settings based on `x-codx-path` header
3. **Process Time Middleware**: Tracks and logs request processing duration via `X-Process-Time` header
4. **Validation Handler**: Converts validation errors to standardized JSON responses (status 422)

### Exception Handling

- **RequestValidationError**: Returns custom status code 10422 with detailed error messages
- **General Exceptions**: Formatted traceback responses with HTTP 500 status

## API Endpoints

### Health & System

- `GET /api/health` - Health check
- `POST /api/restart` - Restart API service
- `POST /api/shutdown` - Graceful server shutdown

### Project Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | List all user-accessible projects and workspaces |
| `/api/projects` | POST | Create new project from path |
| `/api/projects` | DELETE | Delete current project |
| `/api/projects/metrics` | GET | Retrieve project metrics |
| `/api/projects/readme` | GET | Get project README (HTML response) |
| `/api/project/watch` | GET | Enable project file watching |
| `/api/project/unwatch` | GET | Disable project file watching |

### AI & Models

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects/ai/models` | GET | List available AI models for project |
| `/api/projects/ai/models/reload` | POST | Reload AI model configuration |

### Code Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/run/improve` | POST | Improve existing code with AI |
| `/api/run/improve/patch` | POST | Generate full file content from partial content |
| `/api/run/changes/summary` | GET | Build code changes summary |
| `/api/run/script` | POST | Execute custom script in project context |
| `/api/files/write` | POST | Write content to project file |
| `/api/files/reset` | GET | Reset file to original state |
| `/api/files/diff` | POST | Generate file diff with optional branch comparison |
| `/api/files/diff/comments` | POST | Generate commented diff |
| `/api/files/find` | GET | Search for files by pattern |
| `/api/code-server/file/open` | GET | Open file in code server |

### Settings & Profiles

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings` | GET | Read current project settings |
| `/api/settings` | PUT | Save project settings |
| `/api/profiles` | GET | List all profiles |
| `/api/profiles` | POST | Create new profile |
| `/api/profiles/{profile_name}` | GET | Read specific profile |
| `/api/profiles/{profile_name}` | DELETE | Delete profile |
| `/api/profiles/tools` | GET | List available tools for profiles |

### Application Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/apps` | GET | List project applications |
| `/api/apps/run` | GET | Execute application by name |

### System & Logging

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system/logs` | GET | List available logs (Docker containers and files) |
| `/api/system/logs/{log_name}` | GET | Tail specific log (supports size parameter) |
| `/api/screen` | GET | Get current screen resolution |
| `/api/screen` | POST | Set screen resolution |

### Testing

- `GET /api/test/sio` - Test Socket.IO connectivity

## Service Lifecycle

### Startup Events

- Initializes background services via `start_background_services()`
- Dynamically loads and registers all routers from the discovery module
- Sets up APP_STOP_EVENT for graceful shutdown coordination

### Shutdown Events

- Sets APP_STOP_EVENT flag
- Stops all background services via `stop_background_services()`

## Dynamic Router Loading

The `load_routers()` function discovers and registers routers from the `codx.junior.api` module. Each router is registered with a specific URL prefix. Failed registrations are logged as errors without halting startup.

## Authentication & Authorization

- User authentication handled by `get_authenticated_user()` dependency
- Workspace access control based on user roles:
  - **Admin**: Full access to all workspaces
  - **Regular users**: Access restricted by workspace `user_ids` configuration or workspace-level app role filters

## Static Files & Uploads

- Static files served from `CODX_JUNIOR_STATIC_FOLDER` at `/api/static`
- Upload directory created at `{CODX_JUNIOR_STATIC_FOLDER}/uploads`

## Logging Configuration

### Disabled Loggers

The following loggers are set to WARNING level to reduce verbosity:
- httpx, httpcore, OpenAI client, watchfiles, asyncio, project_watcher, selenium

### Request Logging

All HTTP requests are logged with processing time in milliseconds.

## Background Services

Background services are managed through:
- `start_background_services(APP_STOP_EVENT)` - Initializes on startup
- `stop_background_services()` - Cleanup on shutdown

The `CODX_JUNIOR_API_BACKGROUND` environment variable controls background service configuration.

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py