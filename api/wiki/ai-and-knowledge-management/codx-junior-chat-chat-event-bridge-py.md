# ChatEventBridge Documentation

## Overview

ChatEventBridge is a component that attaches AgentRunContext events to chat response messages and persists them with crash-safe guarantees. It bridges agent runtime events onto the chat response message, ensuring that every change is immediately persisted to disk.

## Core Concept

During an AI turn, the SmolAgent emits notifications about tool execution and run lifecycle. Rather than creating separate chat messages, ChatEventBridge associates these events directly with the assistant response message that was created before the AI call began:

- **tool_events**: A list of ToolEvent entries (one per tool call, updated in place as tools run, complete, or error)
- **lifecycle_events**: A list of LifeCycleEvent entries (one per agent run, updated in place)

## Crash-Safety Guarantee

The bridge provides crash-safe persistence through the following mechanism:

1. **Immediate Persistence**: On every event change, the response message is persisted immediately via ChatManager's granular merge-safe methods (`add_message` on first change, `update_message` afterwards)
2. **Real-time Streaming**: Events are streamed to clients via EventManager so the UI can render tool progress live
3. **Information Preservation**: If the process dies mid-run, every event received so far—including tool errors, run errors, and aggregated analytics—is already on disk

### Stream Content Persistence

Streaming callbacks can call `maybe_persist_stream()` on every flush. The bridge persists the response message at most once per `STREAM_PERSIST_MIN_INTERVAL_SECONDS` (default: 5.0 seconds), using a monotonic clock. A hard kill therefore loses at most that many seconds of streamed partial text while keeping disk I/O bounded.

### Auxiliary Message Persistence

Any auxiliary message produced mid-run (such as hidden reasoning messages) can be persisted immediately and idempotently via the `persist_message()` method. Persisted `doc_id`s are tracked bridge-side so the first call inserts and later calls update.

### Defensive Fallback

The idempotency guarantee assumes `ChatManager.update_message` matches by `doc_id`. If the granular methods are missing or fail, the bridge falls back to a coarse `save_chat` full write (after ensuring the message is on the in-memory chat) so information is never silently lost.

## Key Properties and Methods

### Initialization

```python
ChatEventBridge(chat, response_message, chat_manager, event_manager)
```

- **chat**: The in-memory chat being processed (shared reference)
- **response_message**: The assistant response message created before the AI call; events are attached to it
- **chat_manager**: Provides merge-safe persistence methods
- **event_manager**: Used to stream message events to clients

### Event Handling

**`on_event(event)`**: Entry point for handling AgentEvents. The bridge automatically routes events to appropriate handlers and never raises—any persistence or streaming failure is logged and swallowed to prevent killing the AI run.

### Tool Events

Tool events are tracked through:
- **TOOL_START**: Creates a new running ToolEvent
- **TOOL_END**: Updates the ToolEvent to done status with duration and result
- **TOOL_ERROR**: Updates the ToolEvent to error status with duration and error message

Tool responses are truncated to `TOOL_RESPONSE_MAX_CHARS` (default: 4000 characters) with an ellipsis marker if cut.

### Lifecycle Events

Lifecycle events include:
- **RUN_START**: Marks the beginning of an agent run
- **RUN_END**: Marks completion with duration and aggregated analytics
- **RUN_ERROR**: Captures errors that occurred during the run
- **RUN_CANCELLED**: Captures cancellation information

One LifeCycleEvent is kept per `run_id`. Recursive agent iterations that reuse the same bridge get one entry per run.

### Persistence Methods

**`publish()`**: Persists the response message (crash-safe) and streams it to clients. Idempotent by `doc_id`—the first call inserts via `add_message`, subsequent calls update via `update_message`.

**`persist_message(message)`**: Crash-safe persistence of an auxiliary message, used for messages like hidden reasoning that are produced mid-run.

**`maybe_persist_stream(min_interval_seconds)`**: Throttled persist of the response message for streamed content, called from streaming callbacks. Returns True if persist was performed, False if throttled.

## Status Values

- **STATUS_RUNNING**: Event is currently executing
- **STATUS_DONE**: Event completed successfully
- **STATUS_ERROR**: Event encountered an error

## Idempotency Enforcement

Persistence idempotency is enforced bridge-side by tracking which `doc_id`s have already been inserted in `_persisted_doc_ids`. This ensures:
- The response message is inserted only once via `add_message`
- Subsequent updates use `update_message`
- If granular methods are unavailable, the bridge falls back to full `save_chat` write
- No information is silently lost during persistence failures

## Error Handling

The bridge implements defensive error handling:
- All exception types are caught and logged without propagation
- Persistence failures trigger a fallback to full chat save
- Streaming failures are logged but do not affect persistence
- The bridge never raises exceptions to prevent killing the AI run