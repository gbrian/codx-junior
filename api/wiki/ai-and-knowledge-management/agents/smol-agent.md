# SmolAgent Documentation

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed for streaming chat completions with iterative multi-step tool support. Unlike traditional recursive approaches, it uses an iterative tool loop and delegates lifecycle management to `AgentRunContext`.

### Key Features

- **Async-only API**: Single `async chat()` method (no synchronous variant)
- **Iterative tool loop**: Processes tool calls sequentially rather than recursively
- **Tool result caching**: Caches identical tool calls within a conversation to avoid re-execution
- **Streaming support**: Maintains full streaming capabilities with callbacks and real-time progress
- **Dual-message response**: Separates thinking (tool-calling rounds) from final answers
- **Comprehensive event system**: Emits `TOOL_START`, `TOOL_END`, `TOOL_ERROR`, `LLM_REQUEST`, and `LLM_USAGE` events
- **Loop protection**: Delegates guard logic to `LoopGuard` to prevent runaway execution

## Message Structure

When tools are used in a conversation, SmolAgent produces separate messages:

- **Thinking Message**: Contains tool-calling rounds' LLM text and intermediate processing noise (tool executions, reasoning steps). Only emitted if tools were actually used.
- **Final Answer Message**: Contains only the final LLM response without tool-related preprocessing. Always emitted.

If no tools are used, only the final answer message is returned.

## Initialization

```python
agent = SmolAgent(
    settings=CODXJuniorSettings,
    llm_model=None,              # Optional model override
    user=CodxUser,               # Optional user for API key and analytics
    system=None,                 # Optional extra system prompt
    session=None                 # Optional session context for tools
)
```

### Parameters

- **settings**: Project settings providing LLM configuration
- **llm_model**: Optional override of the default model (uses settings' model by default)
- **user**: Optional user object (provides API key and enables analytics)
- **system**: Optional extra system prompt content (appended after global instructions)
- **session**: Optional session context for tools requiring current chat state

## Chat Method

```python
result = await agent.chat(
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None
)
```

### Parameters

- **messages**: Conversation history as LangChain message objects
- **config**: Optional configuration dictionary with keys:
  - `tools`: List of tool names to enable (chat-scoped; global tools always included)
  - `chat_id`: Unique conversation identifier
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Request headers (may include `session_id` and `tags`)
  - `callbacks`: List of streaming callback functions
  - `run_context`: Custom `AgentRunContext` (creates new one if omitted)
  - `event_listeners`: List of event listener callables
  - `current_chat`: Chat object for context

### Returns

Updated messages list with assistant replies appended as:
- Thinking message (if tools were used)
- Final answer message (always present if content produced)

Tool results and intermediate processing are never included in the returned messages.

### Exceptions

- **ToolLoopError**: Raised if max tool rounds, max tool calls, or stuck loop detected
- **CancelledError**: Raised if request cancelled by caller
- **InsufficientFundsError**: Raised if user lacks budget (from preflight wallet check)

## System Message Construction

The system message is dynamically built on every chat call from three sources:

1. **LLM settings system prompt** (if configured)
2. **Global instructions** (loaded fresh from GlobalSettings)
3. **Extra system instructions** (passed to `__init__`)

Global instructions include hardcoded rules for file operations (code blocks, path formatting, indentation preservation).

## Tool Execution

### Tool Call Flow

1. Detect tool calls from LLM completion
2. Separate cached and uncached tool calls
3. Check `LoopGuard` limits (only for uncached calls)
4. Execute uncached tools and emit `TOOL_START`/`TOOL_END`/`TOOL_ERROR` events
5. Append both cached and fresh results to conversation
6. Continue streaming for next completion until no tool calls remain

### Tool Result Caching

Tools are cached by name and parameter hash. Cached results:
- Bypass `LoopGuard` checks entirely (don't count toward limits)
- Skip re-execution
- Still emit `TOOL_END` events with `cached=true` flag
- Work for both successful and failed results

### Tool Response Types

**Single-response tools** return a string:
- Result sent to model only
- Not included in final response

**Dual-response tools** return a `ToolResponse` object:
- `user_response`: Displayed to user in thinking message
- `llm_response`: Sent to model only (not in response)

### Tool Result Normalization

All results are normalized to non-empty strings:
- `None` → sentinel value `"(tool returned no output)"`
- Empty string → sentinel value
- `dict`/`list` → JSON-serialized
- Other types → `str()` conversion

Empty results are never sent to the model to prevent infinite tool-call loops.

## Request Building

### Tool Filtering

Tools are filtered by scope:
- **Global scope tools**: Always included regardless of configuration
- **Chat scope tools**: Included only if explicitly selected in `config["tools"]`

### Request Parameters

Base kwargs built by `_build_request_kwargs()`:
- `model`: Selected LLM model
- `stream`: Always `true`
- `stream_options`: `{"include_usage": true}` for token tracking
- `tools`: Enabled tool definitions (filtered by scope)
- `temperature`: From LLM settings (if non-zero)

## Streaming and Callbacks

### Streaming Flow

1. Stream chunks from OpenAI API
2. Accumulate chunks in buffer
3. Periodically flush full accumulated response to callbacks
4. Parse tool calls from delta chunks
5. Emit `LLM_CHUNK` events for UI progress
6. Bridge cancellation tokens to runtime context

### Callback Behavior

Callbacks receive the **complete accumulated response** (not just deltas):
- Periodic flushing at `CALLBACK_FLUSH_SECONDS` intervals
- Immediate flush on stream completion
- Full response for crash-safe persistence
- Never empty messages to callbacks unless stream ends

## Analytics and Monitoring

### Token Usage Recording

Token usage is recorded with:
- Prompt and completion token counts (from provider or calculated)
- Duration in seconds
- Cache hit/miss statistics
- Tags and metadata (model, provider, project, user)
- Cost tracking via `input_k_tokens_cxjcoins` and `output_k_tokens_cxjcoins`

Token counts include both thinking and final answer content.

### Tool Usage Recording

Each tool execution records:
- Tool name and execution time
- Success/failure status with error details
- Parent chat and request identifiers
- User and project context

### Event Emission

Events emitted through `AgentRunContext`:

| Event | Payload | Purpose |
|-------|---------|---------|
| `LLM_REQUEST` | model, message_count | Track LLM requests |
| `LLM_CHUNK` | (via guard_stream) | Real-time UI progress |
| `LLM_USAGE` | prompt_tokens, completion_tokens | Token tracking |
| `TOOL_START` | tool, tool_call_id, args | Track tool execution start |
| `TOOL_END` | tool, tool_call_id, result, cached, duration_ms | Track successful completion |
| `TOOL_ERROR` | tool, tool_call_id, error, duration_ms | Track failures |
| `RUN_START` / `RUN_END` / `RUN_CANCELLED` / `RUN_ERROR` | (via run_context.run()) | Lifecycle events |

## Conversation Flow Diagram

```
chat() → Preflight limit check
      → Resolve AgentRunContext
      → Build system message
      → Initialize LoopGuard and ToolCache
      → Stream completion loop:
          → Accumulate streamed content
          → Parse tool calls
          → Separate cached/uncached calls
          → Execute uncached tools
          → Append results to conversation
          → Check for more tool calls
      → Record usage and cache stats
      → Emit thinking message (if tools used)
      → Emit final answer message
      → Return updated messages
```

## Error Handling

### Tool Execution Errors

- All tool exceptions are caught and returned as error strings
- Errors are cached to prevent re-execution
- Model receives non-empty error message to react appropriately
- No exceptions propagate to the caller

### Cancellation

- Checked at stream level and between tool executions
- Both legacy `CancellationToken` and runtime context tokens supported
- Gracefully closes stream and raises `CancelledError`
- Emits `RUN_CANCELLED` event with analytics

### Loop Protection

`LoopGuard` enforces:
- Maximum iterations (configurable from `max_iterations`)
- Maximum tool calls per round (configurable from `max_tool_calls`)
- Detection of stuck loops (repeated identical calls)
- Applied only to uncached tool calls

## Advanced Features

### Session Context Injection

Optional session context passed during initialization:
- Stored in agent instance
- Injected into settings for tools requiring it
- Used to establish current chat reference

### Wallet Check

Preflight wallet validation:
- Checked before each chat request
- Uses `input_k_tokens_cxjcoins` and `output_k_tokens_cxjcoins` from settings
- Raises `InsufficientFundsError` if budget exhausted
- Non-fatal: skipped if costs not configured

### Tag Building

Analytics tags constructed from:
- Request headers' `tags` field (split by comma)
- Temperature setting
- Project name
- Username (if user provided)
- Cache statistics (hits, misses, hit rate)

## Design Principles

- **Non-blocking**: Fully async for concurrent request handling
- **Observable**: Rich event system for monitoring and UI integration
- **Safe**: Aggressive error handling prevents infinite loops and crashes
- **Traceable**: Request/tool/chat IDs link events in distributed systems
- **Performant**: Streaming and caching optimize latency and cost
- **Flexible**: Pluggable cancellation, context, and event mechanisms