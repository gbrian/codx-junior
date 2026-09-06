# SmolAgent Documentation

## Overview

SmolAgent is a small, async-only OpenAI chat agent designed for streaming chat completions with multi-step tool support. It represents a simplified alternative to the `OpenAI_AI` implementation, emphasizing iterative tool loops and delegation of runtime concerns to a unified agent runtime context.

## Key Characteristics

SmolAgent differs from traditional OpenAI implementations in several ways:

- **Async-only**: Exposes a single asynchronous `chat()` method with no synchronous variant
- **Iterative tool loop**: Uses sequential iteration instead of recursion for tool execution
- **Delegated responsibilities**: Offloads loop protection, logging, event emission, and cancellation to `LoopGuard` and `AgentRunContext`
- **Streaming and callbacks**: Maintains full support for streaming responses, callbacks, cancellation, and analytics
- **Tool result caching**: Caches tool results within a conversation to prevent re-execution of identical calls

## Message Structure

When tools are used in a conversation, SmolAgent produces two separate message types:

1. **Thinking Message**: Contains tool-calling rounds' LLM text and intermediate processing (tool executions, reasoning steps). Only emitted if tools were used.
2. **Final Answer Message**: Contains only the final LLM response without tool-related preprocessing. Always emitted.

This separation keeps user-facing responses clean while preserving the full execution trace via the thinking message.

## Tool Event Tracking

Tool events (`TOOL_START`, `TOOL_END`, `TOOL_ERROR`) carry:
- The `tool_call_id`
- Parsed JSON request arguments
- Truncated result preview (up to `TOOL_RESULT_PREVIEW_MAX_CHARS`)

This enables listeners (e.g., ChatEventBridge) to surface tool executions as chat messages in real time.

## Initialization

```python
agent = SmolAgent(
    settings=CODXJuniorSettings,
    llm_model=None,           # Optional model override
    user=None,                # Optional CodxUser for API key and analytics
    system=None,              # Optional extra system prompt
    session=None              # Optional session context for tools
)
```

### Configuration Parameters

- **settings**: Project settings providing LLM configuration
- **llm_model**: Optional model override (defaults to LLM settings)
- **user**: Optional CodxUser object (used for API key, analytics, and wallet checks)
- **system**: Extra system prompt content appended after global instructions
- **session**: Session context injected for tools requiring access to current chat state

## Public API

### chat() Method

```python
async def chat(
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None,
) -> List[Union[AIMessage, HumanMessage]]:
```

Executes a streaming chat completion with iterative multi-step tool support.

#### Parameters

- **messages**: Conversation history as LangChain message objects
- **config**: Optional configuration dict with keys:
  - `tools`: List of enabled tools
  - `chat_id`: Chat identifier
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Additional request headers
  - `callbacks`: List of callback functions
  - `run_context`: Custom `AgentRunContext`
  - `event_listeners`: List of event listener callables
  - `current_chat`: Chat object for context

#### Returns

Updated messages list with assistant replies appended. If tools were used, includes both thinking and final answer messages. If no tools were used, only the final answer message is included.

#### Exceptions

- **ToolLoopError**: If max tool rounds, max tool calls, or stuck loop is detected
- **CancelledError**: If the request is cancelled by the caller

## Tool Execution

### Tool Result Normalization

All tool results are normalized to non-empty strings to prevent model re-execution:

1. `None` → sentinel value `(tool returned no output)`
2. `str` → returned as-is (empty strings converted to sentinel)
3. `dict`/`list` → JSON-serialized
4. Other types → `str()` fallback

This ensures the model always receives meaningful feedback.

### Tool Response Types

Tools can return:

- **String**: Traditional single-response used for LLM context only
- **ToolResponse**: Dual-response where:
  - `user_response` goes to the thinking message
  - `llm_response` goes to the model only

### Tool Caching

Tool results are cached within a conversation to avoid re-execution:

- Caching key: Tool name + parameters hash
- Cached results bypass `LoopGuard` checks (don't count toward limits)
- Both successful and failed results are cached

## System Message Building

The system message combines three sources (in order):

1. LLM settings system prompt (if available)
2. Chat global instructions (loaded fresh from GlobalSettings on each chat)
3. Extra system instructions passed during initialization

Global instructions are loaded dynamically on every chat to ensure they're always up-to-date. Hard-coded system rules for file handling are included automatically.

## Streaming and Callbacks

### Chunk Handling

- Chunks are buffered and the FULL accumulated response is sent to callbacks
- Flushing occurs periodically (every `CALLBACK_FLUSH_SECONDS`) or on explicit flush
- Callback strategy ensures crash-safety: partial saves always contain complete content streamed so far

### Usage Reporting

Provider usage is emitted as `LLM_USAGE` events, allowing run analytics to aggregate tokens automatically.

## Cancellation

Cancellation can occur through:

- Legacy `CancellationToken` (bridged onto runtime token)
- `AgentRunContext` cancellation
- Both paths converge on `AgentCancelled` exception

Cancellation checkpoints exist:
- Before each tool execution
- On every chunk in the streaming loop
- Before critical operations

## Analytics and Logging

SmolAgent records:

- Token usage (prompt and completion tokens)
- Tool execution metrics (duration, success/failure, error details)
- Archived messages (complete request/response exchanges)
- Tool call execution details
- Cache statistics (hits, misses, hit rate)

All recording is non-fatal: failures don't interrupt the chat flow.

## Loop Guard

The `LoopGuard` protects against:

- Infinite tool-calling loops via maximum iteration limits
- Breadth violations (too many tools in one round)
- Stuck loops (repeated identical tool calls)

Limits are resolved with priority: Model > Provider > Fallback. Only uncached tool calls count toward guard limits; cached results bypass all checks.

## System Rules for File Handling

SmolAgent includes hard-coded system rules that enforce:

- Code blocks with file names for all file operations
- Valid file paths (absolute or relative) based on project context
- Preservation of original formatting and indentation
- Minimal, reviewable changes (no unnecessary cleanup)

These rules are automatically appended to global instructions.