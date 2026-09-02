# Custom Tools API

## Overview

The Custom Tools API provides admin-only endpoints for managing and executing custom project tools. Custom tools are project-level resources that enable project administrators to create, configure, and run specialized operations within the CODX Junior framework.

## Authorization

All endpoints require authentication and admin authorization (global admin role). The execute endpoint requires authentication but operates under standard authorization rules.

## Endpoints

### List Custom Tools

Lists all custom tools available in the project.

**Request:**
```
GET /api/projects/custom-tools
```

**Response:**
- **Status 200**: Returns `List[CustomTool]`
- **Status 401**: Unauthorized
- **Status 403**: Forbidden (not admin)

**Error Handling:** Returns 500 Internal Server Error if an unexpected error occurs during listing.

---

### Create Custom Tool

Creates a new custom tool in the project.

**Request:**
```
POST /api/projects/custom-tools
Content-Type: application/json

{
  "id": "tool_identifier",
  "name": "Tool Name",
  "description": "Tool description",
  ...
}
```

**Response:**
- **Status 201**: Returns created `CustomTool` with metadata
- **Status 400**: Bad request (validation error)
- **Status 401**: Unauthorized
- **Status 403**: Forbidden (not admin)
- **Status 409**: Conflict (tool already exists)
- **Status 500**: Internal server error

**Behavior:**
- Automatically sets `created_by` to the authenticated user's username
- Sets `created_at` and `updated_at` timestamps to current UTC time
- Validates that a tool with the same ID does not already exist

---

### Get Custom Tool

Retrieves a specific custom tool by ID.

**Request:**
```
GET /api/projects/custom-tools/{tool_id}
```

**Parameters:**
- `tool_id` (string, required): Tool identifier

**Response:**
- **Status 200**: Returns `CustomTool`
- **Status 401**: Unauthorized
- **Status 403**: Forbidden (not admin)
- **Status 404**: Tool not found
- **Status 500**: Internal server error

---

### Update Custom Tool

Updates an existing custom tool.

**Request:**
```
PUT /api/projects/custom-tools/{tool_id}
Content-Type: application/json

{
  "id": "tool_identifier",
  "name": "Updated Name",
  ...
}
```

**Parameters:**
- `tool_id` (string, required): Tool identifier to update

**Response:**
- **Status 200**: Returns updated `CustomTool`
- **Status 400**: Bad request (validation error)
- **Status 401**: Unauthorized
- **Status 403**: Forbidden (not admin)
- **Status 404**: Tool not found
- **Status 500**: Internal server error

**Behavior:**
- Verifies the tool exists before updating
- Automatically updates `updated_at` timestamp to current UTC time

---

### Delete Custom Tool

Deletes a custom tool from the project.

**Request:**
```
DELETE /api/projects/custom-tools/{tool_id}
```

**Parameters:**
- `tool_id` (string, required): Tool identifier to delete

**Response:**
- **Status 204**: No content (successfully deleted)
- **Status 401**: Unauthorized
- **Status 403**: Forbidden (not admin)
- **Status 404**: Tool not found
- **Status 500**: Internal server error

---

### Execute Custom Tool

Executes a custom tool with provided parameters.

**Request:**
```
POST /api/projects/custom-tools/{tool_id}/execute
Content-Type: application/json

{
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**Parameters:**
- `tool_id` (string, required): Tool identifier to execute

**Response:**
- **Status 200**: Returns `CustomToolExecutionResponse` (execution completed, may contain errors)
- **Status 400**: Bad request (validation error)
- **Status 401**: Unauthorized
- **Status 404**: Tool not found or not active
- **Status 500**: Internal server error

**Behavior:**
- Retrieves the tool by ID
- Verifies the tool is active before execution
- Uses `CustomToolExecutor` to run the tool with provided parameters
- Returns execution result regardless of success status (errors included in response)
- Does not require admin authorization; requires only authentication

## Data Models

### CustomTool

Represents a custom tool with metadata:
- `id`: Unique tool identifier
- `created_by`: Username of the user who created the tool
- `created_at`: UTC timestamp of creation
- `updated_at`: UTC timestamp of last update
- `active`: Boolean indicating if the tool is available for execution

### CustomToolExecutionRequest

Request object for tool execution:
- `parameters`: Dictionary of parameter key-value pairs

### CustomToolExecutionResponse

Response object for tool execution:
- `success`: Boolean indicating overall execution success
- Additional fields containing execution results and any errors

## Implementation Details

The API uses internal managers for tool operations:

- **CustomToolManager**: Handles CRUD operations for custom tools
- **CustomToolExecutor**: Handles execution of custom tools

Both are instantiated from the `CODXJuniorSession` available in the request state, which provides access to application settings.

## Logging

All operations are logged at appropriate levels:
- **INFO**: Successful operations (list, create, update, delete, execute)
- **DEBUG**: Tool retrieval operations
- **WARNING**: Validation errors
- **ERROR**: System errors and exceptions