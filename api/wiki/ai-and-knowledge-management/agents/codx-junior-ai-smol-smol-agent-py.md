# SmolAgent Documentation

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed for streaming chat completions with multi-step tool support. It represents a streamlined alternative to traditional recursive agent implementations, using an iterative tool loop instead.

## Key Characteristics

SmolAgent differs from other implementations by:

- **Async-only interface**: Exposes a single async `chat()` method with no synchronous variant
- **Iterative tool loop**: Uses iteration instead of recursion for tool execution
- **Delegated responsibilities**: Delegates loop protection to `LoopGuard`, while logging, event emission, and cancellation management are handled by `AgentRunContext`
- **Full feature support**: Maintains streaming, callbacks, cancellation, and analytics capabilities

## Core Components

### Initialization

The SmolAgent is initialized with project settings and optional configuration:

```python
SmolAgent(
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None
)
```

**Parameters:**
- `settings`: Project settings providing LLM configuration
- `llm_model`: Optional model override
- `user`: Optional user information (used for API key and analytics)
- `system`: Optional extra system prompt content

## Public API

### chat() Method

The primary public method for running a streaming chat completion:

```python
async def chat(
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None
) -> List[Union[AIMessage, HumanMessage]]
```

**Arguments:**
- `messages`: Conversation history as LangChain message objects
- `config`: Optional configuration dictionary supporting:
  - `tools`: List of enabled tools
  - `chat_id`: Chat identifier
  - `cancellation_token`: Optional legacy cancellation token
  - `headers`: Request headers
  - `callbacks`: List of callback functions
  - `run_context`: An `AgentRunContext` instance
  - `event_listeners`: List of event callables

**Returns:**
Updated messages list with the assistant reply appended

**Raises:**
- `ToolLoopError`: When max tool rounds or stuck loop is detected
- `CancelledError`: When the request is cancelled by the caller

## Conversation Flow

The agent follows a structured flow:

1. Resolve `AgentRunContext`
2. Emit `RUN_START` event
3. Build OpenAI-formatted messages
4. Stream completion via guard_stream
5. Check finish_reason:
   - **tool_calls**: Execute guard check via `LoopGuard`
   - **stop/length**: Record usage and emit `RUN_END`
6. Execute tools with `TOOL_START`/`TOOL_END`/`TOOL_ERROR` events
7. Append assistant and tool messages
8. Loop until completion
9. Handle cancellation with `RUN_CANCELLED` event

## Tool Execution

### Tool Call Events

Tool events carry critical information for real-time UI updates:
- `tool_call_id`: Unique identifier for the tool invocation
- `args`: Parsed JSON request arguments
- `result`: Truncated result preview (limited by `TOOL_RESULT_PREVIEW_MAX_CHARS`)

### Error Handling

Tool errors are returned as strings to allow the model to react to failed invocations, rather than propagating exceptions to the caller. Events are emitted manually for both successful and failed executions.

## Runtime Context

The `AgentRunContext` provides unified management of:
- Lifecycle events (`RUN_START`, `RUN_END`, `RUN_ERROR`, `RUN_CANCELLED`)
- Streaming event guards with cancellation checkpoints
- Analytics aggregation
- Token counting and usage tracking

A run context can be provided via `config["run_context"]` to share cancellation tokens and event listeners, or a fresh context is created with optional event listeners.

## Streaming

The `_stream_completion()` method handles:

- OpenAI API streaming with chunk collection
- Content and tool call accumulation
- Usage information tracking (`LLM_USAGE` events)
- Callback batching and periodic flushing
- Cancellation checkpoints on every chunk
- Error handling with graceful stream closure

Streaming is wrapped by `AgentRunContext.guard_stream()` which emits throttled `LLM_CHUNK` events for live UI progress.

## Analytics

### Pre-flight Checks

Wallet checks are performed before execution via `_preflight_limit_check()` to ensure sufficient user budget.

### Usage Recording

Two types of analytics are recorded:

**Token Usage** (`_record_usage`):
- Input and output token counts
- Provider-reported usage when available
- Duration tracking
- Session and request identifiers
- Cost calculation based on configured rates

**Tool Usage** (`_record_tool_usage`):
- Tool name and execution status
- Execution duration
- Error details on failure
- Parent chat and request identifiers

Analytics are recorded non-fatally; errors do not interrupt the chat flow.

## Cancellation

Cancellation is handled through multiple paths:

- **Run context token**: Primary cancellation mechanism
- **Legacy cancellation token**: Bridged onto the run context token
- **Checkpoints**: Placed before tool execution via `run_context.checkpoint()`
- **Stream guarding**: Checked on every chunk during streaming

When cancelled, a `CancelledError` is raised with the message "Chat was cancelled by the caller."

## Request Building

### Configuration

The `_build_request_kwargs()` method constructs OpenAI API request parameters:
- Model selection
- Stream mode with usage inclusion
- Tool filtering based on selected_tools parameter
- Temperature configuration

### Tags and Headers

Analytics tags are built from:
- Request headers
- Temperature setting
- Project name
- Username (if available)

These tags are included in request headers as `x-litellm-tags` for provider-level analytics tracking.

## Tool Argument Parsing

The `_parse_tool_arguments()` static method handles flexible argument formats:
- Direct dict arguments
- JSON string arguments
- Empty dict fallback on parse failure

Parse failures are logged without interrupting execution.

## Callback Management

Callbacks are batched and flushed periodically via `_make_callback_sender()`:
- Accumulates chunk content in a buffer
- Flushes either on explicit request or after `CALLBACK_FLUSH_SECONDS`
- Silently handles callback errors to prevent interruption