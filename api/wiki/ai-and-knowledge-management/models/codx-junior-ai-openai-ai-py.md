# API Integration Modules Wiki - Model AI Components

## Overview Overview

Model AI components in Codx Junior enable comprehensive OpenAI integration for chat completions, tool execution, embeddings, and more. The `OpenAI_AI` singleton class serves as the core abstraction layer that handles model-specific logic while respecting project settings, rate limits, wallet constraints, per-request tags, parent chain tracking, asynchronous streaming, structured error reporting via raw logging, session/context propagation, wallet-based access controls for premium models, and token/budget analytics to ensure responsible usage across multi-tenant environments.

---

## Core Architecture

**Singleton Instance**: The `OpenAI_AI` class is designed as a singleton pattern with the global state managed internally (see `_get_analytics()` initialization flow). This ensures centralized configuration of LLM settings, OpenAI client instances, and shared utility objects while avoiding duplicate connections for multiple concurrent requests.
- `__init__()`: Initializes with `settings`, optional `llm_model`, `user` context, and custom `system` prompts. Loads tools from the `codx.junior.tools.TOOLS` module upon instantiation (see tools integration).

---

## Chat Completions Operations

### Synchronous Completion (`chat_completions`)

The synchronous chat completion method orchestrates non-asynchronous API calls using a streaming pipeline for real-time partial response handling while maintaining full stream support. It handles system messages, user context merging, custom headers with optional session/request identifiers, raw logging of outbound/inbound payloads, cancellation token injection from calling contexts (e.g., `config.get("cancellation_token", None)`), and structured analytics tracking per-request.
- **Usage**: Called directly when synchronous interaction is required; delegates streaming to the OpenAI client (`self.client.chat.completions.create`) while buffering chunks for callbacks.

### Asynchronous Completion (`a_chat_completions`)

The asynchronous chat completion method extends core capabilities by enabling non-blocking API calls and dynamic tool selection:
- **Tool Integration**: When `config.get("tools", [])` is provided, the method maps user-level tools to OpenAI-compatible parameters via `[t["tool_json"] for t in self.tools if ...]`, passing only selected functions.
- **Streaming with Tool Detection**: Processes streaming chunks while checking both structured tool calls (`choice.delta.tool_calls`) and JSON-formatted tool invocations in message content (via `_parse_tool_call()`).
- **Recursive Tool Execution**: When `finish_reason == "tool_calls"`, the method logs a partial response, executes sub-tool steps via `process_tool_calls()`, appends AIMessage outputs to the context stack, and recursively invokes synchronous completion with an updated `parent_request_id`.

---

## Tool Calling Machinery

### Tool Parsing (`_parse_tool_call`)
Attempts JSON deserialization of unstructured chunk streams. If a dict contains a top-level `"name"` key, it maps the tool reference against registered tools (checking `any(tool["tool_json"]["function"]["name"] == ...)`). Returns parsed arguments; returns `None` on failure.

### Tool Execution (`process_tool_calls`)
A self-contained execution engine that extracts JSON-formatted parameters from `arguments`, resolves missing settings to defaults (`{"project_settings": False, "async": False}`), and recursively applies nested tool configurations via `tool.get("settings")`. Errors are captured as structured AIMessage payloads to avoid silent failures.

---

## Message Preprocessing & Standardization

The `convert_message_to_openai()` method handles dual-format input for LLM compatibility:
- **Image Types**: Parses JSON-formatted image metadata from `gpt_message.content` (e.g., base64/URL strings wrapped in arrays) and converts to OpenAI-compatible format.
- **Standard Messages**: Translates `AIMessage` → "assistant", `HumanMessage" → "user", with graceful fallback on deserialization errors (logged via the internal AI logger).

The `preparer_messages_to_openai()` method ensures system messages appear at the start of conversations by prepending project/system-level prompts to user inputs, and supports batch message compression when `settings.merge_messages` is enabled.

---

## Wallet & Limit Enforcement

The `_preflight_limit_check()` workflow intercepts every chat completion attempt before API dispatch:
- Retrieves model pricing tiers via `_get_model_cost()` (extracting input/output CXJcoin costs from LLM settings).
- Invokes `check_user_wallet(user=self.user)` when costs are positive. This guarantees budget-aware access and prevents unauthorized premium calls, with wallet-based throttling for high-frequency tenants.

---

## Analytics & Observability

### Token Tracking (`_record_usage`)
Tracks token consumption across provider-provided usage metadata (from streaming chunks) or manual fallback calculation:
- Extracts `prompt_tokens`/`completion_tokens` from `usage_info`, or computes them via native library calls (`count_tokens()`).
- Records per-user, per-project metrics including CXJcoin cost attribution, request timestamps, tags array, and optional session identifiers.

### Tool Analytics (`_record_tool_usage`)
Executed post-execution to capture tool performance:
- Time delta from invocation start → duration_seconds.
- Success/failure flag with error message payload on exceptions.
- Chat/session context propagation to correlate tool chains across requests.

---

## Error Handling & Cancellation Policies

**Exception Strategy**: Encapsulated raw logging handles network, rate-limit, and timeout scenarios gracefully:
- Non-fatal errors are logged via `RawAILogger` (configurable path) with full error payloads; internal Python exceptions surface for higher-level recovery.
- Rate limit errors from OpenAI trigger the client's built-in retry mechanisms, while streaming is safely interrupted across chunk processing.

**Cancellation**: The `cancellation_token` pattern allows downstream calls to signal early termination:
- Checks `if cancellation_token and cancellation_token.is_cancelled` during streaming loops.
- Closes underlying OpenAI streams, clears buffers, raises `CancelledError` with a contextual message for parent call stacks.

---

## API Specifics & Rate Limits

**Streaming**: Enabled via `"stream": True` in all chat calls. Utilizes `stream_options: {"include_usage": True}` to harvest token-level usage on chunks without full buffering. Callbacks can intercept raw partial content at any step (useful for user-facing streaming displays).

**Rate Limiting & Budget Controls**: OpenAI default tier limits are enforced by the provider; Codx Junior adds wallet-based guardrails via `_preflight_limit_check()`. Project-level settings (`settings.get_llm_settings(llm_model)`) allow dynamic configuration of per-model rates, max_tokens, and context window sizes.

---

## Image Generation & Embeddings Operations

### `generate_image()`
A quick-draft endpoint for image synthesis using DALL-E 3:
- Fixed parameters: `1024x1024`, standard quality, single output (`n=1`). Prompt injection directly from the caller's text.

### `embeddings()`
Returns a callable function that wraps the OpenAI embedding API:
- Accepts a string input and produces high-dimensional vector arrays per token in batches. Supports custom LLM settings for embeddings (endpoint, model, key) via `settings.get_embeddings_settings()`. Useful for similarity search pipelines downstream.

---

## Raw Logging & Request/Response Tracing

The `_raw_log_request/_raw_log_response` / `_raw_log_error()` triad enables real-time audit trails:
- Request logging captures OpenAI payloads and auxiliary headers (tags, session IDs).
- Response logging includes finish reasons, tool call metadata, and duration deltas.
- Custom tags are propagated via `config` objects or request header injections (`request_headers.get("tags", "")`).

---

## System & User Context Propagation

The `_raw_log_ctx()` helper standardizes cross-request context tagging:
- Provider/model/base URL identifiers from LLM config.
- Project-level identifiers (`project_name`, `session_id`).
- Per-user context injection via `self.user.username` or an "anonymous" fallback when no user is bound to the thread.

Session and request identifiers flow through headers into callback systems, analytics events, and raw log entries, ensuring end-to-end traceability across tool chains.

---

## Profiling & Instrumentation

All public methods are wrapped with `profile_function` (from `profiler`). This enables runtime performance metrics for critical paths:
- Total execution duration per AI invocation.
- Latency breakdowns between API dispatch and final response. Useful for benchmarking streaming pipelines and tool calls against SLAs.

---

## Summary

Codx Junior's OpenAI integration layer provides enterprise-ready capabilities through modular singletons, comprehensive wallet checks (e.g., `_preflight_limit_check()`), context-aware streaming utilities, structured tool execution (`process_tool_calls`), and full observability via raw logging and token analytics. Developers can compose synchronous/async workflows with seamless session/request tracing across distributed microservices while leveraging project-specific LLM settings for granular budgeting control.

## Dependencies
**Imports from:** codx/junior/ai/ai_logger.py, codx/junior/ai/raw_logger.py, codx/junior/ai/cancellation.py, codx/junior/ai/wallet_check.py, codx/junior/settings.py, codx/junior/profiling/profiler.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/analytics/__init__.py, codx/junior/analytics/token_counter.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/ai/ai.py