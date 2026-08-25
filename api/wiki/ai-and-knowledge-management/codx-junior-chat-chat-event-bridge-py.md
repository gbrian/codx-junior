# ChatEventBridge Documentation

## Overview

ChatEventBridge is a component that translates agent runtime events into chat messages. During an AI turn, the SmolAgent emits various notifications through the `AgentEvent` system, which the bridge converts into `role="tool"` chat messages that are stored, persisted, and streamed to clients in real time.

## Purpose and Architecture

The bridge serves three primary functions:

1. **Converting events to messages** — Transforms `AgentEvent` notifications into `Message` objects with typed properties
2. **Persisting changes** — Stores messages immediately via `ChatManager` using merge-safe methods for crash safety
3. **Real-time streaming** — Delivers messages to clients via the `EventManager`

Event details are stored in typed message properties:
- `message.tool_event` → `ToolEvent` for tool execution details
- `message.lifecycle_event` → `LifeCycleEvent` for run lifecycle information

Supplementary information not covered by typed models (such as `run_id` and aggregated `analytics`) is stored in `meta_data`.

## Message Update Strategy

Tool messages are updated **in place** with one message per tool call, transitioning from `running` to `done` or `error` status. All run-lifecycle events share a single message per run, also updated in place, to avoid flooding the chat timeline.

## Event Handling

### Tool Events

Tool events follow a lifecycle pattern:

**TOOL_START** — Creates a new message with status `running`:
- Generates a new unique message ID
- Sets content to indicate tool is executing
- Sets `done=False`

**TOOL_END/TOOL_ERROR** — Updates the same message with final state:
- Updates `tool_event.status` to either `done` or `error`
- Adds duration information via `duration_ms`
- For errors: stores error text and updates content with failure message
- For success: stores truncated response (max 4000 characters) and updates content with result
- Sets `done=True`

Defensive handling is implemented for edge cases where TOOL_END arrives without a matching TOOL_START.

### Lifecycle Events

Lifecycle events tracked include:

- `RUN_START` — Run initialization
- `RUN_END` — Successful completion
- `RUN_ERROR` — Run encountered an error
- `RUN_CANCELLED` — Run was cancelled
- `LLM_REQUEST` — Language model invocation
- `LLM_USAGE` — Token consumption statistics
- `WALLET_CHECK` — Balance verification

Each lifecycle event generates a user-friendly summary line that is appended to the single lifecycle message's content.

## Key Components

### Constructor Parameters

```
chat: Chat
    The in-memory chat being processed (mutated in place)

chat_manager: ChatManager
    Provides add_message/update_message for persistence

event_manager: EventManager
    Used to stream message events to clients
```

### Status Constants

- `STATUS_RUNNING = "running"` — Event/message in progress
- `STATUS_DONE = "done"` — Successfully completed
- `STATUS_ERROR = "error"` — Encountered an error

### Configuration

`TOOL_RESPONSE_MAX_CHARS = 4000` — Maximum characters of tool response stored in messages. Responses exceeding this limit are truncated with an ellipsis marker.

## Event Processing Flow

The main entry point is the `on_event()` method, which routes events to specialized handlers:

1. **TOOL_START** → `_on_tool_start()` — Creates new message
2. **TOOL_END** → `_on_tool_finished()` — Updates message with success
3. **TOOL_ERROR** → `_on_tool_finished()` — Updates message with error
4. **Lifecycle events** → `_on_lifecycle()` — Appends to lifecycle message

All exceptions during event handling are caught and logged without interrupting the AI run, ensuring robustness.

## Persistence and Streaming

The `_publish()` method handles both persistence and streaming:

- **For new messages** — Calls `chat_manager.add_message()`
- **For existing messages** — Calls `chat_manager.update_message()`
- **For all messages** — Calls `event_manager.message_event()`

Both operations are wrapped in independent exception handling to prevent failures in one channel from affecting the other.

## Text Truncation

The `_truncate()` utility function limits text to a specified character count (default 4000 characters). When truncation occurs, it appends `"\n… (truncated)"` to indicate the text was shortened. Empty text returns an empty string.