# OpenAI AI Integration

## Overview

The `OpenAI_AI` class is a comprehensive wrapper around the OpenAI Python SDK that provides streaming chat completions with advanced features including multi-step tool calling, request/response logging, token analytics, and sophisticated loop detection mechanisms.

## Core Features

### Streaming Chat Completions

The module supports both synchronous and asynchronous streaming chat completion operations:

- **Synchronous**: `chat_completions()` - Standard streaming without tool support
- **Asynchronous**: `a_chat_completions()` - Full multi-step tool support with recursion guards

### Tool Calling Support

Multi-step tool calling is orchestrated with the following safeguards:

#### Recursion Depth Guard

The `_tool_recursion_depth` parameter tracks the number of sequential tool-call rounds. Each round represents one LLM response that requests tools. Multiple parallel tool calls within a single round count as a single depth increment, not multiple increments.

- **Maximum depth**: `MAX_TOOL_RECURSION_DEPTH` = 20 rounds
- Prevents infinite recursion while supporting legitimate multi-step reasoning chains (e.g., sequential file reading)

#### Loop Detection Guard

A SHA-256 fingerprint mechanism detects when the model becomes stuck requesting identical tools with identical arguments:

- **Fingerprint basis**: Stable hash of tool function names and normalized arguments
- **Order-independent**: Different ordering of the same tools produces identical fingerprints
- **Loop threshold**: `MAX_IDENTICAL_ROUNDS` = 3 consecutive identical rounds triggers abort

When either guard is violated, a `RuntimeError` is raised with descriptive messaging.

## Message Handling

### Message Conversion

The `convert_message_to_openai()` method converts LangChain message objects (AIMessage, HumanMessage) to OpenAI-compatible message dictionaries. Special handling is provided for image messages with JSON content validation.

### Message Preparation

The `preparer_messages_to_openai()` method:
- Converts message lists to OpenAI format
- Prepends system prompts from both LLM settings and instance configuration
- Supports message history override for recursive tool-call invocations via `_openai_messages_override` in config

## Logging and Analytics

### Raw Request/Response Logging

The `RawAILogger` captures complete request-response cycles with context including:
- Provider and model information
- Username and project identifiers
- Session and request IDs for traceability
- Message payloads and tool calls
- Duration metrics and completion status

Methods:
- `_raw_log_request()` - Logs outgoing LLM requests
- `_raw_log_response()` - Logs completed responses
- `_raw_log_error()` - Logs error conditions

### Token Usage Analytics

The `_record_usage()` method tracks:
- Input and output token counts (from provider or fallback local counting)
- Model costs in CXJCoins
- Session and request identifiers
- User, project, and provider information
- Duration metrics

Supports both provider-supplied token counts and fallback counting via `count_tokens()`.

### Tool Usage Analytics

The `_record_tool_usage()` method records:
- Tool execution duration
- Success/failure status
- Error messages on failure
- Traceability links to parent LLM requests and chat sessions

## Configuration and Setup

### Initialization Parameters

- `settings`: `CODXJuniorSettings` - Project and LLM configuration
- `llm_model`: Optional model override
- `user`: `CodxUser` - User context for billing and identification
- `system`: Optional system prompt override

### API Credentials

The class prioritizes user-specific API keys over default settings:
- Uses `user.api_key` if available
- Falls back to `llm_settings.api_key` otherwise

## Cancellation Support

Requests support mid-stream cancellation via `CancellationToken`:

```python
config = {
    "cancellation_token": token
}
```

When cancellation is requested, the response stream is closed and a `CancelledError` is raised.

## Tool Execution Flow

1. **Tool-call detection** - Finish reason equals "tool_calls"
2. **Recursion check** - Verify depth hasn't exceeded `MAX_TOOL_RECURSION_DEPTH`
3. **Loop detection** - Check fingerprint history for stuck patterns
4. **Tool execution** - Call `process_tool_calls()` for each requested tool in parallel
5. **Message assembly** - Append assistant message with tool_calls array (required by OpenAI API)
6. **Result collection** - Gather tool outputs in role=tool messages
7. **Recursion** - Re-invoke `a_chat_completions()` with accumulated message history

## Additional Capabilities

### Image Generation

The `generate_image()` method generates images using DALL-E 3, returning the URL of the generated image.

### Embeddings

The `embeddings()` method returns a callable that computes text embeddings using the configured embeddings model. The callable concatenates embedding vectors from the provider response.

## Request Headers and Tags

Custom headers and analytics tags can be passed via config:

```python
config = {
    "headers": {
        "tags": "tag1,tag2",
        "session_id": "session123"
    }
}
```

Tags are augmented with temperature and user information before transmission.

## Preflight Checks

The `_preflight_limit_check()` method validates user wallet status before executing requests when the model has associated costs.

## Dependencies
**Imports from:** codx/junior/ai/ai_logger.py, codx/junior/ai/raw_logger.py, codx/junior/ai/cancellation.py, codx/junior/ai/wallet_check.py, codx/junior/settings.py, codx/junior/profiling/profiler.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/analytics/__init__.py, codx/junior/analytics/token_counter.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/ai/ai.py