# SmolAgent: Async Streaming Chat Agent with Multi-Step Tool Support

## Overview

SmolAgent is a lightweight, async-only OpenAI chat agent designed for iterative multi-step tool execution. Unlike traditional recursive implementations, it uses an iterative tool loop for better control flow and combines several architectural improvements:

- **Async-only API**: Exposes a single `chat()` method with no synchronous variant
- **Iterative tool loop**: Replaces recursion with a while-based loop for clarity and maintainability
- **Delegated responsibilities**: Logging, event emission, and cancellation handled by `AgentRunContext`
- **Tool result caching**: Cached results per conversation prevent redundant execution
- **Dual message structure**: Separates thinking messages (tool-calling rounds) from final answers

## Key Features

### Streaming and Tool Execution

The agent streams LLM responses while accumulating tool calls. When tools are detected, it executes them iteratively until the model produces a final answer (no more tool calls).

### Tool Result Caching

Identical tool calls (same name and parameters) are cached within a conversation. Cached results:
- Bypass `LoopGuard` checks and don't count toward execution limits
- Emit `TOOL_END` events with `cached=True` for observability
- Improve performance by avoiding redundant expensive operations

### Message Structure

When tools are used, the response includes two messages:
- **Thinking Message**: Contains all tool-calling round text and intermediate reasoning
- **Final Answer Message**: Contains only the final LLM response without preprocessing noise

If no tools are used, only the final answer message is returned.

### Loop Protection

The `LoopGuard` enforces limits on:
- Maximum iterations (tool-calling rounds)
- Maximum tool calls per round
- Detection of stuck loops (repeated identical calls)

Only uncached tool calls are counted against these limits.

## API

### chat()

```python
async def chat(
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None,
) -> List[Union[AIMessage, HumanMessage]]
```

Runs a streaming chat completion with iterative multi-step tool support.

**Parameters:**
- `messages`: Conversation history as LangChain message objects
- `config`: Optional configuration dict with keys:
  - `tools`: List of tool names to enable
  - `chat_id`: Chat identifier
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Request headers
  - `callbacks`: List of callback functions for streaming output
  - `run_context`: Custom `AgentRunContext` for event handling
  - `event_listeners`: List of event listener callables
  - `current_chat`: Chat object for context

**Returns:**
Updated messages list with assistant replies appended (thinking message + final answer if tools were used, or just final answer otherwise).

**Raises:**
- `ToolLoopError`: If max tool rounds, max tool calls, or stuck loop is detected
- `CancelledError`: If the request is cancelled by the caller

## Tool Execution

### Tool Response Types

Tools can return either:
- **String**: Traditional single-response (used for LLM context only)
- **ToolResponse**: Dual-response where:
  - `user_response` → Added to thinking message
  - `llm_response` → Sent to model only

### Tool Events

The agent emits detailed tool events on `AgentRunContext`:
- `TOOL_START`: Before execution (includes parsed args)
- `TOOL_END`: After successful execution (includes result preview and cached flag)
- `TOOL_ERROR`: When execution fails (includes error details)

### Error Handling

All tool exceptions are caught and converted to error strings. The model always receives a non-empty tool message, preventing infinite loops from empty responses.

## System Prompt Construction

The system message is built dynamically on each chat from three sources (in order):

1. LLM settings system prompt (if configured)
2. `chat_global_instructions` (loaded fresh from GlobalSettings)
3. Extra system instructions passed to `__init__`

The hardcoded system rules include guidelines for working with files and code blocks.

## Analytics and Logging

### Token Usage Recording

Token usage is automatically recorded including:
- Input and output tokens (from provider or calculated)
- Duration and performance metrics
- Cache statistics (hit rate, hits, misses)

### Tool Call Archiving

Each tool execution is archived with:
- Tool name and call ID
- Request arguments (sanitized for serialization)
- Result sent to model
- Success/failure status and error messages
- Execution duration

### Message Archiving

Complete message exchanges are archived after successful streaming, including:
- Request and response content
- Token usage
- Model and provider information
- Traceability links

## Configuration

### Tool Scopes

Tools can be configured with scope settings:
- `global`: Always included regardless of configuration
- `chat`: Selectively included based on request configuration

### LLM Settings

Key settings from `CODXJuniorSettings`:
- `model`: LLM model identifier
- `api_key`: API authentication
- `api_url`: API endpoint
- `max_iterations`: Maximum tool-calling rounds
- `max_tool_calls`: Maximum tools per round
- `temperature`: Response randomness
- `system`: Base system prompt

## Cancellation Handling

The agent supports cancellation through:
- Legacy `CancellationToken` (bridged onto runtime token)
- Runtime `AgentRunContext` cancellation
- Checkpoints before each tool execution
- Stream closure on cancellation request

Cancelled runs emit `RUN_CANCELLED` events and raise `CancelledError`.

## Callback System

Callbacks receive the **full accumulated response** at periodic intervals (configurable via `CALLBACK_FLUSH_SECONDS`), not just deltas. This approach keeps partial saves crash-safe by always containing complete content streamed to that point.