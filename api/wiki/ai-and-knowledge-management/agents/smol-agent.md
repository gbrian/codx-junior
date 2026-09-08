# SmolAgent Documentation

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed for streaming chat completions with multi-step tool support. It provides an iterative approach to tool execution with built-in protection against infinite loops, comprehensive logging, and analytics tracking.

### Key Characteristics

- **Async-only**: Exposes a single async `chat()` method with no synchronous variant
- **Iterative tool loop**: Uses iterative processing instead of recursion
- **Stream-first**: Supports real-time streaming callbacks during tool execution
- **Tool caching**: Caches tool results per conversation to avoid re-execution
- **Unified runtime**: Delegates logging, event emission, and cancellation to `AgentRunContext`
- **Safety guards**: Implements loop protection via `LoopGuard` to prevent runaway execution

## Architecture

### Message Structure

When tools are used in a conversation, SmolAgent produces a single final answer message combining:
- **Thinking content**: Accumulated LLM text and dual-response tool outputs during tool-calling rounds
- **Final answer content**: The final LLM response after all tool calls complete

This structure ensures all tool-generated user-facing content is preserved in persisted messages while being streamed live to clients via callbacks.

### Conversation Flow

The agent follows this execution pattern:

1. **Initialization**: Resolve `AgentRunContext`, build system message, initialize `ToolCache` and `LoopGuard`
2. **Streaming loop**: Request completion from OpenAI with streaming enabled
3. **Response accumulation**: Collect content and tool calls from streamed chunks
4. **Tool handling**: 
   - Check cache for identical tool calls (same name + args)
   - For cached calls: emit `TOOL_END` event with `cached=true`
   - For uncached calls: check guards, execute tool, emit `TOOL_START`/`TOOL_END`/`TOOL_ERROR`
5. **Result processing**:
   - Dual-response tools: `user_response` → thinking content (streamed + persisted), `llm_response` → model only
   - Single-response tools: Result → model only (not included in user-facing content)
6. **Final answer**: Combine thinking and final answer content into single AIMessage

## Core Components

### SmolAgent Class

The main agent class managing chat execution and tool integration.

#### Constructor

```python
def __init__(
    self,
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None,
    session: Optional[Any] = None,
) -> None:
```

**Parameters:**
- `settings`: Project settings providing LLM configuration
- `llm_model`: Optional model override (defaults to settings model)
- `user`: Optional user for API key and analytics
- `system`: Extra system prompt content appended after global instructions
- `session`: Session context for tools requiring access to chat/session state

#### Public API

##### `chat()` Method

```python
async def chat(
    self,
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None,
) -> List[Union[AIMessage, HumanMessage]]:
```

Runs a streaming chat completion with iterative multi-step tool support.

**Configuration Options (via `config` dict):**
- `tools`: List of enabled tool names
- `chat_id`: Chat identifier for tracing
- `cancellation_token`: Legacy cancellation token
- `headers`: Request headers (may include `tags`, `session_id`)
- `callbacks`: List of streaming callbacks
- `run_context`: Custom `AgentRunContext` (shares cancellation and listeners)
- `event_listeners`: List of event listener callables
- `current_chat`: Chat object for tool context

**Returns:** Updated messages list with final assistant reply appended

**Raises:**
- `ToolLoopError`: If max tool rounds, max tool calls, or stuck loop detected
- `CancelledError`: If request cancelled by caller

## System Message Construction

The agent dynamically builds system messages on each chat to ensure freshness:

1. **LLM settings system prompt** (if configured)
2. **Global instructions** (loaded fresh from GlobalSettings)
3. **Hardcoded system rules** (file handling standards)
4. **Extra system instructions** (passed to constructor)

See: `_build_system_message()`, `_load_chat_global_instructions()`

## Tool Execution

### Tool Call Processing

Tools are executed through `_execute_tool()` with automatic error handling:

1. **Validation**: Check tool exists in registry
2. **Parameter injection**: Inject settings if tool requires them
3. **Execution**: Call tool function (async or sync)
4. **Result normalization**: Convert output to non-empty string via `_normalise_tool_result()`
5. **Caching**: Store result in `ToolCache` for conversation
6. **Analytics**: Record execution details and archive to analytics

**Tool Return Types:**
- `str`: Traditional single-response (used for LLM context only)
- `ToolResponse`: Dual-response with `user_response` (user-facing) and `llm_response` (model-facing)

### Result Caching

The `ToolCache` stores results keyed by tool name + parameter hash:

- **Cache hits**: Skip execution and LoopGuard checks
- **Cache misses**: Execute tool and check guards
- Cached results surface `user_response` to thinking content exactly like uncached execution
- Statistics tracked: hits, misses, hit rate (included in analytics tags)

See: `codx.junior.ai.smol.tool_cache.ToolCache`

### Tool Scope

Tools are filtered by scope:

- **Global scope** (`TOOL_SCOPE_GLOBAL`): Always included regardless of configuration
- **Chat scope** (`TOOL_SCOPE_CHAT`): Selectively included based on `config["tools"]`

## Streaming and Callbacks

### Stream Processing

The `_stream_completion()` method handles OpenAI streaming:

1. **Guarded iteration**: Wraps stream with `AgentRunContext.guard_stream()` for cancellation checks
2. **Chunk accumulation**: Collects content and tool calls from delta messages
3. **Callback flushing**: Sends FULL accumulated response to callbacks (not just delta)
4. **Usage tracking**: Emits `LLM_USAGE` events for token accounting
5. **Message archival**: Records complete message exchange to analytics after streaming

### Callback Strategy

Callbacks receive the FULL accumulated response so far (never just the delta):

- Periodic flushing on interval (`CALLBACK_FLUSH_SECONDS`)
- Immediate flushing on tool execution boundaries
- Ensures crash-safe partial saves always contain complete streamed content

See: `_make_callback_sender()`

## Loop Protection

The `LoopGuard` enforces execution limits:

- **Max iterations**: Total number of tool-calling rounds
- **Max tool calls**: Total number of tools executed across all rounds
- **Stuck loop detection**: Detects repeated identical tool calls

**Behavior:**
- Only uncached tool calls count towards limits
- Cached calls bypass all guard checks
- Violations raise `ToolLoopError` (surfaces as `RUN_ERROR`)

See: `codx.junior.ai.smol.loop_guard.LoopGuard`

## Cancellation and Error Handling

### Cancellation

The agent supports two cancellation paths that converge on `AgentCancelled`:

1. **Legacy path**: `CancellationToken` checked on every chunk
2. **Runtime path**: `AgentRunContext.token` checked at cancellation points

**Cancellation points:**
- Before tool execution: `run_context.checkpoint()`
- During streaming: Guard stream checks every chunk
- Result: Stream closes, callbacks flushed, `CancelledError` raised

### Tool Errors

All tool exceptions are caught and normalized:

- Error string returned to model (never empty message)
- Error result cached to avoid re-execution
- `TOOL_ERROR` event emitted with error details
- Analytics record error with timestamp

See: `_execute_tool()` try/except/finally block

## Analytics and Logging

### Event Types

The agent emits events via `AgentRunContext`:

- `RUN_START`: Chat execution begins
- `RUN_END`: Chat execution completes successfully
- `RUN_ERROR`: Tool loop limit exceeded
- `RUN_CANCELLED`: Request cancelled by caller
- `LLM_REQUEST`: LLM request initiated
- `LLM_USAGE`: Token usage reported
- `LLM_CHUNK`: Streamed chunk received (throttled)
- `TOOL_START`: Tool execution begins
- `TOOL_END`: Tool execution completes
- `TOOL_ERROR`: Tool execution failed

### Message Archival

Complete message exchanges are archived to analytics including:

- Request messages (OpenAI format)
- Response content
- Token usage (input/output)
- Duration and model info
- Request ID for traceability

Tool call archives include:
- Tool name, parameters, and result
- Success/failure status with error message
- Execution duration
- Distinguishes cached vs fresh execution

### Token Usage Recording

Usage is recorded with:

- Input/output token counts (from provider or calculated)
- Combined token count for thinking + final answer content
- Cost calculation via `input_k_tokens_cxjcoins` and `output_k_tokens_cxjcoins`
- Cache statistics (hits, misses, hit rate)
- Provider, model, and project information

See: `_record_usage()`, `count_tokens()`

## Tool Argument Handling

### Argument Parsing

Tool arguments arrive as either JSON strings or dicts:

```python
@staticmethod
def _parse_tool_arguments(raw_arguments: Any, func_name: str) -> Dict[str, Any]:
```

- Dicts returned as-is
- Strings parsed via `json.loads()`
- Parse failures logged and return empty dict

### Serialization Sanitization

Results and parameters are sanitized for analytics:

```python
@staticmethod
def _sanitize_for_serialization(obj: Any) -> Any:
```

Handles:
- Async futures and coroutines (converted to string representation)
- Pydantic models (dumped to dict)
- Recursive sanitization of nested structures
- Fallback to `str()` for non-serializable types

## Configuration and Settings

### System Rules

Hardcoded system rules cover file handling standards:

- Use code blocks with file names for all file operations
- Maintain original file formatting and indentation
- Avoid unnecessary changes unless explicitly requested
- Keep changes simple and easy to review

See: `HARDCODED_SYSTEM_RULES`

### Settings Resolution

The agent resolves settings with this priority:

1. User-provided API key (if available)
2. LLM settings API key (fallback)
3. Model from LLM settings (with optional override)
4. Base URL from LLM settings
5. Temperature and tool limits from LLM settings

## Request Building

### OpenAI Request Construction

The `_build_request_kwargs()` method prepares base request parameters:

- Model and streaming options
- Tool definitions (filtered by scope)
- Temperature setting
- Stream usage tracking

**Tool Filtering Logic:**
- Global scope tools always included
- Chat scope tools included if in `config["tools"]` list
- Tool names and scope configured via tool registry

### Request Headers

Headers support:

- `tags`: Analytics tag string (extended with cache statistics)
- `session_id`: Session tracking
- `x-litellm-tags`: Provider-specific tagging
- Custom headers passed through to OpenAI

See: `_build_tags()`

## Wallet and Preflight Checks

Pre-flight wallet verification runs before chat:

```python
def _preflight_limit_check(self) -> None:
```

- Checks user wallet balance against LLM costs
- Input cost: `input_k_tokens_cxjcoins`
- Output cost: `output_k_tokens_cxjcoins`
- Raises `InsufficientFundsError` if budget exhausted

See: `check_user_wallet()`

## Constants and Sentinels

- `CANCELLED_MESSAGE`: Message when run cancelled by caller
- `TOOL_SCOPE_GLOBAL`: Global scope constant
- `TOOL_SCOPE_CHAT`: Chat scope constant
- `_TOOL_NO_OUTPUT`: Sentinel for tools returning None/empty
- `CALLBACK_FLUSH_SECONDS`: Interval for callback flushing
- `TOOL_RESULT_PREVIEW_MAX_CHARS`: Max length for result previews in events

## Related Components

- **AgentRunContext**: Unified runtime context handling logging, events, cancellation
- **LoopGuard**: Tool execution loop protection
- **ToolCache**: Per-conversation tool result caching
- **ToolCallAccumulator**: Accumulates tool calls from streamed chunks
- **Analytics**: Records usage, messages, and tool calls
- **CancellationToken**: Legacy cancellation interface

See also: `codx.junior.ai.cancellation`, `engine.agent_runtime`, `codx.junior.analytics`