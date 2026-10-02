# Shared API Utilities

## Overview

This module provides shared utilities and dependencies used across multiple routers in the CODX Junior API. It handles authentication, session management, and dynamic router discovery.

## Key Functions

### `require_admin()`

A FastAPI dependency that enforces admin-only access control.

**Parameters:**
- `user`: Authenticated user (injected via dependency)

**Returns:**
- `CodxUser`: The authenticated user if authorized

**Behavior:**
- Raises `HTTPException` with status code 403 if the user is not authenticated or does not have admin role
- Logs access denial attempts with the username

**Usage:**
```python
@router.delete("/sensitive-endpoint")
def delete_resource(user: CodxUser = Depends(require_admin)):
    # Only admins can reach this endpoint
    pass
```

### `get_current_session()`

Extracts the active `CODXJuniorSession` from the incoming HTTP request.

**Parameters:**
- `request`: The incoming HTTP request object

**Returns:**
- `CODXJuniorSession`: The session object attached to `request.state`

**Note:** This function assumes middleware has already injected the session into the request state before the endpoint is reached.

### `discover_routers()`

Dynamically discovers and loads all router modules in the API package.

**Returns:**
- `List[dict]`: List of router configurations, each containing:
  - `router`: The FastAPI router object
  - `prefix`: The API prefix (`/api`)
  - `module`: The module name

**Behavior:**
- Scans the API package directory for Python files
- Excludes `__init__.py` and test files
- Loads modules that export a `router` attribute
- Logs discovery results and any import errors
- Returns routers sorted by module name

**Error Handling:**
- Import errors and runtime exceptions are caught and logged; they do not halt the discovery process

## Dependencies

- FastAPI for HTTP exception handling and dependency injection
- `CodxUser` model for user representation
- `CODXJuniorSession` for session management
- Standard library modules: `logging`, `os`, `importlib`, `pathlib`

## Dependencies
**Imports from:** codx/junior/model/model.py, codx/junior/security/user_management.py, codx/junior/engine.py
**Imported by:** codx/junior/api/analytics.py, codx/junior/api/knowledge.py, codx/junior/api/logs.py, codx/junior/api/views.py, codx/junior/api/workspaces.py