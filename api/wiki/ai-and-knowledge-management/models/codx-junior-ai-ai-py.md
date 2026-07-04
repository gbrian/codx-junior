# AI Service Module

The `AI` class serves as the main entry point for managing all interactions with various Artificial Intelligence providers, providing robust routing, caching, error handling, and specialized functions like image generation and embeddings.

## Initialization and Setup

### `__init__(self, settings: CODXJuniorSettings, llm_model: Optional[str] = None, user: Optional[CodxUser] = None, system: Optional[str] = None)`

Initializes the AI service by setting up connections to underlying LLMs, embeddings models, and logging utilities. It determines the appropriate client based on provider configuration (as described in `create_chat_model` and `create_embeddings_model`).

**Parameters:**
*   `settings` (`CODXJuniorSettings`): Configuration settings for AI services.
*   `llm_model` (`Optional[str]`): The specific Large Language Model name to use (e.g., "gpt-4").
*   `user` (`Optional[CodxUser]`): The user initiating the call.
*   `system` (`Optional[str]`): System-level parameters or persona instructions for the LLM.

**Internal Components Initialized:**
*   **LLMs:** Creates both synchronous (`self.llm`) and asynchronous (`self.a_llm`) chat completion clients using `create_chat_model` and `create_a_chat_model`, respectively, which typically route to an internal provider like `OpenAI_AI`.
*   **Embeddings:** Initializes the embeddings model client via `create_embeddings_model()`.

## Core Chat Functionality

### `chat(self, messages: Optional[List[Message]] = None, prompt: Optional[str] = None, *, max_response_length: Optional[int] = None, callback: Optional[Callable] = None, tools: Optional[List[str]] = None, headers: Optional[Dict[str, Any]] = None, cancellation_token: Optional[CancellationToken] = None) -> List[Message]`

Performs a synchronous chat completion request. This method handles conversation history, integrates function calling capabilities (tools), and includes crucial logic for caching responses and handling connection failures.

**Parameters:**
*   `messages`: History of messages (`List[AIMessage | HumanMessage | SystemMessage]`). If provided, the prompt is appended to this list before processing.
*   `prompt`: An optional string that will be added as a `HumanMessage` to the conversation history.
*   **Keyword Arguments:**
    *   `max_response_length`: Maximum tokens allowed in the response.
    *   `callback`: An optional callback function for streaming responses.
    *   `tools`: A list of function names/descriptions available for tool calling (function calling).
    *   `headers`: Custom HTTP headers to include with the LLM API request.
    *   `cancellation_token`: Token used to cancel an ongoing completion request.

**Behavior:**
1.  **Caching Check:** Determines a unique MD5 hash (`messages_md5`) based on the message history and checks `self.cache`. If a matching result exists, it returns a cached response immediately.
2.  **API Call:** Calls the synchronous chat completions client (`self.llm`).
3.  **Error Handling (Model Not Found):** If an exception occurs that matches a model not found error (`model_not_found`, `model not found`), it triggers the recovery process:
    *   It calls `_handle_model_not_found(exc)`. This function checks the provider type. If the provider is **Ollama**, it attempts to pull the missing model via `_pull_ollama_model()`.
    *   If pulling succeeds, it automatically retries the LLM call using the updated client.
4.  **Caching Update:** Upon a successful response, the content and message history are serialized (`serialize_messages`) and saved to `self.cache` under the calculated MD5 key.

### `a_chat(self, messages: Optional[List[Message]] = None, prompt: Optional[str] = None, *, max_response_length: Optional[int] = None, callback: Optional[Callable] = None, tools: Optional[List[str]] = None, headers: Optional[Dict[str, Any]] = None, cancellation_token: Optional[CancellationToken] = None) -> List[Message]`

Performs an asynchronous version of the chat completion request. It mimics all the functional behavior of `chat()`, including caching and automatic model recovery/retries for `model_not_found` errors, but utilizes `await self.a_llm(...)`.

## Specialized AI Capabilities

### `image(self, prompt: str) -> str`

Generates an image URL or data based on a descriptive string prompt. This delegates the request to the configured LLM client via its specialized `generate_image()` method.

**Parameters:**
*   `prompt`: The textual description used for image generation.
**Returns:** Generated image content (e.g., a URL or data).

### `embeddings(self, content: Union[str, List[str]]) -> Any`

Generates dense embedding vectors for the provided text content using the configured embeddings model client.

**Parameters:**
*   `content`: A single string (`str`) or a list of strings (`List[str]`).

**Behavior:**
*   If `content` is a **list**, it uses the batch method (e.g., `embed_documents`).
*   If `content` is a **single string**, it uses the query method (e.g., `embed_query`).
*   Returns either a single vector (`List[float]`) or a list of vectors (`List[List[float]]`).

### `log(self, message: str, *args: Any) -> None`

A utility function that logs operational messages using the internal AI Logger (`self.ai_logger`), but only if logging is enabled in the application settings (`settings.get_log_ai()`) (Source: `AI.log`).

## Model Recovery and Provider Handling

### `_handle_model_not_found(self, exc: Exception) -> None`

This internal handler is invoked when a `model_not_found` error occurs during chat completion.
1.  It checks if the AI provider (`provider_type`) is explicitly set to `"ollama"`.
2.  If it is Ollama, it calls `_pull_ollama_model()` to attempt downloading the model.
3.  If the provider is not Ollama (or if pulling fails), it raises a `RuntimeError`, signaling failure.

### `_pull_ollama_model(self) -> None`

A specialized method for Ollama connectivity. If a model is missing, this function connects to the configured Ollama API URL and streams the pull request using `requests.post` to download the required model locally. The progress status is logged during this process.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/ai/openai_ai.py, codx/junior/ai/ai_logger.py, codx/junior/ai/cancellation.py, codx/junior/profiling/profiler.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/context.py