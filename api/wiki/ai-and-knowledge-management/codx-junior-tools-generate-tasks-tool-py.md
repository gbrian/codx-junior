# Generate Tasks Tool

## Overview

The Generate Tasks Tool is a utility that enables LLM models to request generation of sub-tasks from within chat conversations. It bridges the SmolAgent execution environment with the task generation pipeline, allowing intelligent splitting of complex work into actionable, manageable sub-tasks.

## Purpose

This tool invokes the task generation pipeline, which analyzes the current chat context and creates a list of actionable sub-tasks. Each generated sub-task is created as a child chat connected to the parent through a parent_id relationship, maintaining organizational structure within the project.

## Function Signature

```python
def generate_tasks_tool(
    instructions: str = "",
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instructions` | `str` | No | Optional additional instructions to guide the AI in creating sub-tasks (e.g., 'Focus on frontend tasks' or 'Split by component'). |
| `settings` | `CODXJuniorSettings` | No | The CODXJuniorSettings instance, typically passed by the SmolAgent runtime. |

## Return Value

Returns a `ToolResponse` object containing:

- **user_content**: Human-readable summary of generated tasks
- **llm_feedback**: JSON task list for model context

## Behavior

The tool performs the following operations:

1. **Validation**: Verifies that settings are provided and an active session exists
2. **Context Retrieval**: Accesses the current chat from the session context via the chat manager
3. **Task Generation**: Invokes the asynchronous task generation pipeline
4. **Async Handling**: Manages both async and sync execution contexts appropriately
5. **Response Building**: Constructs a summary message with task information

## Exception Handling

The tool raises exceptions in the following scenarios:

| Exception | Condition |
|-----------|-----------|
| `ValueError` | Settings parameter is not provided |
| `RuntimeError` | No active session exists in settings or no current chat found in session context |
| `RuntimeError` | Task generation pipeline fails |

All exceptions are logged with appropriate context for debugging purposes.

## Usage Notes

- The SmolAgent runtime must inject the session context into settings via the `_active_session` attribute
- The session must provide access to a current chat via the `_current_chat` attribute
- The tool handles both asynchronous contexts (where an event loop is already running) and synchronous contexts (where a new event loop must be created)
- Task generation happens asynchronously, with tasks appearing on the project board after completion

## Related Components

- **CODXJuniorSettings**: Configuration object required for tool operation
- **CODXJuniorSession**: Session management for accessing chat and task contexts
- **ToolResponse**: Response model for tool outputs
- **SmolAgent**: The runtime environment that executes this tool