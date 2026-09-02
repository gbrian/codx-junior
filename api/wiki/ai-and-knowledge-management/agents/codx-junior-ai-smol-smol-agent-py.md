# SmolAgent: Async OpenAI Chat Agent

SmolAgent is a lightweight, async-only streaming chat agent built on OpenAI's API. It provides multi-step tool support with intelligent caching, cancellation handling, and comprehensive analytics integration.

## Overview

SmolAgent simplifies agent implementation compared to traditional recursive approaches by using an iterative tool loop with built-in safeguards. It delegates runtime concerns like logging, event emission, and cancellation to a unified `AgentRunContext`, keeping the agent logic focused and maintainable.

### Key Features

- **Async-only design**: Single `chat()` method with no synchronous variant
- **Iterative tool loop**: Non-recursive multi-step tool execution with cycle protection
- **Tool result caching**: Automatic deduplication within conversations to avoid re-execution
- **Streaming support**: Real-time response delivery with chunk batching and callbacks
- **Comprehensive events**: `TOOL_START`, `TOOL_END`, `TOOL_ERROR`, `LLM_CHUNK`, `LLM_USAGE` for full observability
- **Cancellation safety**: Graceful handling of user-initiated cancellations
- **Dual-response tools**: Support for tools that return both user-facing and model-only content

## Architecture

### Conversation Flow

The agent follows a well-defined execution path:

1. **Initialization**: Resolve runtime context and build system message from cached global instructions
2. **Streaming loop**: Stream completions from the LLM until tool calls are detected or a final response is produced
3. **Tool execution**: Execute non-cached tool calls with guard checks; bypass checks for cached results
4. **Result handling**: 
   - Tool responses route to the model as tool messages only
   - Dual-response tools send user content to the final response, model feedback to the LLM
5. **Completion**: Record usage analytics and append final response to conversation history

Tool calls are separated into cached and uncached batches. Only uncached calls are subject to `LoopGuard` depth, breadth, and stuck-detection checks, allowing efficient reuse of previous results.

## System Message Building

The system message is dynamically constructed on each chat from three sources:

1. **LLM settings system prompt**: Model-specific base instructions
2. **Global chat instructions**: Loaded fresh from `GlobalSettings` (not cached) to ensure currency
3. **Extra system instructions**: Additional directives passed at agent initialization

This layered approach keeps instructions up-to-date while maintaining model consistency.

### Hardcoded System Rules

All agents include built-in rules for file handling, requiring code blocks with proper file paths and enforcing formatting consistency.

## Tool Execution

### Caching Strategy

Tool results are cached per conversation using a hash of the tool name and parameters. When the model requests an identical tool with the same arguments:

- The cached result is returned immediately
- No re-execution or LoopGuard checks occur
- A `TOOL_END` event is emitted with `cached=true` for observability

Both successful and failed results are cached to prevent repeated execution of broken tools.

### Dual-Response Tools

Tools can return either a string (traditional single-response) or a `ToolResponse` object:

- **Single-response**: Result goes to model context only; user never sees the raw output
- **Dual-response** (`ToolResponse`):
  - `user_response`: Appended to the final user-facing response (wrapped in code blocks)
  - `llm_response`: Sent to the model in tool messages; enables model feedback separate from user output

### Error Handling

All tool exceptions are caught and converted to error strings. The model always receives non-empty tool messages, preventing infinite loops where empty responses trigger re-execution of the same call.

## Loop Protection

The `LoopGuard` enforces limits on:

- **Max iterations**: Total rounds of tool calling
- **Max tool calls**: Total tools executed per round
- **Stuck detection**: Repeated identical tool calls within a round

Limits are resolved from `AISettings` with priority: Model > Provider > Fallback.

Cached tool results bypass all LoopGuard checks and don't count toward execution limits.

## Streaming and Callbacks

### Chunk Accumulation

The agent uses a state-based callback sender that:

1. Buffers incoming chunks
2. Flushes the **complete accumulated response** (not just deltas) periodically or on explicit flush
3. Invokes all registered callbacks with full content

This batching ensures crash-safe partial saves and reduces callback invocation overhead.

### Event Emission

The `AgentRunContext` emits throttled `LLM_CHUNK` events for UI progress and `LLM_USAGE` events carrying token counts for immediate analytics aggregation.

## Cancellation

Cancellation is checked:

- At the start of each tool execution
- On every chunk received during streaming
- Between sequential tool calls in a round

Legacy `CancellationToken` objects are bridged onto the runtime token, allowing both cancellation paths to converge on `AgentCancelled`.

## Analytics Integration

### Token Usage Recording

Token counts are sourced from provider-reported usage (if available) or estimated via `count_tokens()`. Analytics records:

- Input and output tokens
- Model, provider, and project identifiers
- Session and chat IDs for traceability
- Cost data (if configured)
- Tool cache statistics (hits, misses, hit rate)

### Tool Usage Recording

Every tool execution is recorded with:

- Execution time
- Success/failure status
- Error messages (if failed)
- Chat and request IDs for correlation

All analytics recording is non-fatal; failures are logged but don't interrupt the conversation.

## Configuration

### Initialization

```python
agent = SmolAgent(
    settings=CODXJuniorSettings,
    llm_model="optional-override",
    user=CodxUser,
    system="additional system prompt",
    session=session_context
)
```

### Chat Invocation

```python
result = await agent.chat(
    messages=[AIMessage(...), HumanMessage(...)],
    config={
        "tools": ["tool1", "tool2"],  # chat-scoped tools to enable
        "chat_id": "...",
        "cancellation_token": token,
        "callbacks": [callback_fn],
        "run_context": context,  # optional; created if not provided
        "event_listeners": [listener],
        "current_chat": chat_object,
    }
)
```

### Tool Scopes

Tools declare their scope in settings:

- **Global scope** (`"scope": "global"`): Always included regardless of selected tools
- **Chat scope** (default): Selectively included based on `config["tools"]`

## Response Assembly

The final response combines:

- LLM-streamed text from all iterations (tool-calling rounds + final response)
- User-facing content from dual-response tools (wrapped in code blocks)

Tool results (model feedback, raw outputs) are never included in the user-facing response; they serve model context only.

## Preflight Checks

Before execution, the agent performs a wallet check if the LLM pricing model requires it. This prevents spending against exhausted budgets.