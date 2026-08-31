# SmolAgent Documentation

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed for streaming completions with iterative multi-step tool support. It provides a streamlined implementation compared to traditional chat agents by using an iterative tool loop instead of recursion and delegating core responsibilities to runtime infrastructure.

### Key Characteristics

- **Async-only**: Exposes a single async `chat()` method with no synchronous variant
- **Iterative execution**: Uses a loop-based approach instead of recursion for tool execution
- **Streaming support**: Maintains streaming, callbacks, cancellation, and analytics capabilities
- **Robust tool handling**: Ensures the model always receives meaningful tool feedback

## Architecture

### Core Components

**LoopGuard**
Delegates loop protection to prevent infinite tool-calling cycles by enforcing:
- Iteration depth limits (`max_iterations`)
- Tool calls per round limits (`max_tool_calls`)
- Stuck loop detection (identical consecutive rounds)

**AgentRunContext**
Unified runtime context that handles:
- Logging and event emission
- Cancellation management
- Per-run analytics

**Tool Call Accumulator**
Processes streaming tool calls from the LLM response and accumulates them for execution.

## Chat Flow

The agent follows this execution path:

1. **Stream completion** from the LLM with accumulated content tracking
2. **Check for tool calls** in the response
3. **If tool calls exist**:
   - Validate against loop guard (depth, breadth, stuck detection)
   - Save streamed content to accumulated buffer
   - Append assistant message with tool calls to conversation
   - Execute each tool sequentially
   - Normalize tool results (never None/empty)
   - Handle dual-response tools (user content + LLM feedback)
   - Append tool message to conversation
   - Loop back to step 1
4. **If no tool calls** (final response):
   - Merge all LLM responses across iterations
   - Add user-facing content from dual-response tools
   - Record analytics
   - Return updated message list

## Configuration and Initialization

### Constructor Parameters

```python
SmolAgent(
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None,
    session: Optional[Any] = None,
)
```

- **settings**: Project settings providing LLM configuration
- **llm_model**: Optional model override
- **user**: User object for API key and analytics
- **system**: Extra system prompt content (appended after global instructions)
- **session**: Optional session context for tools requiring access to chat state

### System Message Construction

The system message is built dynamically on each chat from three sources (in order):

1. LLM settings system prompt (if available)
2. Chat global instructions (loaded fresh from GlobalSettings)
3. Extra system instructions passed to initialization

This ensures global instructions remain current without caching.

## Tool Execution

### Tool Result Normalization

All tool results are normalized via `_normalise_tool_result()` before sending to the model using these priority rules:

1. `None` → Replaced with sentinel string `"(tool returned no output)"`
2. `str` → Returned as-is (empty strings → sentinel)
3. `dict`/`list` → JSON-serialized for readability
4. Other types → Converted via `str()` fallback

This prevents the model from re-issuing identical tool calls due to empty or missing tool messages.

### Dual-Response Tools

Tools can return a `ToolResponse` object containing:

- **user_content**: User-facing content displayed in the final message
- **llm_feedback**: Lightweight feedback for model context

This allows tools like `code_block_generator` to produce formatted output while keeping the LLM loop efficient.

### Tool Scopes

Tools can be classified by scope:

- **Global scope**: Always included in conversations regardless of selection
- **Chat scope**: Selectively included based on request configuration

Global scope tools are automatically added to every conversation.

## Streaming and Callbacks

### Callback Accumulation

Streaming callbacks receive the **full response accumulated so far** on every flush, not just deltas. This ensures:

- Mid-stream persistence of partial content is crash-safe
- No streamed information is lost during partial saves
- Callbacks always have complete context

### Event Types

The agent emits the following events via `AgentRunContext`:

- **LLM_REQUEST**: Issued before sending completion request
- **LLM_CHUNK**: Throttled during streaming
- **LLM_USAGE**: Provider token usage reported
- **TOOL_START**: Before executing a tool
- **TOOL_END**: After successful tool execution
- **TOOL_ERROR**: When tool execution fails
- **RUN_START/RUN_END/RUN_ERROR/RUN_CANCELLED**: Run lifecycle events

Tool events carry the `tool_call_id`, parsed JSON arguments, and truncated result preview for real-time rendering.

## Public API

### Chat Method

```python
async def chat(
    self,
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None,
) -> List[Union[AIMessage, HumanMessage]]:
```

**Parameters:**

- **messages**: Conversation history as LangChain message objects
- **config**: Optional dictionary with keys:
  - `tools`: List of enabled tool names
  - `chat_id`: Chat identifier
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Extra request headers
  - `callbacks`: List of streaming callbacks
  - `run_context`: Custom AgentRunContext
  - `event_listeners`: List of event listeners
  - `current_chat`: Chat object for context

**Returns:**

Updated messages list with the assistant reply appended. User-facing content from dual-response tools is included, and all assistant responses across the entire tool-calling loop are preserved.

**Raises:**

- `ToolLoopError`: If loop limits are exceeded or stuck loop detected
- `CancelledError`: If cancelled by the caller

## Response Accumulation

### Multi-Iteration Merging

The agent preserves all assistant text generated across tool-calling iterations:

- **llm_responses_accumulated**: Collects LLM text from each streaming round
- **user_facing_content**: Collects user content from dual-response tools

Final content is merged by joining all accumulated LLM responses followed by user-facing content.

### Content Preservation

Previously, only the final response (after all tool calls) was returned, losing intermediate assistant text. Now:

- All streamed content is preserved across iterations
- Explanatory text before, during, and after tool executions is retained
- The final message contains complete context from the entire run

## Session Context Injection

SmolAgent can inject session context into tool settings for tools requiring access to current chat or session state:

```python
if self.session and current_chat:
    self.settings._active_session = self.session
    self.session._current_chat = current_chat
```

This allows complex tools like `generate_tasks_tool` to interact with broader execution context beyond direct parameters.

## Analytics and Usage Recording

### Token Usage Recording

Token usage is recorded via `_record_usage()` capturing:

- Input and output tokens (from provider or calculated)
- Wall-clock duration
- Model and provider information
- User and project context
- Analytics tags

Calculations fall back to token counting when provider doesn't report usage.

### Tool Usage Recording

Tool execution metrics are recorded via `_record_tool_usage()` including:

- Tool name and execution time
- Success/failure status
- Error details
- Parent chat and request IDs

Both recording methods are non-fatal on error to prevent analytics failures from affecting chat operation.

## Hardcoded System Rules

The agent includes built-in system rules for file handling that are prepended to all system messages:

- Use code blocks with file names for file operations
- Follow original file formatting and indentation
- Avoid unnecessary changes unless explicitly requested
- Keep changes simple and easy to review

## Error Handling

### Exception Handling

All exceptions during tool execution are caught (not just OSError/ValueError/TypeError/RuntimeError) and returned as error strings. This ensures:

- The model always receives a non-empty tool message
- No infinite loops due to missing tool responses
- Proper error feedback to the model for recovery

### Cancellation

Cancellation is handled through both:

- Legacy `CancellationToken` (bridged to runtime context)
- Runtime context cancellation (`run_context.cancel()`)

Both paths converge on `AgentCancelled` exception with proper stream cleanup.

## Limits and Constraints

### Tool Call Limits

Limits are resolved from AISettings with priority:

1. Model-specific configuration
2. Provider-level configuration
3. Fallback defaults

These limits are enforced by LoopGuard on every tool round to prevent runaway execution.

### Wallet Checks

Pre-flight wallet validation via `check_user_wallet()` prevents execution when users exceed their budget based on configured token costs.