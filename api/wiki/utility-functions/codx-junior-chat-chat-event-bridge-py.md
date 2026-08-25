# ChatEventBridge Documentation

## Overview

ChatEventBridge is a utility component that translates `AgentRunContext` events into chat messages. It serves as the bridge between the SmolAgent runtime and the chat persistence/streaming system, converting agent events into user-visible messages that are stored and transmitted to clients.

## Purpose

During an AI turn, the SmolAgent emits various `AgentEvent` notifications including tool execution (start/end/error), LLM requests, usage statistics, and run lifecycle events. The ChatEventBridge converts these events into `role="tool"` chat messages that are:

- Appended to the in-memory `Chat` object (shared reference)
- Persisted immediately via `ChatManager` granular merge-safe methods (crash-safe)
- Streamed to clients in real time via the EventManager

## Key Features

### In-Place Message Updates

Tool messages are updated **in place** during their lifecycle (running → done/error). This means one message per tool call is maintained throughout its execution, rather than creating new messages for each state change.

All run-lifecycle events share a single message per run, also updated in place, to prevent flooding the chat timeline with repetitive events.

### Message Types

The bridge handles two categories of messages:

1. **Tool Event Messages** (`META_TYPE_TOOL_EVENT`): Created when tools start execution and updated with results or errors
2. **Lifecycle Event Messages** (`META_TYPE_LIFECYCLE_EVENT`): A single message per run collecting all lifecycle events

### Status Values

Messages maintain status metadata with the following values:
- `STATUS_RUNNING`: Event is in progress
- `STATUS_DONE`: Event completed successfully
- `STATUS_ERROR`: Event encountered an error

## Configuration Constants

- `TOOL_RESPONSE_MAX_CHARS`: Maximum characters of tool response stored in message metadata (default: 4000)
- `LIFECYCLE_EVENT_TYPES`: Set of lifecycle events surfaced to users (excludes `LLM_CHUNK`)

## Core Components

### Initialization

The `ChatEventBridge` constructor accepts three parameters:

- `chat`: The in-memory chat being processed (mutated in place)
- `chat_manager`: ChatManager providing `add_message`/`update_message` methods
- `event_manager`: EventManager used to stream message events

The bridge maintains internal state:
- `_tool_messages`: Dictionary mapping tool identifiers to their corresponding messages
- `_lifecycle_message`: Single lifecycle message per run
- `_lifecycle_lines`: List of formatted lifecycle event descriptions

### Event Handling

The `on_event()` method serves as the entry point for handling `AgentEvent` objects. It routes events to appropriate handlers:

- `AgentEventType.TOOL_START`: Routes to `_on_tool_start()`
- `AgentEventType.TOOL_END`: Routes to `_on_tool_finished()`
- `AgentEventType.TOOL_ERROR`: Routes to `_on_tool_finished()` with error flag
- Other lifecycle events: Route to `_on_lifecycle()`

**Error Safety**: The bridge catches and logs all exceptions without re-raising them, ensuring no event handling failure can interrupt the AI run.

## Tool Event Processing

### Tool Start Event

When a tool execution begins, `_on_tool_start()` creates a new message with:
- Content: Visual indicator with tool name
- Status: `STATUS_RUNNING`
- Metadata: Tool name, tool_call_id, request arguments, run_id

The message is immediately published to persist and stream.

### Tool Finish Event

When a tool completes (successfully or with error), `_on_tool_finished()` updates the same message in place with:
- **Success case**: Final response (truncated to max chars) and execution duration
- **Error case**: Error description and duration

The message status is updated to `STATUS_DONE` or `STATUS_ERROR` accordingly.

## Lifecycle Event Processing

The `_on_lifecycle()` method accumulates lifecycle events into a single per-run message. Each event is converted to a user-friendly line via `_lifecycle_line()`:

- `RUN_START`: Run initiation marker
- `LLM_REQUEST`: Model call information with message count
- `LLM_USAGE`: Token usage statistics
- `WALLET_CHECK`: Wallet balance information
- `RUN_END`: Successful completion marker
- `RUN_CANCELLED`: Cancellation reason
- `RUN_ERROR`: Error details (truncated to 500 chars)

Multiple lines are joined together in the single lifecycle message content, which is updated as new events arrive.

## Text Processing

The `_truncate()` utility function truncates text to a maximum character limit and appends an ellipsis marker (`\n… (truncated)`) when cutting occurs. This ensures tool responses and error messages don't overwhelm the message storage.

## Persistence and Streaming

The `_publish()` method handles both persistence and streaming:

- **Persistence**: Calls `chat_manager.add_message()` for new messages or `update_message()` for updates
- **Streaming**: Calls `event_manager.message_event()` to transmit to clients

Each operation is wrapped in error handling that logs failures without raising exceptions, maintaining run continuity even if persistence or streaming fails.