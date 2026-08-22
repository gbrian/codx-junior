# SmolAgent Documentation

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed as a lightweight alternative to the standard OpenAI_AI implementation. It provides a single async `chat()` method with iterative tool loop support, leveraging an asynchronous-only architecture for improved performance and responsiveness.

## Key Characteristics

SmolAgent differentiates itself from `codx.junior.ai.openai_ai.OpenAI_AI` through:

- **Async-only interface**: Exposes a single async `chat()` method without synchronous variants
- **Iterative tool loop**: Uses iteration instead of recursion for tool execution
- **Delegated responsibilities**: Relies on `LoopGuard` for loop protection and `AgentRunContext` for logging, event emission, and cancellation
- **Stream compatibility**: Maintains support for streaming, callbacks, cancellation, and analytics

## Conversation Flow

The agent executes the following sequence:

1. **Initialization**: Resolves the `AgentRunContext` and emits `RUN_START` event
2. **Message Building**: Constructs OpenAI-format messages from conversation history
3. **Streaming**: Streams completions via `guard_stream` with cancellation checks
4. **Tool Handling**: If tool calls are present, executes loop guard checks before execution
5. **Tool Execution**: Runs tools sequentially with event emission (`TOOL_START`, `TOOL_END`, `TOOL_ERROR`)
6. **Loop Continuation**: Appends assistant and tool messages, repeating until no more tool calls
7. **Completion**: Records usage analytics and emits `RUN_END` or `RUN_CANCELLED`

## Initialization

### Constructor

```python
def __init__(
    self,
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None,
) -> None:
```

**Parameters:**

- `settings`: Project settings providing LLM configuration
- `llm_model`: Optional model override (defaults to settings value)
- `user`: Optional user object (provides API key and analytics context)
- `system`: Optional extra system prompt content

The constructor initializes the OpenAI client with credentials from either the user object or settings, and loads available tools from the tools module.

## Public API

### chat() Method

```python
async def chat(
    self,
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None,
) -> List[Union[AIMessage, HumanMessage]]:
```

Executes a streaming chat completion with iterative multi-step tool support.

**Parameters:**

- `messages`: Conversation history as LangChain message objects
- `config`: Optional configuration dictionary supporting keys:
  - `tools`: List of tool names to enable
  - `chat_id`: Chat identifier for analytics
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Additional request headers
  - `callbacks`: List of chunk callback functions
  - `run_context`: Custom `AgentRunContext` for event sharing
  - `event_listeners`: List of event listener callables

**Returns:**

Updated messages list with the assistant reply appended

**Raises:**

- `ToolLoopError`: If max tool rounds or a stuck loop is detected
- `CancelledError`: If the request is cancelled by the caller

## Chat Loop Execution

### _run_chat_loop() Method

Implements the core iterative streaming and tool execution loop. The method:

1. Extracts configuration parameters and builds OpenAI messages
2. Initializes a `LoopGuard` instance for loop protection
3. Continuously streams completions until no more tool calls are returned
4. Executes tools sequentially upon detection of tool calls (after guard check)
5. Records usage analytics upon completion

The loop terminates when the model returns a `finish_reason` of `stop` or `length` rather than `tool_calls`.

## Streaming

### _stream_completion() Method

Handles the streaming of a single completion with the following features:

- **Cancellation checking**: Bridges legacy `CancellationToken` onto the runtime context token
- **Event emission**: Emits `LLM_REQUEST` and `LLM_USAGE` events
- **Chunk accumulation**: Collects content and tool call information from streamed chunks
- **Callback sending**: Forwards cleaned text chunks to registered callbacks
- **Error handling**: Properly closes the stream on cancellation

**Returns:**

Tuple of `(content, tool_calls, usage_info)` representing the completion response

## Tool Execution

### _execute_tool() Method

Executes a single tool call with comprehensive error handling and event emission.

**Features:**

- Validates tool existence before execution
- Injects project settings when configured as a tool parameter
- Supports both synchronous and asynchronous tool implementations
- Emits `TOOL_START`, `TOOL_END`, or `TOOL_ERROR` events
- Records tool usage analytics regardless of success/failure
- Returns tool errors as strings, allowing the model to respond to failures

**Raises:**

- `AgentCancelled`: If cancellation is requested before execution

### _parse_tool_arguments() Method

Parses tool arguments that may arrive as either JSON strings or dictionaries. Returns an empty dict on parse failure.

## Request Building

### _build_request_kwargs() Method

Constructs the base OpenAI API request parameters including:

- Model identifier
- Stream configuration with usage info enabled
- Filtered tool definitions based on selected tools
- Temperature setting if non-zero

### _build_tags() Method

Generates a comma-separated analytics tag string from:

- Existing tags from request headers
- Temperature setting
- Project name
- Username (if user available)

## Callback Management

### _make_callback_sender() Method

Creates a closure that batches and flushes streamed chunks to registered callbacks. Chunks are buffered and flushed either when:

- An explicit flush is requested
- The buffer age exceeds `CALLBACK_FLUSH_SECONDS`

This mechanism reduces callback overhead for high-frequency chunk updates.

## Analytics

SmolAgent provides comprehensive analytics tracking through two mechanisms:

### _record_usage() Method

Records token usage statistics including:

- Input and output token counts (from provider or via local counting)
- Duration and session information
- Cost metrics based on configured token pricing
- Request and chat traceability identifiers

Errors in analytics recording are logged but do not propagate.

### _record_tool_usage() Method

Records individual tool execution events with:

- Execution duration
- Success/failure status
- Error messages on failure
- Chat and request traceability

### Wallet Check

The `_preflight_limit_check()` method validates user budget sufficiency before executing AI requests, preventing operations when funds are exhausted.

## Runtime Context

### _resolve_run_context() Method

Resolves the `AgentRunContext` for a chat by either:

- Reusing a provided context from the config (enabling shared cancellation tokens and event listeners)
- Creating a fresh context with optional event listeners

This allows callers to manage context lifecycle and share event subscriptions across multiple chat calls.

## Event Emission

SmolAgent emits the following event types through the run context:

- `LLM_REQUEST`: Before streaming begins
- `LLM_CHUNK`: During streaming (throttled via guard_stream)
- `LLM_USAGE`: When usage information is available
- `TOOL_START`: Before tool execution
- `TOOL_END`: After successful tool execution
- `TOOL_ERROR`: After failed tool execution
- `RUN_START`, `RUN_END`, `RUN_CANCELLED`, `RUN_ERROR`: Lifecycle events from AgentRunContext