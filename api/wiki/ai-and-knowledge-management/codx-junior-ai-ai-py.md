## AI Interface Management (`AI` Class)

The `AI` class serves as a comprehensive wrapper and router for all Artificial Intelligence interactions within the application, managing connections to various large language model (LLM) providers (such as OpenAI or Vllm). It provides unified interfaces for chat completion, image generation, embedding vector creation, and robust error handling, including automatic model management.

### Initialization

```python
def __init__(self, 
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None,
)
```

Initializes the `AI` client instance. It sets up internal components for logging (`AILogger`), caching, and initializes both synchronous (`self.llm`) and asynchronous (`self.a_llm`) chat model clients based on the provided settings and LLM model configuration.

*   **Parameters:**
    *   `settings` (`CODXJuniorSettings`): Global application and AI configuration settings.
    *   `llm_model` (`Optional[str]`): The specific LLM identifier to be used across all calls.
    *   `user` (`Optional[CodxUser]`): Contextual information about the current user.
    *   `system` (`Optional[str]`): System-level instructions or context for the AI model.

***

### Public Methods

#### `image(self, prompt: str)`

Generates a visual representation (image) based on a supplied textual description. This method delegates to the underlying LLM client configured for image generation.

*   **Parameters:**
    *   `prompt` (`str`): The detailed text prompt describing the desired image.
*   **Returns:**
    *   `str`: The generated image data or URL.

#### `log(self, message: str, *args: Any)`

Logs a structured message detailing AI interactions to the logger if the logging feature is enabled in the settings. This utilizes an internal dedicated logger (`AILogger`).

*   **Parameters:**
    *   `message` (`str`): The main message string (supports Python logging format arguments).
    *   `args` (`Any`): Optional arguments to fulfill lazy string formatting in the `message`.

#### `chat(self, messages: Optional[List[Message]] = None, prompt: Optional[str] = None, *, max_response_length: Optional[int] = None, callback: Optional[Callable] = None, tools: Optional[List[str]] = None, headers: Optional[Dict[str, Any]] = None, cancellation_token: Optional[CancellationToken] = None)`

Executes a synchronous chat completion request. This method implements sophisticated features including response caching and proactive error handling for model unavailability.

*   **Parameters:**
    *   `messages` (`Optional[List[Message]]`): The history of messages to feed into the LLM. If `None`, an empty list is used.
    *   `prompt` (`Optional[str]`): An optional new prompt that will be appended to the message history.
    *   `max_response_length` (`Optional[int]`): Maximum tokens allowed for the response (unused in function signature but intended for control).
    *   `callback` (`Optional[Callable]`): Optional callback function executed during the completion process.
    *   `tools` (`Optional[List[str]]`): A list of tools available to the model, enabling function calling.
    *   `headers` (`Optional[Dict[str, Any]]`): Custom HTTP headers to pass with the API request.
    *   `cancellation_token` (`Optional[CancellationToken]`): Token used to signal premature cancellation of the request.
*   **Behavior Highlights:**
    1.  **Caching:** Before calling the LLM, it generates an MD5 hash key based on the message history. If a cached response exists for this key (`self.cache`), it returns the stored result immediately.
    2.  **Model Failure Handling (Ollama):** If an explicit `model_not_found` error is detected during execution:
        *   It calls the internal method `_handle_model_not_found`.
        *   If the provider is "ollama," it attempts to automatically pull the required model using `_pull_ollama_model()`.
        *   The request then retries after a successful model pull.
    3.  **Error Handling:** If retrieval fails or if the provider is not Ollama, a non-retryable `RuntimeError` is raised detailing the failure.
*   **Returns:**
    *   `List[Message]`: A list of messages representing the transaction, including the final AI response.

#### `a_chat(self, messages: Optional[List[Message]] = None, prompt: Optional[str] = None, *, max_response_length: Optional[int] = None, callback: Optional[Callable] = None, tools: Optional[List[str]] = None, headers: Optional[Dict[str, Any]] = None, cancellation_token: Optional[CancellationToken] = None)`

Asynchronously executes a chat completion request. This method mirrors the functionality of `chat()` but is designed for use in an asynchronous context (`async`), supporting caching and robust model failure handling (including automatic Ollama model pulling and retries).

*   **Parameters:** Matches `chat()` parameters.
*   **Returns:**
    *   `awaitable`: A list of messages including the final AI response.

#### `embeddings(self, content: Union[str, List[str]])`

Generates dense vector representations (embeddings) for provided input text. The method automatically determines if the input is a single string or a collection of strings and delegates to the configured embeddings model (`self.embeddings_model`).

*   **Parameters:**
    *   `content` (`Union[str, List[str]]`): One or more text strings that need to be embedded.
*   **Behavior:**
    *   If `content` is a single string (`str`), it uses the embed query function and returns a single vector (`List[float]`).
    *   If `content` is a list of strings (`list`), it processes the entire batch, typically using an `embed_documents` method, and returns a list of vectors (`List[List[float]]`).
*   **Returns:**
    *   `Any`: A single embedding vector or a list of embedding vectors.

***

### Internal Mechanisms & Utilities

#### Model Management and Error Handling

The class implements the following utilities to manage model availability:

1.  **Model Not Found Detection (`_is_model_not_found_error`)**: Inspects an exception message or type to determine if it specifically indicates a `model_not_found` error, catering to various API response formats (e.g., `"model_not_found"`, `"model 'ollama/xxx' not found"`).
2.  **Ollama Pulling (`_pull_ollama_model`)**: If an Ollama-related model is detected as missing, this method constructs and executes a POST request to the configured `api_url` endpoint (e.g., `/api/pull`) to stream and download the necessary LLM weights, logging progress throughout the process.
3.  **Model Failure Handling (`_handle_model_not_found`)**: Orchestrates the workflow upon receiving a model not found error. If the provider is Ollama, it initiates `_pull_ollama_model()` and then retries the original chat request, ensuring operational continuity where possible.

#### Message Serialization (For Caching)

*   `messages_md5(messages: List[Message])`: Generates a unique MD5 hash key based on all message contents in the conversation history, used to ensure cache lookups are accurate for repeated chats.
*   `serialize_messages(messages: List[Message])`: Converts runtime `Message` objects into a standard JSON-compatible list of dictionaries before storage in the cache.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/ai/openai_ai.py, codx/junior/ai/ai_logger.py, codx/junior/ai/cancellation.py, codx/junior/profiling/profiler.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/context.py