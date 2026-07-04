# OpenAI_AI Class Reference

The `OpenAI_AI` class serves as a comprehensive wrapper around the OpenAI client library within the system. It provides standardized methods for interacting with large language models (LLMs), handling core functionalities like chat completions, image generation, and embeddings. Crucially, it encapsulates sophisticated features including usage tracking (`_record_usage`), granular API logging (`_raw_log_*` methods), project configuration adherence, and pre-call wallet checking (`_preflight_limit_check`).

## Initialization and Setup

The class is instantiated with configuration settings required for connectivity and context. It requires `settings` (of type `CODXJuniorSettings`) to determine the API endpoint, model name, and authentication keys.

**Constructor:**
```python
__init__(self, settings: CODXJuniorSettings, llm_model: str = None, user: CodxUser = None, system: str = None)
```

| Parameter | Type | Description | Internal Usage/Reference |
| :--- | :--- | :--- | :--- |
| `settings` | `CODXJuniorSettings` | Global application settings. Used to fetch LLM-specific configurations (API URLs, keys, costs). | Referenced in `__init__` and multiple helper methods. |
| `llm_model` | `str` | Optional model name override for the current session. | Sets `self.model`. |
| `user` | `CodxUser` | The active user object. Used to derive API keys and display names for logging/authorization checks. | Referenced in `__init__`, `_raw_log_ctx`, and `_preflight_limit_check`. |
| `system` | `str` | An optional system prompt content used alongside the configured system message from settings. | Used in `preparer_messages_to_openai`. |

## Core Chat Completion Methods

These methods handle the primary interaction with the LLM for conversational or task-oriented prompts and support streaming, usage recording, and tool integration. Because they handle state (like logging callbacks), asynchronous versions are provided for modern Python development.

### 1. `chat_completions` (Synchronous)
This is the synchronous method for fetching chat completions (`@profile_function`).

**Usage:**
```python
chat_completions(messages: list, config: dict = {})
```

*   **Input Messages:** Takes a list of messages (`messages`) which must be formatted or processed via `preparer_messages_to_openai`.
*   **Config Dictionary:** A dictionary containing optional parameters such as `"cancellation_token"`, `"callbacks"`, `"headers"`, and importantly, the `"parent_request_id"` if called from a tool-call response.

**Workflow Highlights (Referencing `chat_completions`):**
1.  **Pre-flight Check:** Calls `_preflight_limit_check()` to ensure sufficient user wallet funds are available.
2.  **Message Preparation:** The inputs are processed into the format required by OpenAI (`openai_messages`) via `preparer_messages_to_openai`.
3.  **Streaming & Calling:** It streams content chunks, allowing for immediate display via provided callbacks.
4.  **Error Handling:** Catches exceptions and utilizes `_raw_log_error` to log the final failure state with `STATUS_ERROR`, or logs a specific termination event using `CancelledError` (`STATUS_CANCELLED`).
5.  **Post-Completion Processing:** After streaming finishes, it calls `_raw_log_response` and `_record_usage` are called to track tokens consumed.

### 2. `a_chat_completions` (Asynchronous)
This is the asynchronous version (`@profile_function`) of `chat_completions`, essential for concurrent API operations. It extends the sync method by adding robust support for function/tool calling within an execution pipeline.

**Usage:**
```python
await a_chat_completions(messages: list, config: dict = {})
```

**Advanced Tool Flow (Tool Calling):**
When `a_chat_completions` detects that the model outputs tool calls (`choice.delta.tool_calls`), it performs the following steps automatically:
1.  It gathers all requested tool information into `all_tool_calls`.
2.  It executes the necessary tools by calling `await self.process_tool_calls(tool_call_data)`.
3.  The results are converted back into an AI message and appended to `messages`.
4.  Crucially, it recursively calls `self.chat_completions` (synchronously) using the current request ID as the parent ID (`child_config = {**config, "parent_request_id": request_id}`) to integrate tool results into the final LLM response.

## Supporting Functionality and Utilities

### Tool Call Execution
**Method:** `process_tool_calls(self, tool_call_data)`
Handles the execution of a single tool based on data provided by the model's output.

1.  It parses the tool name (`func_name`) and arguments JSON from the input `tool_call_data`.
2.  It retrieves the corresponding callable tool definition from `self.tools`.
3.  The function is executed:
    *   If the tool defines project settings, those are passed to the execution context ($\text{params}[\text{"settings"}]$).
    *   The call handles both synchronous and asynchronous tools (`if settings["async"]: content = await content`).
4.  It formats the result into a standardized output dictionary usable by the LLM: `{"type": "function_call_output", "call_id": tool_call_data["id"], "output": tool_response}`.

### Image Generation
**Method:** `generate_image(self, prompt)`
A specialized method for creating images using DALL-E 3 (`@profile_function`).

*   **Input:** A descriptive string `prompt`.
*   **Output:** The URL of the generated image.
*   **Configuration:** Fixed model ("dall-e-3"), size ("1024x1024"), quality, and count (1).

### Embeddings Generation
**Method:** `embeddings(self)`
Generates vector embeddings for a given piece of text content (`@profile_function`).

*   This method uses dedicated credentials retrieved via `settings.get_embeddings_settings()`, allowing it to use a separate API key and base URL from the primary LLM client setup.
*   **Input:** An embedded function expecting a single string argument: `content: str`.
*   **Output:** A list of floating-point numbers representing the embedding vector (`List[float]`).

## Internal Mechanism Documentation

### 🔑 Resource Management and Security
*   **Wallet Check:** Before any chat completion, `_preflight_limit_check()` runs a wallet check using `check_user_wallet()` if the model has defined costs.
*   **Usage Tracking (`_record_usage`):** Tracks token consumption (input/output tokens) and elapsed duration. It calculates both native usage data and falls back to `count_tokens(text, model)` if provider-specific usage info is missing. This information is passed to the analytics backend using `Analytics.record_token_usage`.

### ⚙️ Logging and Metrics
The class implements robust logging across three levels:
1.  **`log(msg)`:** General informational output via `self.ai_logger`, activated if AI logging is enabled in settings.
2.  **Request Logging (`_raw_log_request`)**: Logs the entire outgoing request payload (messages and parameters) using `RawAILogger`.
3.  **Response Logging (`_raw_log_response`)**: Logs the final response details after streaming completes, including finish reason, duration, and tool calls.
4.  **Error Logging (`_raw_log_error`)**: Used to log any operational failure, setting the status to `STATUS_ERROR` or `STATUS_CANCELLED`.

## Dependencies
**Imports from:** codx/junior/ai/ai_logger.py, codx/junior/ai/raw_logger.py, codx/junior/ai/cancellation.py, codx/junior/ai/wallet_check.py, codx/junior/settings.py, codx/junior/profiling/profiler.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/analytics/__init__.py, codx/junior/analytics/token_counter.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/ai/ai.py