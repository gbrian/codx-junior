# CODX Junior API Engine Module

## Overview

The `app.py` file serves as the main engine module for the CODX Junior API backend. It implements a FastAPI-based REST API with Socket.IO support for real-time communication, managing project sessions, user authentication, and various operational features.

## Core Architecture

### Framework & Dependencies

The application is built on:
- **FastAPI**: Modern async web framework for building REST APIs
- **Socket.IO**: Real-time bidirectional communication
- **Flask**: Integration for JSON responses
- **Concurrent Processing**: ThreadPoolExecutor for background tasks

### Application Initialization

```
FastAPI configuration includes:
- API documentation endpoints (/api/docs, /api/redoc)
- OpenAPI schema generation (/api/openapi.json)
- SSL/TLS support with 'adhoc' context
```

### Router Registration

The application integrates multiple API routers under the `/api` prefix:
- Chat and messaging (chatGPT_router, chat_router)
- User management (users_router)
- Project operations (projects_router)
- File operations (files_router, file_finder_router)
- Git integration (git_router)
- Knowledge management (knowledge_router)
- Analytics and logging (analytics_router, logs_router)
- Database operations (db_router)
- Settings management (global_settings_router)
- Additional utilities (wiki_router, views_router)

## Session Management

### Session Creation

The `get_codx_junior_session()` function creates a CODX Junior session with:
- User authentication via `get_authenticated_user()`
- Session channel setup using Socket.IO
- Codx project path initialization

### Middleware Pipeline

**add_codx_junior_settings Middleware:**
Extracts and validates the `codx_path` from query parameters or headers (`x-codx-path`), establishing the session context for each request.

**timeout_middleware:**
Enforces a global request timeout threshold of 280 seconds, returning HTTP 504 errors when exceeded.

**add_process_time_header Middleware:**
Tracks and logs request processing time in response headers and application logs.

## Logging Configuration

### Log Management

The application disables verbose logging for specific modules:
- HTTP clients (httpx, httpcore)
- OpenAI client operations
- File watchers and async operations
- Selenium WebDriver

Debug logs are available for selective re-enabling via `enable_logs()` function.

## Key API Endpoints

### Health & System

- `GET /api/health`: Health check endpoint
- `GET /api/system/logs`: List available system and container logs
- `GET /api/system/logs/{log_name}`: Retrieve log file contents with filtering
- `POST /api/restart`: Restart API server
- `POST /api/shutdown`: Graceful server shutdown

### Project Management

- `GET /api/projects`: List all user-accessible projects and workspaces
- `POST /api/projects`: Create or load a project
- `DELETE /api/projects`: Delete current project
- `GET /api/project/watch`: Enable project watching
- `GET /api/project/unwatch`: Disable project watching
- `GET /api/projects/metrics`: Retrieve project metrics
- `GET /api/projects/readme`: Get project README content
- `GET /api/projects/ai/models`: List available AI models for project

### File Operations

- `GET /api/files/find`: Search for files within project
- `POST /api/files/write`: Write content to project files
- `GET /api/files/reset`: Reset file to original state
- `POST /api/files/diff`: Generate file differences
- `POST /api/files/diff/comments`: Add comments to file diffs
- `GET /api/code-server/file/open`: Open file in code editor

### Settings & Configuration

- `GET /api/settings`: Retrieve project settings
- `PUT /api/settings`: Update and persist project settings
- `GET /api/profiles`: List user profiles
- `POST /api/profiles`: Create new profile
- `GET /api/profiles/{profile_name}`: Retrieve specific profile
- `DELETE /api/profiles/{profile_name}`: Delete profile
- `GET /api/profiles/tools`: List available tools

### AI & Code Operations

- `POST /api/run/improve`: Improve existing code with AI assistance
- `POST /api/run/improve/patch`: Generate partial file content improvements
- `GET /api/run/changes/summary`: Build summary of code changes
- `POST /api/run/script`: Execute custom scripts within project context

### Media & Display

- `POST /api/images`: Upload and store images with MD5-based naming
- `POST /api/image-to-text`: Convert uploaded images to text using OCR/AI
- `GET /api/screen`: Retrieve current display resolution
- `POST /api/screen`: Set display resolution

### Application Management

- `GET /api/apps`: List available project applications
- `GET /api/apps/run`: Execute specified application

## Exception Handling

### Custom Exception Handlers

**RequestValidationError Handler:**
Returns HTTP 422 with formatted validation error messages.

**General Exception Handler:**
Returns HTTP 500 with full traceback information for debugging.

## Background Services

The application supports background service management:
- `startup_event()`: Initializes background services on server startup
- `shutdown_event()`: Gracefully stops background services on server shutdown
- `APP_STOP_EVENT`: Asyncio event for coordinating shutdown operations

## Data Models

The API integrates with domain models:
- `Chat`: Chat message data
- `Profile`: User profile configuration
- `Document`: File content representation
- `GlobalSettings`: Application-wide settings
- `Screen`: Display configuration
- `CodxUser`: Authenticated user information
- `AIModel`: AI model configuration

## Static Files & Resources

The application serves static content:
- **Static folder**: Mounted at `/api/static`
- **Image uploads**: Stored in `{CODX_JUNIOR_STATIC_FOLDER}/images`
- **Message images**: Stored with MD5 hash-based filenames in `{CODX_JUNIOR_STATIC_FOLDER}/images/message`

## User Access Control

The project implements role-based workspace access:
- **Admin users**: Full access to all workspaces
- **Empty user_ids**: All users have access
- **Specified user_ids**: Only listed users have access
- **Role-based app filtering**: Apps filtered by user role permissions

## Security

- User authentication via `get_authenticated_user()` dependency
- Session ID validation through `x-sid` headers
- Codx path validation and sanitization
- Static file serving with directory access control

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py