# SmolAgent Documentation

## Overview

SmolAgent is a lightweight, async-only OpenAI chat agent designed for streaming conversations with iterative multi-step tool support. It implements an iterative tool loop architecture rather than recursion, delegating runtime concerns like logging, event emission, and cancellation to the `AgentRunContext`.

## Key Features

- **Async-only API**: Exposes a single `chat()` method with no synchronous variant
- **Iterative Tool Loop**: Uses iteration instead of recursion for better control and resource management
- **Tool Caching**: Caches tool results per conversation to prevent re-execution of identical calls
- **Streaming Support**: Maintains streaming, callbacks, and real-time analytics throughout execution
- **Dual-Response Tools**: Supports tools that return both user-facing content and LLM-only feedback via `ToolResponse`
- **Cancellation Support**: Integrated cancellation checkpoints throughout execution flow
- **Live Thinking Content**: Streams tool-generated thinking content to clients in real-time while persisting it in the final message

## Architecture

### Conversation Flow

The agent follows a structured execution pattern:

1. **Initialization**: Resolve runtime context and initialize tool cache
2. **Completion Loop**: Stream LLM completions until no tool calls remain
3. **Tool Processing**: Execute tools (both cached and new), handling dual-response tools specially
4. **Message Assembly**: Combine thinking content (tool outputs) with final answer
5. **Analytics**: Record usage, token counts, and cache statistics

### Message Structure

SmolAgent produces a single final `AIMessage` combining:
- **Thinking Content**: Accumulated tool outputs and LLM reasoning during tool rounds, streamed live to clients
- **Final Answer Content**: The final LLM response after all tool calls complete

This ensures all tool-generated content is persisted correctly in saved conversations.

## Core Components

### System Message Building

The complete system message is constructed from three sources (in order):

1. LLM settings system prompt
2. Fresh chat_global_instructions (loaded from GlobalSettings on every chat)
3. Extra system instructions passed to initialization

The `_build_system_message()` method reloads instructions on each chat to ensure freshness.

### Tool Execution

Tools are executed via `_execute_tool()` which:

- Emits `TOOL_START`, `TOOL_END`, or `TOOL_ERROR` events with execution metadata
- Catches all exceptions to ensure the model always receives non-empty tool messages
- Supports both synchronous and asynchronous tool implementations
- Caches results by tool name and parameter hash
- Handles dual-response tools (`ToolResponse` objects) specially

**Dual-Response Tools**: When a tool returns `ToolResponse`:
- `user_response`: Added to thinking content and streamed to client immediately
- `llm_response`: Sent only to the model for internal reasoning

**Traditional Tools**: Return a single value used only for LLM context.

### Tool Result Normalization

The `_normalise_tool_result()` function ensures the model never receives empty tool messages:

1. `None` → sentinel value `"(tool returned no output)"`
2. Empty string → sentinel value
3. Dict/List → JSON-serialized
4. Other types → string conversion fallback

### Tool Caching

The `ToolCache` tracks results by `(tool_name, parameters_hash)`:
- Cached results bypass `LoopGuard` checks entirely (don't count toward limits)
- Cached `ToolResponse` objects still surface `user_response` to thinking content
- Error results are cached to prevent re-execution of failing tools

### Loop Protection

`LoopGuard` enforces three safety limits on **uncached** tool calls:

1. **Max Iterations**: Total number of tool-calling rounds
2. **Max Tool Calls**: Total number of individual tool invocations
3. **Stuck Loop Detection**: Prevents repeated execution of identical tool calls

Cached results do not trigger these limits.

## Public API

### `async chat(messages, config) → List[AIMessage]`

Execute a streaming chat completion with multi-step tool support.

**Parameters:**
- `messages`: Conversation history as LangChain message objects
- `config`: Optional dictionary with:
  - `tools`: List of tool names to enable
  - `chat_id`: Chat identifier
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Request headers
  - `callbacks`: List of chunk callbacks
  - `run_context`: Optional custom `AgentRunContext`
  - `event_listeners`: List of event handler callables
  - `current_chat`: Chat object for context

**Returns:** Updated messages list with final assistant reply appended

**Raises:**
- `ToolLoopError`: If limits exceeded or stuck loop detected
- `CancelledError`: If cancelled by caller

## Streaming and Callbacks

### Chunk Accumulation Strategy

The `_make_callback_sender()` closure implements smart callback batching:

- **Buffer**: Accumulates chunks between flushes
- **Accumulated**: Maintains full response history
- **Flush Triggers**: Periodic time intervals or explicit flush flag
- **Full Content**: Callbacks always receive the complete accumulated response, not just deltas

This approach ensures crash-safe persistence: any partial save contains everything streamed up to that point.

### Event Emission

Events are emitted through `AgentRunContext`:
- `LLM_REQUEST`: Completion request initiated
- `LLM_CHUNK`: Individual chunks received (throttled)
- `LLM_USAGE`: Token usage from provider
- `TOOL_START`: Tool execution begins
- `TOOL_END`: Tool execution completed successfully
- `TOOL_ERROR`: Tool execution failed
- `RUN_START`/`RUN_END`/`RUN_ERROR`/`RUN_CANCELLED`: Lifecycle events

## Analytics and Observability

### Message Archival

Complete message exchanges are archived after successful streaming:
- LLM request/response pairs with token counts
- Full tool call execution details including parameters and results
- Timestamp and duration tracking

### Usage Recording

`_record_usage()` captures:
- Token counts (from provider or calculated via counter)
- Execution duration
- Cache statistics (hits, misses, hit rate)
- Session and request identifiers

`_record_tool_usage()` logs individual tool executions with success/error status.

### Sanitization for Serialization

The `_sanitize_for_serialization()` method handles non-serializable objects:
- Futures and coroutines → string representation
- Pydantic models → `model_dump()`
- Nested structures → recursive sanitization
- Fallback → string conversion

## Tool Scope System

Tools can have different scopes:

- **Global Scope**: Always included regardless of request configuration
- **Chat Scope**: Included only when explicitly selected

The `_build_request_kwargs()` method filters tools based on scope and selection.

## Hardcoded System Rules

The agent includes hardcoded rules for file handling:

- Always use code blocks with file names after language specifier
- Use valid file paths (absolute or relative)
- Follow original file formatting and indentation
- Avoid unnecessary changes unless explicitly requested
- Keep changes simple and easy to review

These rules are prepended to chat global instructions to ensure consistent code generation behavior.

## Error Handling

All exceptions during tool execution are caught and converted to error strings returned to the model. This prevents:
- Empty tool messages (which cause model to repeat the same call)
- Infinite loops terminating only via `LoopGuard`
- Unhandled exceptions propagating to callers

The model can then react to tool failures and adjust its approach.

## Runtime Context Integration

SmolAgent delegates to `AgentRunContext` for:
- **Logging**: Structured event logging
- **Event Fan-out**: Listener notification for real-time UI updates
- **Cancellation**: Cooperative cancellation checkpoints
- **Analytics**: Aggregated usage and performance metrics

Callers can provide their own context to share cancellation tokens and listeners across multiple agent instances.