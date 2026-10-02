# SmolAgent Documentation

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed for streaming chat completions with multi-step tool support. Unlike the standard `OpenAI_AI` implementation, SmolAgent uses an iterative tool loop instead of recursion and delegates key responsibilities to specialized components.

## Key Characteristics

### Design Principles

- **Async-only**: Exposes a single async `chat()` method with no synchronous variant
- **Iterative tool loop**: Processes tool calls sequentially rather than recursively
- **Delegated responsibilities**:
  - Loop protection via `LoopGuard`
  - Logging, event emission, and cancellation via `AgentRunContext`
  - Tool result caching to prevent re-execution of identical calls

### Feature Set

- Streaming responses with live callbacks
- Multi-step tool execution with cancellation support
- Tool result caching per conversation
- Real-time analytics and event tracking
- Combined thinking and final answer messages for complete conversation persistence

## Architecture

### Conversation Flow

The agent follows a structured execution pattern:

1. **Initialization**: Resolve runtime context and build request configuration
2. **Streaming loop**: Iteratively request completions from the LLM
3. **Tool execution**: When tool calls are detected:
   - Check tool cache for identical previous calls
   - Guard against runaway loops (max iterations, max calls, stuck detection)
   - Execute uncached tools with `TOOL_START`/`TOOL_END`/`TOOL_ERROR` events
4. **Message accumulation**: Combine thinking content (tool outputs) with final LLM response
5. **Completion**: Emit single final answer message and record analytics

### Message Structure

The agent produces a unified final answer message combining:
- **Thinking content**: Accumulates user-facing outputs from dual-response tools during tool-calling rounds
- **Final answer content**: The final LLM response after all tool calls complete

This structure ensures all tool-generated content is preserved in persisted messages while being streamed live to clients.

## Core Components

### Tool Execution

Tools can return two types of responses:

- **Single-response tools**: Return a string sent only to the model for context
- **Dual-response tools** (`ToolResponse`): Return both `user_response` (added to thinking content and streamed to client) and `llm_response` (sent to model only)

### Tool Caching

Tool results are cached per conversation based on tool name and parameters hash:
- Cached results bypass `LoopGuard` checks entirely
- Cache hits don't count toward execution limits
- Enables efficient handling of repeated requests with identical parameters

### Loop Protection

The `LoopGuard` enforces three constraints on uncached tool calls:

- **Max iterations**: Maximum number of tool-calling rounds
- **Max tool calls**: Total tool invocations per conversation
- **Stuck detection**: Prevention of infinite loops with identical parameters

Priority for limits: Model > Provider > Fallback

## System Configuration

### System Message Building

The complete system message combines three sources:

1. **LLM settings system prompt**: Base model instructions
2. **Chat global instructions**: Loaded fresh from GlobalSettings on each chat (not cached)
3. **Extra system instructions**: Passed via constructor

Global instructions are loaded dynamically to ensure freshness, while hardcoded system rules regarding file handling are always included.

### Hardcoded System Rules

The agent includes built-in instructions for working with files:
- Use code blocks with file names as language identifiers
- Valid file paths (absolute or relative) based on project context
- Preserve original file formatting and indentation
- Avoid unnecessary changes unless explicitly requested
- Keep modifications simple and easy to review

## API Usage

### Initialization

```python
agent = SmolAgent(
    settings=CODXJuniorSettings,
    llm_model=Optional[str],
    user=Optional[CodxUser],
    system=Optional[str],
    session=Optional[Any]
)
```

### Chat Method

```python
messages = await agent.chat(
    messages=List[Union[AIMessage, HumanMessage]],
    config=Optional[Dict[str, Any]]
)
```

**Config parameters**:
- `tools`: List of enabled tool names
- `chat_id`: Conversation identifier
- `cancellation_token`: Legacy cancellation token
- `headers`: Extra request headers
- `callbacks`: List of chunk callback functions
- `run_context`: Existing `AgentRunContext` (reuses for shared cancellation/listeners)
- `event_listeners`: List of event listener callables
- `current_chat`: Chat object for tool context

**Returns**: Updated messages list with final assistant reply appended (tool results never included)

## Event Emission

SmolAgent emits detailed events via `AgentRunContext`:

- **`LLM_REQUEST`**: Before API call
- **`LLM_CHUNK`**: On each streamed chunk (throttled)
- **`LLM_USAGE`**: Provider token usage
- **`TOOL_START`**: Before tool execution with parsed arguments
- **`TOOL_END`**: After successful execution with truncated result preview
- **`TOOL_ERROR`**: On execution failure with error details
- **`RUN_START`/`RUN_END`/`RUN_ERROR`/`RUN_CANCELLED`**: Lifecycle events

Tool events carry `tool_call_id`, parsed arguments, and result previews for real-time UI rendering.

## Analytics and Monitoring

### Token Usage Recording

The agent automatically tracks:
- Input and output token counts
- Model and provider information
- Session and request identifiers
- Cache hit/miss statistics with hit rate percentages
- Cost tracking for budget enforcement

### Tool Call Archival

All tool executions are archived with:
- Tool name, call ID, and arguments
- Execution results (both user-facing and model-facing)
- Success/failure status and error messages
- Execution duration

### Request Archival

Completed LLM interactions are archived including:
- Full message exchange and response content
- Request ID for traceability
- Token usage and duration
- Chat and project context

## Error Handling

### Tool Execution Errors

- **ALL exceptions caught**: Returned as error strings to prevent model confusion
- **Never empty messages**: Model always receives non-empty tool results to prevent infinite loops
- **Cached error results**: Failed tool calls are cached to avoid re-execution
- **Error details in analytics**: Enables post-execution debugging

### Cancellation

- **Checkpoint-based**: Cancellation is checked at safe points (before tools, during streaming)
- **Dual-path support**: Handles both `AgentRunContext` token and legacy `CancellationToken`
- **Stream cleanup**: Properly closes response streams on cancellation
- **Preserves callbacks**: Final flush sent even when cancelled

## Tool Configuration

### Tool Scope

Tools can be scoped as:
- **Global scope** (`TOOL_SCOPE_GLOBAL`): Always included regardless of selection
- **Chat scope** (`TOOL_SCOPE_CHAT`): Selectively enabled per request

### Tool Settings

Tools support configuration flags:
- `project_settings`: Injects `settings` parameter to tool function
- `async`: Indicates tool returns an awaitable
- `scope`: Tool scope designation

## Performance Considerations

### Streaming and Callbacks

- Chunks are buffered and flushed at intervals (default: 1 second) or on explicit flush
- Callbacks receive the **full accumulated content** (not just delta) for crash-safe persistence
- Thinking content is streamed live during tool rounds for real-time feedback

### Tool Caching

- Significant performance gain when models request identical tool calls repeatedly
- Cache statistics included in analytics for visibility
- Per-conversation scope prevents cross-chat cache contamination

### Request Limits

- Preflight wallet check prevents execution without sufficient budget
- Loop guards prevent runaway tool execution
- Configurable iteration and call limits per model/provider