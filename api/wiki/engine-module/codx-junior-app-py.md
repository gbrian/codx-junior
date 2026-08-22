# Engine Module Documentation

## Overview

The Engine Module (`app.py`) serves as the core FastAPI application for the CODX Junior API. It manages project creation, session handling, backend logic, and coordinates communication between the frontend and various backend services through HTTP and WebSocket connections.

## Core Components

### Application Initialization

The FastAPI application is configured with the following settings:
- **Title**: codx-junior API
- **Version**: 1.0
- **API Documentation**: Available at `/api/docs` and `/api/redoc`
- **OpenAPI Schema**: Accessible at `/api/openapi.json`
- **WebSocket Support**: Integrated via Socket.IO at `/api/socket.io`

### Router Integration

The application includes multiple specialized routers for different functionalities:
- Chat and ChatGPT-like API
- User management
- Wiki functionality
- Git operations
- File finder and file operations
- Database operations
- Global settings management
- Project search and project management
- Knowledge management
- Views and analytics
- Logging system

## Session Management

### CODXJuniorSession

Sessions are created for each request via the `get_codx_junior_session()` function, which:
- Authenticates the user from the request
- Retrieves the session ID from request headers (`x-sid`)
- Creates a `SessionChannel` for WebSocket communication
- Initializes a `CODXJuniorSession` with the project path

The session is attached to the request state and tracks the last access time for monitoring purposes.

### Middleware Stack

The application implements several layers of middleware:

1. **Codx Junior Settings Middleware** (`add_codx_junior_settings`): Loads project settings from the `codx_path` parameter or header (`x-codx-path`)

2. **Timeout Middleware** (`timeout_middleware`): Enforces a global request timeout of 280 seconds, returning a 504 Gateway Timeout error if exceeded

3. **Process Time Middleware** (`add_process_time_header`): Records request processing time in the response header `X-Process-Time`

## API Endpoints

### Health & Diagnostic

- `GET /api/health` - Health check endpoint

### Settings Management

- `GET /api/settings` - Retrieve project settings
- `PUT /api/settings` - Save project settings

### Profile Management

- `GET /api/profiles` - List all profiles
- `GET /api/profiles/tools` - List available tools for profiles
- `POST /api/profiles` - Create a new profile
- `GET /api/profiles/{profile_name}` - Read specific profile
- `DELETE /api/profiles/{profile_name}` - Delete a profile

### Project Management

- `GET /api/projects` - Find all projects with workspace filtering based on user role and permissions
- `POST /api/projects` - Create a new project
- `DELETE /api/projects` - Delete the current project
- `GET /api/project/watch` - Enable project watching
- `GET /api/project/unwatch` - Disable project watching
- `GET /api/projects/metrics` - Retrieve project metrics
- `GET /api/projects/readme` - Fetch project README
- `GET /api/projects/ai/models` - List available AI models for the project
- `POST /api/projects/ai/models/reload` - Reload AI models

### Code Improvement

- `POST /api/run/improve` - Improve existing code
- `POST /api/run/improve/patch` - Generate full file content with patches
- `GET /api/run/changes/summary` - Build summary of code changes

### File Operations

- `GET /api/files/find` - Find files by search query
- `POST /api/files/write` - Write content to a file
- `GET /api/files/reset` - Reset a file to its original state
- `POST /api/files/diff` - Get file diff with optional branch comparison
- `POST /api/files/diff/comments` - Get diff with comments
- `GET /api/code-server/file/open` - Open a file in code server

### Image Management

- `POST /api/images` - Upload and store images using MD5 hash as filename
  - Returns relative URL path for accessing the uploaded image
  - Avoids duplicate writes by checking file existence

### Application Management

- `GET /api/apps` - List project applications
- `GET /api/apps/run` - Run a specific application
- `POST /api/run/script` - Execute custom scripts

### System Operations

- `GET /api/system/logs` - List available logs from Docker containers and log files
- `GET /api/system/logs/{log_name}` - Tail specific log files
- `GET /api/screen` - Get current screen resolution
- `POST /api/screen` - Set screen resolution

### Utilities

- `POST /api/image-to-text` - Convert uploaded image to text
- `GET /api/test/sio` - Test Socket.IO connection
- `POST /api/restart` - Restart the API
- `POST /api/shutdown` - Shut down the server

## Logging Configuration

The application disables verbose logging for specific modules to reduce noise:
- HTTP client libraries (`httpx`, `httpcore`)
- OpenAI base client
- File watching
- Async operations
- Selenium WebDriver

## Error Handling

### Exception Handlers

1. **Validation Error Handler**: Converts `RequestValidationError` to a custom JSON response with status code 10422
2. **Generic Exception Handler**: Returns full traceback for unhandled exceptions with 500 status code

## Background Services

The application supports background service management:
- `startup_event()` - Initializes background services on API startup
- `shutdown_event()` - Gracefully stops background services on API shutdown
- Uses `APP_STOP_EVENT` for coordinating shutdown

## Static File Serving

The application mounts a static file directory at `/api/static` for serving static assets. The path is configured via the `CODX_JUNIOR_STATIC_FOLDER` environment variable.

## Access Control

Project and workspace access is controlled through a role-based system:
- **Admin users**: Have access to all workspaces and projects
- **Workspace restrictions**: If `user_ids` is empty, all users have access; otherwise only specified users can access
- **Project filtering**: Workspaces are filtered to include only projects the user has access to
- **App-level roles**: Apps within workspaces can define role restrictions

## Environment Variables

- `CODX_JUNIOR_API_BACKGROUND` - Enables/disables background API mode
- `CODX_JUNIOR_STATIC_FOLDER` - Path to static files directory
- `CODX_JUNIOR_DISPLAY` - Display configuration for screen operations

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py