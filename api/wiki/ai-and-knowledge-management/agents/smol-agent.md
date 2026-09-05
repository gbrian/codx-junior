# SmolAgent Documentation

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed for efficient multi-step tool execution. It provides a streaming chat completion interface with integrated tool support, caching, and comprehensive analytics.

### Key Characteristics

- **Async-only**: Exposes a single async `chat()` method with no synchronous variant
- **Iterative tool loop**: Uses iterative execution instead of recursion for better control
- **Delegated responsibilities**: Offloads loop protection, logging, event emission, and cancellation to `AgentRunContext`
- **Streaming support**: Maintains streaming, callbacks, cancellation, and analytics capabilities
- **Tool result caching**: Caches tool results per conversation to prevent re-execution

## Architecture

### Conversation Flow

SmolAgent follows a structured conversation flow:

1. **Initialization**: Chat request is resolved with `AgentRunContext`
2. **Message Building**: OpenAI-format messages are constructed from conversation history
3. **Tool Cache Setup**: Tool result cache is initialized for the conversation
4. **Streaming Loop**: Completion is streamed via `guard_stream`
5. **Tool Execution**: When tool calls are detected:
   - Cached results bypass execution and loop guards
   - New tool calls are checked against loop limits
   - Tools are executed sequentially with cancellation checkpoints
6. **Response Accumulation**: Content is accumulated in thinking and final answer buffers
7. **Message Generation**: Response is split into thinking and final answer messages

### Message Structure

When tools are used, SmolAgent produces two separate messages:

- **Thinking Message**: Contains tool-calling rounds' LLM text and intermediate processing. Only generated if tools were used.
- **Final Answer Message**: Contains only the final LLM response without tool-related preprocessing. Always generated.

This separation keeps user-facing responses clean while preserving full execution traces.

## Core Methods

### `__init__`

Initializes a SmolAgent instance with configuration and LLM settings.

**Parameters:**
- `settings` (CODXJuniorSettings): Project settings providing LLM configuration
- `llm_model` (Optional[str]): Optional model override
- `user` (Optional[CodxUser]): User context for API key and analytics
- `system` (Optional[str]): Extra system prompt content appended after global instructions
- `session` (Optional[Any]): Session context for tools requiring access to chat state

**System Message Building:**
The system message is dynamically constructed from three sources:
1. LLM settings system prompt
2. Chat global instructions (loaded fresh on each chat)
3. Extra system instructions from initialization

### `chat`

Main public API for running a streaming chat completion with multi-step tool support.

**Parameters:**
- `messages` (List[Union[AIMessage, HumanMessage]]): Conversation history
- `config` (Optional[Dict[str, Any]]): Configuration dict with optional keys:
  - `tools`: List of tool names to enable
  - `chat_id`: Chat identifier
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Request headers
  - `callbacks`: Chat message callbacks
  - `run_context`: AgentRunContext instance
  - `event_listeners`: List of event callables
  - `current_chat`: Chat object for context

**Returns:**
Updated messages list with assistant replies appended. If tools were used, includes both thinking and final answer messages. If no tools were used, only the final answer message.

**Raises:**
- `ToolLoopError`: If max tool rounds, max tool calls, or stuck loop is detected
- `CancelledError`: If the request is cancelled

## Tool Execution

### Tool Call Processing

Tools are processed in two phases:

1. **Cached Calls**: Previously executed tool calls with identical arguments
   - Bypass `LoopGuard` checks
   - Don't count towards execution limits
   - Emit `TOOL_END` events with `cached=True` flag

2. **Uncached Calls**: New tool invocations
   - Checked against loop guard limits
   - Fully executed with error handling
   - Results cached for future use

### Tool Result Normalization

The `_normalise_tool_result` method ensures the model always receives non-empty tool messages. Conversion rules (in priority order):

1. `None` → sentinel `_TOOL_NO_OUTPUT`
2. `str` → returned as-is (empty string → sentinel)
3. `dict`/`list` → JSON-serialized for readability
4. Anything else → `str()` fallback

### Tool Response Types

Tools can return:

- **Traditional single-response** (`str` or any serializable type): Used for LLM context only
- **Dual-response** (`ToolResponse` object):
  - `user_response`: Added to thinking message for user visibility
  - `llm_response`: Sent to model only, not included in user-facing response

## Streaming and Callbacks

### Callback Mechanism

The callback sender uses an accumulation strategy:

- Chunks are buffered as they arrive from the stream
- The **full accumulated response** (not just deltas) is sent to callbacks
- Flushing occurs on explicit flush flag or after `CALLBACK_FLUSH_SECONDS` interval
- This ensures crash-safe persistence where any partial save contains complete streamed content

## Analytics and Monitoring

### Event Emission

SmolAgent emits detailed events through `AgentRunContext`:

- `RUN_START` / `RUN_END` / `RUN_ERROR` / `RUN_CANCELLED`: Run lifecycle events
- `LLM_REQUEST` / `LLM_CHUNK` / `LLM_USAGE`: LLM streaming events
- `TOOL_START` / `TOOL_END` / `TOOL_ERROR`: Tool execution events

Tool events include:
- `tool_call_id`: Identifier for the tool call
- `args`: Parsed JSON request arguments
- `result`: Truncated preview for user-facing display
- `cached`: Whether result was from cache

### Usage Recording

Token usage is recorded including:
- Input and output tokens (from provider or calculated via `count_tokens`)
- Tool cache statistics (hits, misses, hit rate)
- Duration and cost metrics
- Traceability links to chat and request IDs

## Loop Protection

The `LoopGuard` class prevents runaway tool execution:

- Enforces `max_iterations`: Total tool-calling rounds
- Enforces `max_tool_calls`: Total tool invocations across all rounds
- Detects stuck loops where the model repeats identical calls

Limits are configurable via LLM settings with priority: Model > Provider > Fallback.

Cached tool results bypass these checks entirely, allowing the model to reference previously computed results without counting towards limits.

## Cancellation Handling

Cancellation is handled through two mechanisms:

1. **Legacy `CancellationToken`**: Bridged onto the runtime context token for compatibility
2. **Runtime Context Token**: Native cancellation mechanism via `run_context.checkpoint()`

Checkpoints are placed at strategic locations:
- Before each tool execution
- During streaming on every chunk
- Between sequential tool executions

When cancelled, the stream is gracefully closed and `CancelledError` is raised to the caller.

## Error Handling

All tool execution errors are caught and normalized:

- Exceptions never propagate; error strings are returned to the model
- The model can react to failed tool invocations
- Prevents empty tool messages that would cause infinite loops
- Both successful and failed results are cached

## System Rules for Tool Output

Hardcoded system rules guide tool output formatting:

- Code blocks must include file names after the language specifier
- File paths should be valid (absolute or relative) based on project context
- Changes must follow original file formatting and indentation
- Avoid unnecessary changes unless explicitly requested
- Keep changes simple and easy to review