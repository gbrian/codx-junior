# CODX Junior API Engine Module

## Overview

The CODX Junior API serves as the core backend engine for the project management and AI-assisted code improvement system. Built with FastAPI and WebSocket support via Socket.IO, it handles session management, project creation, code analysis, and real-time communication between clients and the backend.

## Core Architecture

### Application Initialization

The FastAPI application is configured with:
- **Title**: codx-junior API
- **Version**: 1.0
- **Documentation**: OpenAPI endpoints at `/api/openapi.json`, `/api/docs`, and `/api/redoc`
- **WebSocket Support**: Socket.IO integration via ASGIApp at `/api/socket.io`

### Dynamic Router Loading

Routers are discovered and registered dynamically at startup through the `load_routers()` function, which discovers available routers and registers them with appropriate prefixes. Failed router registrations are logged without interrupting the startup process.

## Session Management

### Session Creation and Lifecycle

Sessions are created through `get_codx_junior_session()` which:
1. Authenticates the user from request headers
2. Extracts the session ID (`x-sid`) from headers
3. Creates a communication channel via `SessionChannel`
4. Initializes a `CODXJuniorSession` with the project path

Session data is attached to each request via the `add_codx_junior_settings` middleware, which:
- Validates the `codx_path` parameter from query strings or headers (`x-codx-path`)
- Updates the last access time for active sessions
- Handles initialization errors gracefully with logging

## Middleware Stack

### Request Processing Pipeline

1. **Timeout Middleware**: Enforces a global request timeout of 280 seconds, returning HTTP 504 on timeout
2. **Process Time Tracking**: Adds `X-Process-Time` header to responses with execution time in milliseconds
3. **Session Initialization**: Attaches CODX Junior session to request state
4. **Validation Error Handling**: Custom formatting of FastAPI validation errors

## API Endpoints

### Health and System

- `GET /api/health` - Health check endpoint returning "ok"
- `POST /api/restart` - Restart the API service
- `POST /api/shutdown` - Graceful shutdown of the server

### Project Management

- `GET /api/projects` - List all user-accessible projects and workspaces with role-based filtering
- `POST /api/projects` - Create a new project or load existing from `.codx/project.json`
- `DELETE /api/projects` - Delete current project
- `GET /api/project/watch` - Enable project watching
- `GET /api/project/unwatch` - Disable project watching
- `GET /api/projects/metrics` - Retrieve project metrics
- `GET /api/projects/readme` - Get project README as HTML

### Settings and Profiles

- `GET /api/settings` - Retrieve project settings
- `PUT /api/settings` - Save project settings
- `GET /api/profiles` - List all profiles
- `POST /api/profiles` - Create a new profile
- `GET /api/profiles/{profile_name}` - Read specific profile
- `DELETE /api/profiles/{profile_name}` - Delete profile
- `GET /api/profiles/tools` - List available tools for profiles

### Code Improvement and Analysis

- `POST /api/run/improve` - Improve existing code based on chat
- `POST /api/run/improve/patch` - Generate full file content with patches
- `GET /api/run/changes/summary` - Build summary of code changes
- `POST /api/files/write` - Write file content to project
- `GET /api/files/reset` - Reset file to original state
- `GET /api/files/find` - Search for files by pattern
- `POST /api/files/diff` - Generate diff between file versions
- `POST /api/files/diff/comments` - Add comments to file diffs

### AI and Models

- `GET /api/projects/ai/models` - List AI models available for project
- `POST /api/projects/ai/models/reload` - Reload AI model configuration

### Development Tools

- `GET /api/code-server/file/open` - Open file in code server
- `POST /api/run/script` - Execute arbitrary scripts in project directory
- `GET /api/apps` - List project applications
- `GET /api/apps/run` - Run specific application
- `GET /api/test/sio` - Test Socket.IO communication

### System and Logging

- `GET /api/system/logs` - List available logs (Docker containers and log files)
- `GET /api/system/logs/{log_name}` - Retrieve log entries with tail functionality
- `GET /api/screen` - Get current screen resolution
- `POST /api/screen` - Set screen resolution via xrandr

## Logging Configuration

### Disabled Loggers

The following loggers are set to WARNING level to reduce noise:
- `httpx`, `httpcore.http11`, `httpcore.connection`
- `openai._base_client`
- `watchfiles.main`
- `asyncio`
- `codx.junior.project_watcher`
- `selenium.webdriver.common.selenium_manager`

### Log Management

Logs are stored in the configured `LOGS_FOLDER` and can be accessed via the system logging endpoints. Docker container logs are also made accessible through the same interface.

## Background Services

### Startup and Shutdown

- **Startup Event**: Initializes background services with an `APP_STOP_EVENT` for graceful shutdown
- **Shutdown Event**: Sets the stop event and awaits background service cleanup

Background services are managed by `start_background_services()` and `stop_background_services()` functions.

## Error Handling

### Exception Handlers

1. **Validation Errors**: Custom handler returning HTTP 422 with formatted error details
2. **General Exceptions**: Traceback formatting and HTTP 500 response

### Fault Handling

The module enables Python's `faulthandler` for better debugging of segmentation faults and other system-level errors.

## Security and Access Control

### User Authentication

- User authentication is handled via `get_authenticated_user()` dependency injection
- Session validation occurs through request headers
- Role-based access control filters workspaces and applications based on user roles

### Workspace Access

The `/api/projects` endpoint implements role-based filtering:
- **Admins**: Full access to all workspaces
- **Other Users**: Access only if `workspace.user_ids` is empty or their username is in the list
- **Application-level Filtering**: Applications are further filtered by role requirements

## Static Files and Uploads

The API serves static files from `CODX_JUNIOR_STATIC_FOLDER` directory with an `uploads` subdirectory created at initialization. Files are accessible via `/api/static` path.

## Environment Configuration

- `CODX_JUNIOR_API_BACKGROUND` - Determines background service mode
- `CODX_JUNIOR_STATIC_FOLDER` - Root directory for static assets and uploads
- `CODX_JUNIOR_DISPLAY` - X11 display for screen resolution commands

## Dependencies and Integrations

- **FastAPI**: Web framework and request handling
- **Socket.IO**: Real-time bidirectional communication
- **SQLAlchemy Models**: Chat, Document, Profile, Screen, AIModel, and other data models
- **Project Management**: Discovery and creation via `project_discover` and `project_manager` modules
- **Session Engine**: `CODXJuniorSession` for project-specific operations
- **AI Integration**: `AIManager` for model operations

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py