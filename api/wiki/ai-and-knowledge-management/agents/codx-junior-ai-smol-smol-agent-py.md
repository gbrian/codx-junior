# SmolAgent: Async OpenAI Chat Agent

SmolAgent is a streamlined, async-only implementation of an OpenAI chat agent designed for multi-step tool execution with comprehensive event streaming and cancellation support.

## Overview

SmolAgent improves upon traditional recursive chat implementations by:

- Exposing a single async `chat()` method (no synchronous variant)
- Using an **iterative tool loop** instead of recursion for better control
- Delegating loop protection, logging, event emission, and cancellation to dedicated components
- Supporting streaming callbacks, real-time analytics, and graceful cancellation
- Implementing tool scope classification and dual-response tool support
- Dynamically loading global chat instructions on each conversation

## Architecture

### Core Components

**Runtime Context**: All logging, event fan-out, cancellation checkpoints, and per-run analytics are delegated to `AgentRunContext`, providing a unified agent runtime. Callers can share custom contexts or provide event listeners via the `config` parameter.

**Loop Guard**: Prevents infinite tool loops by tracking execution rounds and detecting stuck patterns before tools are executed.

**Message Accumulator**: Handles streaming message assembly, tool call parsing, and content accumulation across multiple completion rounds.

**Analytics**: Records token usage, tool execution metrics, and session-level analytics non-fatally (errors don't interrupt the chat flow).

### Conversation Flow

```
1. Stream completion from LLM
2. Accumulate streamed content and check for tool calls
3. If tool_calls exist:
   - Guard against infinite loops
   - Execute each tool and collect results
   - Handle dual-response tools (user_content + llm_feedback)
   - Append results to conversation
   - Loop back to step 1
4. If no tool_calls, merge LLM content with accumulated user content
5. Record analytics and return updated messages
```

## Key Features

### Streaming with Accumulated Callbacks

Streaming callbacks receive the **full response accumulated so far** on every flush, not just deltas. This ensures mid-stream persistence is crash-safe: partial saves always contain all information streamed up to that point, never just the latest fragment.

### Tool Scope Support

Tools are classified by scope:

- **Global scope**: Always included in conversations, regardless of the `selected_tools` list
- **Chat scope**: Selectively included based on request configuration

This allows critical tools to remain available while request-specific tools can be toggled on/off.

### Dual-Response Tools

Tools can return either:

- **String**: Traditional single-response used for LLM context
- **ToolResponse**: Object with both `user_content` (displayed to user) and `llm_feedback` (for model context)

This separation allows tools like code generators to produce formatted user-facing output while keeping the LLM loop lightweight with concise feedback.

### Dynamic Global Instructions

Chat global instructions are loaded fresh from `GlobalSettings` on every chat invocation (not cached), ensuring instructions are always current. These are prepended to the system message, followed by any extra system instructions passed to the agent.

### Session Context Injection

SmolAgent injects session context into settings, allowing tools to access:

- Current chat state
- Session information
- User context

This enables complex tools like `generate_tasks_tool` to interact with the broader execution context beyond their direct parameters.

## Public API

### Constructor

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
- `llm_model`: Optional model override
- `user`: Optional user for API key and analytics
- `system`: Extra system prompt content (appended after global instructions)
- `session`: Session context for tools requiring access to chat/session state

### Chat Method

```python
async def chat(
    messages: List[Union[AIMessage, HumanMessage]],
    config: Optional[Dict[str, Any]] = None,
) -> List[Union[AIMessage, HumanMessage]]
```

**Parameters:**
- `messages`: Conversation history as LangChain message objects
- `config`: Optional dict with:
  - `tools`: List of selected tools
  - `chat_id`: Chat identifier
  - `cancellation_token`: Legacy cancellation token
  - `headers`: Request headers
  - `callbacks`: Streaming callbacks (receive full accumulated content)
  - `run_context`: Custom `AgentRunContext`
  - `event_listeners`: Event listener callables
  - `current_chat`: Chat object for context

**Returns:** Updated messages list with assistant reply appended

**Raises:**
- `ToolLoopError`: Max tool rounds or stuck loop detected
- `CancelledError`: Request cancelled by caller

## Internal Processing

### System Message Building

The system message combines three layers:

1. LLM settings system prompt (if configured)
2. Global chat instructions (loaded fresh on each chat)
3. Extra system instructions passed to constructor

All layers are concatenated with newlines for clarity.

### Tool Execution

Each tool execution:

1. Emits `TOOL_START` event with parsed arguments
2. Injects project settings if the tool requires them
3. Executes the tool (awaiting if async)
4. Handles both string and `ToolResponse` return types
5. Emits `TOOL_END` or `TOOL_ERROR` event with duration and result preview
6. Records analytics (non-fatal on error)
7. Returns result string or `ToolResponse` object

Tool errors are caught and returned as strings so the model can react to failures, rather than propagating exceptions.

### Request Building

The OpenAI request is configured with:

- Enabled tools filtered by scope (global + selected chat tools)
- Streaming enabled with usage information
- Optional temperature override
- Model and message history

### Analytics Recording

Token usage is recorded with:

- Input/output token counts (from provider or estimated)
- Request duration
- Project and user identifiers
- Cost calculations (cxjcoins)
- Session and chat identifiers for traceability

Tool execution metrics capture:
- Tool name and execution time
- Success/failure status with error details
- Parent chat and request identifiers

## Error Handling

**Preflight Check**: User wallet is checked before execution to prevent running out of budget mid-stream.

**Tool Errors**: Tool execution errors are caught and returned as strings, allowing the model to handle failures gracefully.

**Analytics Errors**: Analytics recording failures are logged but don't interrupt the chat flow.

**Stream Cancellation**: Cancellation is checked on every streamed chunk. When detected, the stream is closed and an `AgentCancelled` exception is raised, which the runtime translates to the legacy `CancelledError`.

## Configuration & Customization

### Hardcoded System Rules

The agent includes hardcoded rules about working with files (code block formatting, file paths, preservation of formatting) that are always appended to global instructions to ensure consistent behavior.

### Custom Callbacks

Callbacks registered via `config["callbacks"]` receive streaming updates with the full accumulated response. This enables real-time UI updates while maintaining crash-safe persistence semantics.

### Event Listeners

Event listeners receive lifecycle events:
- `RUN_START` / `RUN_END` / `RUN_ERROR` / `RUN_CANCELLED`
- `LLM_REQUEST` / `LLM_CHUNK` / `LLM_USAGE`
- `TOOL_START` / `TOOL_END` / `TOOL_ERROR`

Each event carries relevant metadata for logging, monitoring, and UI feedback.