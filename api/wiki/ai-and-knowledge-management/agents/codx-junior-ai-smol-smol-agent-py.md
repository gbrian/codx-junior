# SmolAgent: Async-Only OpenAI Chat Agent

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed as an improved alternative to `OpenAI_AI`. It implements a **streaming chat completion** system with **iterative multi-step tool support**, featuring enhanced loop protection, event emission, and cancellation handling.

### Key Distinctions from OpenAI_AI

- **Async-only**: Exposes a single `chat()` method with no synchronous variant
- **Iterative tool loop**: Uses iteration instead of recursion for tool execution
- **Delegated concerns**: Delegates loop protection, logging, event emission, and cancellation to `LoopGuard` and `AgentRunContext`
- **Preserved streaming**: Maintains streaming callbacks, cancellation support, and real-time analytics

## Core Concepts

### Streaming Callback Accumulation

Streaming callbacks now receive the **full accumulated response** on every flush, not just the delta since the last flush. This ensures:

- Mid-stream persistence of partial content is crash-safe
- No information is lost during mid-run saves
- Downstream consumers can safely assign callback payloads directly to response message content

### Tool Scope Support

Tools are classified by scope with different inclusion rules:

- **Global scope tools**: Always included in conversations regardless of configuration
- **Chat scope tools**: Selectively included based on request configuration

### Dual-Response Tools

Tools can return a `ToolResponse` object containing:

- **user_content**: Displayed to the user in the chat interface
- **llm_feedback**: Lightweight content sent to the model for continued processing

This allows tools (e.g., code_block_generator) to generate formatted output while keeping the LLM loop lightweight.

### Global Chat Instructions

Chat instructions are dynamically loaded from `GlobalSettings` on every chat invocation (not cached) to ensure freshness. The complete system message combines:

1. LLM settings system prompt (if available)
2. Chat global instructions (loaded fresh)
3. Extra system instructions passed to initialization

### Session Context Injection

SmolAgent injects session context into settings for tools requiring access to current chat or session state. This enables complex tools like `generate_tasks_tool` to interact with broader execution context beyond direct parameters.

### Full Response Accumulation Across Tool Loops

Assistant responses generated during tool-calling iterations are accumulated across all iterations, preserving:

- Intermediate assistant text generated before tool calls
- Explanatory content during tool execution
- All streamed content from every iteration (not just the final response)

This ensures no information is lost when the model generates explanatory text across multiple tool-calling rounds.

### Loop Guard with Resolved Limits

Tool execution limits are resolved from `AISettings` with priority: **Model > Provider > Fallback**. These limits are enforced by `LoopGuard` on every tool round to prevent:

- Runaway execution (depth violations via `max_iterations`)
- Breadth violations (tool calls per round via `max_tool_calls`)
- Stuck loops (detecting identical consecutive rounds)

## Class: SmolAgent

### Initialization

```python
SmolAgent(
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None,
    session: Optional[Any] = None,
)
```

**Parameters:**

- `settings`: Project settings providing LLM configuration
- `llm_model`: Optional model override (defaults to settings)
- `user`: Optional user object (used for API key and analytics)
- `system`: Optional extra system prompt (appended after global instructions)
- `session`: Optional session context injected for tools needing access to current chat/session state

### Primary Method: chat()

```python
async def chat(
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None,
) -> List[Union[AIMessage, HumanMessage]]
```

Executes a streaming chat completion with iterative multi-step tool support.

**Parameters:**

- `messages`: Conversation history as LangChain message objects
- `config`: Optional configuration dictionary with keys:
  - `tools`: List of enabled tool names
  - `chat_id`: Chat identifier
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Additional request headers
  - `callbacks`: Streaming callback functions
  - `run_context`: Custom `AgentRunContext` instance (reuses if provided)
  - `event_listeners`: Event listener callables
  - `current_chat`: Chat object for context

**Returns:**

Updated messages list with assistant reply appended. User-facing content from dual-response tools and all accumulated LLM responses are merged into the final assistant message content.

**Raises:**

- `ToolLoopError`: If max tool rounds, max tool calls, or stuck loop is detected
- `CancelledError`: If the request is cancelled by the caller

**Lifecycle:**

The entire run is wrapped in `AgentRunContext.run()`, which emits:
- `RUN_START`: At execution beginning
- `RUN_END`: On successful completion with analytics summary
- `RUN_ERROR`: On error condition
- `RUN_CANCELLED`: On cancellation

## Chat Loop Flow

The iterative chat loop follows this sequence:

1. **Stream completion** from LLM
2. **Accumulate streamed content** and check for tool calls
3. **If tool calls exist:**
   - Guard against infinite loops via `LoopGuard`:
     - Check iteration depth (`max_iterations`)
     - Check tool calls per round (`max_tool_calls`)
     - Detect stuck loops (identical consecutive rounds)
   - Save streamed content to accumulated responses
   - Append assistant message with tool calls to conversation
   - **Execute each tool:**
     - Emit `TOOL_START` event
     - Parse and execute tool with injected settings
     - Handle `ToolResponse` (extract user_content and llm_feedback)
     - Emit `TOOL_END` or `TOOL_ERROR` event
     - Append tool message to conversation
   - Loop back to step 1
4. **If no tool calls** (final response):
   - Merge all accumulated LLM content
   - Add user-facing content from dual-response tools
   - Record analytics
   - Return updated messages

## Tool Execution

### Tool Call Execution Flow

Each tool execution:

1. **Checkpoint cancellation** before spending time on tool
2. **Parse tool arguments** from JSON string or dict
3. **Locate tool** in the tools registry
4. **Inject settings** if tool requires project settings
5. **Execute tool** (with async support)
6. **Handle results:**
   - `ToolResponse`: Extract user_content and llm_feedback separately
   - String/JSON: Use as single response
7. **Emit events** with tool_call_id, parsed args, and result preview
8. **Record analytics** for tool execution

### Tool Arguments Parsing

```python
_parse_tool_arguments(raw_arguments: Any, func_name: str) -> Dict[str, Any]
```

Safely parses tool arguments accepting both JSON strings and dictionaries. Returns empty dict on parse failure with appropriate logging.

### Tool Events

Tools emit lifecycle events on the run context:

- `TOOL_START`: Includes tool name, tool_call_id, and parsed args (as copy)
- `TOOL_END`: Includes duration_ms and truncated result preview
- `TOOL_ERROR`: Includes duration_ms and error message

Event payloads allow listeners (e.g., ChatEventBridge) to surface tool executions as chat messages in real time.

## Request Building

### Building Request kwargs

```python
_build_request_kwargs(selected_tools: List[str]) -> Dict[str, Any]
```

Constructs OpenAI API request parameters:

- Includes model and streaming configuration
- Filters tools by scope (global always included, chat scope selectively included)
- Sets temperature from LLM settings
- Enables usage token reporting

### Building System Message

```python
_build_system_message() -> str
```

Constructs complete system message combining:

1. LLM settings system prompt (if available)
2. Chat global instructions (loaded fresh from GlobalSettings)
3. Extra system instructions passed to initialization

This ensures instructions are always up-to-date without caching.

## Streaming and Callbacks

### Stream Completion

```python
async def _stream_completion(
    kwargs: Dict[str, Any],
    openai_messages: List[Dict[str, Any]],
    headers: Dict[str, str],
    cancellation_token: Optional[CancellationToken],
    send_callback: Callable[[str, bool], None],
    run_context: AgentRunContext,
) -> Tuple[str, Dict[str, Dict[str, Any]], Any]
```

Streams one completion from OpenAI:

- Wraps stream with `run_context.guard_stream()` for cancellation checks
- Accumulates content chunks and tool calls
- Emits `LLM_CHUNK` and `LLM_USAGE` events
- Bridges legacy cancellation tokens onto runtime token

**Returns:** Tuple of accumulated content, tool calls dict, and usage info

### Callback Sender

```python
_make_callback_sender(
    callbacks: Optional[List[Callable[[str], None]]]
) -> Callable[[str, bool], None]
```

Returns a closure that:

- Buffers streamed chunks
- Accumulates all chunks across the entire run
- Flushes **full accumulated response** to callbacks (not just delta)
- Sends on timer (CALLBACK_FLUSH_SECONDS) or explicit flush
- Ensures mid-stream persistence is crash-safe

## Analytics and Metrics

### Recording Token Usage

```python
_record_usage(
    openai_messages: List[Dict[str, Any]],
    output_text: str,
    duration_seconds: float,
    tags: str,
    session_id: Optional[str],
    request_id: Optional[str],
    usage_info: Any,
    chat_id: Optional[str],
)
```

Records to analytics (non-fatal on error):

- Input and output token counts (from provider or estimated)
- Duration metrics
- Model and provider information
- Cost tracking via k_tokens_cxjcoins
- Session and chat identifiers

### Recording Tool Usage

```python
_record_tool_usage(
    tool_name: str,
    time_taken: float,
    success: bool,
    error_message: Optional[str],
    chat_id: Optional[str],
    request_id: Optional[str],
)
```

Records tool execution metrics:

- Tool name and execution duration
- Success/failure status
- Error details when applicable
- Parent chat and request identifiers

### Preflight Wallet Check

```python
_preflight_limit_check()
```

Runs pre-flight wallet validation before executing AI requests. Raises `InsufficientFundsError` if user budget is exhausted.

## Runtime Context Management

### Resolving Run Context

```python
_resolve_run_context(config: Dict[str, Any]) -> AgentRunContext
```

Returns the appropriate run context:

- Reuses `config["run_context"]` if provided (enables shared cancellation and event listeners)
- Creates fresh `AgentRunContext` with optional event listeners
- Allows callers to share context across multiple invocations

## Global Configuration

### Hardcoded System Rules

SmolAgent includes hardcoded system rules enforcing best practices for file handling:

- **Code blocks**: Always use code blocks with file names for file operations
- **File paths**: Use valid absolute or relative paths based on project context
- **Formatting preservation**: Maintain original file formatting and indentation
- **Minimal changes**: Avoid unnecessary changes, formatting, or cleanup unless explicitly requested
- **Review simplicity**: Keep changes simple and easy for users to review

These rules are automatically prepended to chat global instructions to ensure consistent code handling behavior.

## Error Handling and Cancellation

### Cancellation Flow

1. **Legacy token check**: `cancellation_token.is_cancelled` triggers runtime cancellation
2. **Runtime cancellation**: Sets `run_context.token.cancelled` and raises `AgentCancelled`
3. **Stream closure**: Safely closes response stream on cancellation
4. **Error translation**: `AgentCancelled` is converted to legacy `CancelledError`

### Tool Execution Error Handling

Tool errors are:

- Caught (OSError, ValueError, TypeError, RuntimeError)
- Logged with full exception traceback
- Returned as string responses (not propagated)
- Included in `TOOL_ERROR` events with error details

This allows the model to handle and react to failed tool invocations gracefully.

## Constants and Configuration

- `CALLBACK_FLUSH_SECONDS`: Interval (in seconds) for streaming callback flushes
- `TOOL_RESULT_PREVIEW_MAX_CHARS`: Maximum characters in tool result preview for events
- `TOOL_SCOPE_GLOBAL`: String constant for global scope tools
- `TOOL_SCOPE_CHAT`: String constant for chat scope tools
- `CANCELLED_MESSAGE`: Message when run is cancelled by caller