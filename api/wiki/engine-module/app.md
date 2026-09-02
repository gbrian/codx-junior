# CODX Junior API Engine Module

## Overview

The `app.py` file serves as the main entry point for the CODX Junior API backend engine. It initializes and configures a FastAPI application with Socket.IO support, implements session management, and provides comprehensive REST endpoints for project management, file operations, and AI-powered code enhancement.

## Core Architecture

### Application Initialization

The FastAPI application is configured with the following settings:
- **Title**: codx-junior API
- **Version**: 1.0
- **Documentation URLs**: 
  - OpenAPI: `/api/openapi.json`
  - Swagger UI: `/api/docs`
  - ReDoc: `/api/redoc`
- **Socket.IO Integration**: Mounted at `/api/socket.io` for real-time communication

### Router Configuration

The application includes multiple API routers organized by feature:

- **Chat & Communication**: ChatGPT-like API, Chat router
- **User Management**: Users router
- **Project Management**: Projects router, Project search
- **File Operations**: Files router, File finder
- **Knowledge Management**: Knowledge router, Wiki router
- **Development Tools**: Git router, Database router, Views router
- **System**: Global settings, Analytics, Logs
- **Static Assets**: Static files mounted at `/api/static`

## Session Management

### Session Creation

Sessions are created per-request through the `get_codx_junior_session()` function which:
- Extracts the authenticated user from request headers
- Retrieves the Socket.IO session ID (`x-sid`)
- Creates a `SessionChannel` for bidirectional communication
- Instantiates a `CODXJuniorSession` with the project path

### Middleware Pipeline

Three main middleware layers handle request processing:

1. **CODX Junior Settings Middleware** (`add_codx_junior_settings`)
   - Extracts project path from query parameters or headers (`x-codx-path`)
   - Initializes session context
   - Updates last access time for the session

2. **Timeout Middleware** (`timeout_middleware`)
   - Enforces a global request timeout of 280 seconds
   - Returns HTTP 504 (Gateway Timeout) on timeout exceeded
   - Logs all incoming HTTP requests

3. **Process Time Header Middleware** (`add_process_time_header`)
   - Calculates and appends request processing time to response headers
   - Logs request metrics

## Project Management

### Project Discovery and Creation

- **`/api/projects`** (GET): Lists all projects accessible to the authenticated user
  - Filters projects based on user role and workspace permissions
  - Handles admin access and role-based app filtering
  
- **`/api/projects`** (POST): Creates a new project or loads existing configuration
  - Attempts to load from existing `.codx/project.json`
  - Falls back to `create_project()` function if not found

- **`/api/projects`** (DELETE): Deletes the current project

### Project Monitoring

- **`/api/project/watch`** (GET): Enables project watching for changes
- **`/api/project/unwatch`** (GET): Disables project watching

### Project Information

- **`/api/projects/readme`** (GET): Retrieves project README
- **`/api/projects/metrics`** (GET): Returns project usage metrics
- **`/api/projects/ai/models`** (GET): Lists available AI models for the project
- **`/api/projects/ai/models/reload`** (POST): Reloads AI model configuration

## Code Enhancement & Improvement

### AI-Powered Code Operations

- **`/api/run/improve`** (POST): Improves existing code based on chat context
  - Processes the improvement request via `CODXJuniorSession`
  - Saves the updated chat history

- **`/api/run/improve/patch`** (POST): Generates full file content from partial content
  - Accepts partial file content and generates complete, improved versions

- **`/api/run/changes/summary`** (GET): Builds a summary of code changes
  - Supports force refresh via query parameter

## File Operations

### File Management

- **`/api/files/write`** (POST): Writes content to a project file
- **`/api/files/reset`** (GET): Reverts a file to its original state
- **`/api/files/find`** (GET): Searches for files matching a pattern
- **`/api/files/diff`** (POST): Generates diff for file changes with optional branch comparison
- **`/api/files/diff/comments`** (POST): Adds comments to file diffs
- **`/api/code-server/file/open`** (GET): Opens a file in the code editor

## User Profiles

Profiles allow users to define custom AI behavior and tool configurations:

- **`/api/profiles`** (GET): Lists all available profiles
- **`/api/profiles`** (POST): Creates a new profile
- **`/api/profiles/{profile_name}`** (GET): Retrieves a specific profile
- **`/api/profiles/{profile_name}`** (DELETE): Removes a profile
- **`/api/profiles/tools`** (GET): Lists all available AI tools

## Settings Management

### Project Settings

- **`/api/settings`** (GET): Retrieves current project settings
  - Validates project configuration
  - Returns `CODXJuniorSettings` object

- **`/api/settings`** (PUT): Updates and persists project settings
  - Accepts settings JSON
  - Triggers project discovery refresh

## Image & Media Operations

### Image Upload and Processing

- **`/api/images`** (POST): Uploads images with MD5-based deduplication
  - Stores images in `/images/message/` directory
  - Returns relative URL path for access
  - Skips duplicate writes using hash-based filenames

- **`/api/image-to-text`** (POST): Converts uploaded images to text using OCR/AI
  - Processes image bytes
  - Returns extracted text content

## System & Diagnostics

### Health & Status

- **`/api/health`** (GET): Basic health check endpoint
- **`/api/system/logs`** (GET): Lists available log files and Docker container logs
- **`/api/system/logs/{log_name}`** (GET): Retrieves log contents with configurable line limit
  - Filters self-referential log entries
  - Supports both file and Docker container log sources

### Display Configuration

- **`/api/screen`** (GET): Retrieves current screen resolution
- **`/api/screen`** (POST): Sets screen resolution using xrandr

### Application Control

- **`/api/restart`** (POST): Restarts the API service
- **`/api/shutdown`** (POST): Gracefully shuts down the server

## Apps & Scripts

### Application Execution

- **`/api/apps`** (GET): Lists available applications
- **`/api/apps/run`** (GET): Executes a specified application

### Script Execution

- **`/api/run/script`** (POST): Executes custom scripts within project context
  - Runs commands in project root directory
  - Returns standard output

## Error Handling & Logging

### Exception Handlers

- **Validation Errors**: Returns HTTP 422 with formatted validation messages
- **Generic Exceptions**: Returns HTTP 500 with traceback information

### Logging Configuration

- Disables verbose logging for external libraries (httpx, httpcore, openai, asyncio, etc.)
- Enables DEBUG level logging for CODX Junior components
- Provides structured logging with request tracking

## Background Services

### Lifecycle Management

- **Startup Event**: Initializes background services with app stop event
- **Shutdown Event**: Gracefully stops all background services and sets stop event

The background services are controlled via environment variable `CODX_JUNIOR_API_BACKGROUND` and handle long-running operations independently from request processing.

## Security

User authentication and authorization are handled through:
- `get_authenticated_user()` dependency for request authentication
- User role-based access control (admin vs. regular users)
- Workspace-level access restrictions via `user_ids` configuration
- Session tracking via Socket.IO session IDs

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py