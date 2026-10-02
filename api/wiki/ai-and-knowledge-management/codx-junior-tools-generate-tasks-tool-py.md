# Generate Tasks Tool

## Overview

The Generate Tasks Tool is a utility that allows Language Model (LM) models to request generation of sub-tasks from within conversations. It bridges the SmolAgent execution environment with the task generation pipeline, enabling AI-driven task decomposition.

## Purpose

This tool invokes the task generation pipeline, which analyzes the current chat context and automatically creates a list of actionable sub-tasks. Each generated sub-task is created as a child chat connected to the parent through a parent_id relationship.

## Function Signature

```python
generate_tasks_tool(
    instructions: str = "",
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse
```

## Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `instructions` | `str` | Optional additional instructions for task generation to guide the AI in creating sub-tasks | `""` |
| `settings` | `CODXJuniorSettings` | CODXJuniorSettings instance (passed by SmolAgent) | `None` |

## Return Value

The function returns a `ToolResponse` object containing:

- **user_response**: Human-readable summary of generated tasks
- **llm_response**: JSON task list for model context

## Exception Handling

The tool raises the following exceptions:

| Exception | Scenario |
|-----------|----------|
| `ValueError` | If settings parameter is not provided |
| `RuntimeError` | If no active session is available in settings or if task generation fails |

## How It Works

1. **Validation**: Verifies that settings are provided and contain an active session context
2. **Session Access**: Retrieves the active session from settings
3. **Chat Context**: Obtains the current chat from the session context
4. **Task Generation**: Invokes the async task generation pipeline via `session.chat_engine_actions.generate_tasks()`
5. **Response Building**: Constructs a response containing task summaries and status

## Event Loop Handling

The tool intelligently handles both asynchronous and synchronous contexts:

- If already in an async context, it creates a task that can be handled by the caller
- If in a synchronous context, it runs the generation using `asyncio.run()`

## Integration with SmolAgent

The tool is designed to be injected into SmolAgent's execution environment. The SmolAgent runtime must:

1. Provide the `settings` parameter with an active session reference stored in `settings._active_session`
2. Ensure the session has a current chat available in `session._current_chat`
3. Handle the asynchronous task creation appropriately based on the execution context

## Error Handling

The tool includes comprehensive error handling with logging at multiple levels:

- **ERROR**: When settings are not provided
- **INFO**: When task generation starts and completes successfully
- **DEBUG**: When tasks are created asynchronously
- **EXCEPTION**: When errors occur during task generation

All exceptions are logged with full context before being raised to the caller.