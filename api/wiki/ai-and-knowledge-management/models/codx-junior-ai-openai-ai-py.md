# OpenAI API Client Documentation

The `OpenAI_AI` class serves as a unified wrapper client designed to interact with various OpenAI functionalities, including chat completions, image generation, and embeddings. It handles crucial infrastructure tasks such as managing API keys, checking user budgets, logging usage metrics, and raw request/response auditing.

## ⚙️ Initialization and Setup

The client is instantiated using the following parameters:

```python
__init__(self, settings: CODXJuniorSettings, llm_model: str = None, user: CodxUser = None, system: str = None)
```

**Parameters:**

*   `settings`: Configuration settings required to determine API endpoints and billing information (Source: `OpenAI_AI.__init__`).
*   `llm_model` (Optional): Specifies the target LLM model.
*   `user` (Optional): The authenticated user, used for fetching credentials or logging per-user data.
*   `system`: Optional system prompt content applied across requests (Source: `OpenAI_AI.__init__`).

Upon initialization, the client sets up an instance of `openai.OpenAI`, utilizing API keys and base URLs derived from the provided settings.

## 🔗 Core Chat Completion Functionality

The class provides both synchronous (`chat_completions`) and asynchronous (`a_chat_completions`) methods for retrieving chat completions. Both methods include handling for streaming responses, system priming, and tool usage.

### Synchronous Streaming (`chat_completions`)

This method performs the AI request in a blocking manner suitable for synchronous workflows.

**Key Features:**
*   **Budget Check:** Runs `_preflight_limit_check` to ensure sufficient user wallet funds before executing the call (Source: `OpenAI_AI.chat_completions`).
*   **Logging:** Logs requests, responses, errors (`_raw_log_*`), and records usage metrics upon completion (Source: `_raw_log_request`, `_record_usage`).
*   **Input Preparation:** Handles system messages and user history by converting structured `AIMessage` or `HumanMessage` Python objects into OpenAI message dictionary formats (`preparer_messages_to_openai`) (Source: `OpenAI_AI.preparer_messages_to_openai`).

### Asynchronous Tool-Enabled Streaming (`a_chat_completions`)

This asynchronous method is designed for complex interactions involving external functions and tool calls, supporting modern multi-turn chat flows.

**Key Capabilities:**
1.  **Tool Integration:** Accepts a list of `tools` (Source: `config.get("tools", [])`). If tools are present, the client marshals them into the request.
2.  **State Management & Tool Execution:** During streaming, if the model output indicates tool calls (`finish_reason == 'tool_calls'`), the method internally intercepts these calls and processes them using `await self.process_tool_calls` (Source: `OpenAI_AI.a_chat_completions`).
3.  **Recursive Calling:** After processing tools, the client automatically updates the message history with tool outputs (`AIMessage`) and re-runs a follow-up chat completion call to continue generation, propagating the current request ID as the parent (Source: `OpenAI_AI.a_chat_completions`).

### Tool Processing Flow (`process_tool_calls`)

This function acts as the executor for tools suggested by the model.

*   **Input:** Receives structured data containing the tool name and arguments from the LLM response.
*   **Execution:** Maps the tool name back to the defined `self.tools` dictionary (Source: `OpenAI_AI.process_tool_calls`).
*   **Output:** Executes the associated callable, passing parsed parameters (`params`), and returns a standardized format that OpenAI expects for function call results ("function_call_output") (Source: `OpenAI_AI.process_tool_calls`).

## 🛠️ Specialized API Methods

### Image Generation (`generate_image`)
This method is dedicated to generating images using the DALL-E model. It accepts a text prompt and defaults to popular parameters like size and quality (Source: `OpenAI_AI.generate_image`).

### Embedding Creation (`embeddings`)
Provides functionality to generate vector embeddings for arbitrary content strings by utilizing a configurable separate OpenAI client instance specific to embedding tasks (Source: `OpenAI_AI.embeddings`).

## 📊 Auxiliary and Utility Methods

| Method | Purpose | Details | Document Source Section |
| :--- | :--- | :--- | :--- |
| `_record_usage` | **Usage Tracking:** Records detailed analytics on API calls, including input/output tokens (`input_tokens`, `output_tokens`), duration, model cost (in coin equivalents), and usage type (provider native vs. estimated) (Source: `OpenAI_AI._record_usage`). | Receives explicit token counts if available from the provider's response or falls back to calling `count_tokens` for estimation. |
| `_preflight_limit_check` | **Authorization Check:** Performs a budget check against the user's account before initiating any expensive API call (Source: `OpenAI_AI._preflight_limit_check`). | Raises an exception if insufficient funds are detected (`InsufficientFundsError`). |
| `raw_log_*` methods | **Auditing:** Methods like `_raw_log_request`, `_raw_log_response`, and `_raw_log_error` ensure detailed logging of the entire API interaction cycle (inputs, outputs, timings, metadata) into a dedicated raw logger instance (`self.raw_logger`) for deep auditing capabilities. | Used internally within primary chat methods. |

## Dependencies
**Imports from:** codx/junior/ai/ai_logger.py, codx/junior/ai/raw_logger.py, codx/junior/ai/cancellation.py, codx/junior/ai/wallet_check.py, codx/junior/settings.py, codx/junior/profiling/profiler.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/analytics/__init__.py, codx/junior/analytics/token_counter.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/ai/ai.py