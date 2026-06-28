# AI Interaction Manager

The `AI` class serves as the central routing and management layer for all AI interactions within the system. It abstracts away connectivity differences between various Large Language Model (LLM) providers, handling both synchronous and asynchronous chat completions, image generation, and vector embedding tasks.

## Initialization

The `AI` instance is initialized with site configurations and potential custom parameters.

### Constructor Signature
```python
__init__(
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None,
)
```

**Parameters:**

*   `settings`: The primary configuration object (`CODXJuniorSettings`) containing global project settings.
*   `llm_model`: An optional specific model name to be used (e.g., `"gpt-4"`). This overrides or specifies the role of the `settings`.
*   `user`: Optional information about the current user (`CodxUser`).
*   `system`: Optional system-level prompt or parameters applied to all AI calls.

**Internal Logic:**
Upon initialization, the class sets up connections for:
1.  Synchronous chat completion (`self.llm`).
2.  Asynchronous chat completion (`self.a_llm`).
3.  Embedding vectors (`self.embeddings_model`), which uses settings from `settings.get_embeddings_settings`.

## Core Functionality

### Chat Completion (Synchronous)

The core method for text-based conversations in a synchronous manner, handling message history and context.

**Method:** `chat()`
**Signature:**
```python
@profile_function
def chat(
    messages: Optional[List[Message]] = None,
    prompt: Optional[str] = None,
    *,
    max_response_length: Optional[int] = None,
    callback: Optional[Callable] = None,
    tools: Optional[List[str]] = None,
    headers: Optional[Dict[str, Any]] = None,
    cancellation_token: Optional[CancellationToken] = None,
) -> List[Message]:
```

**Parameters:**

*   `messages`: A list of preceding `Message` objects (the conversation history). If provided, a new `HumanMessage` created from `prompt` is appended.
*   `prompt`: An optional string prompt to append as the latest human input message.
*   `max_response_length`: Optional integer defining the maximum tokens allowed in the response.
*   `callback`: An optional function to receive intermediate callback outputs during generation.
*   `tools`: A list of available tools for potential function calling by the model.
*   `headers`: Custom HTTP headers for the underlying LLM request.
*   `cancellation_token`: An optional token used to cancel an ongoing completion gracefully.

**Features:**

1.  **Caching:** Implements local caching using MD5 hashing (`messages_md5`) based on the input message history. If a cache hit occurs and `self.cache` is active, the cached response content is immediately returned.
2.  **Retry/Recovery:** Wraps exception handling to detect Model Not Found errors. If an error occurs and the provider is configured for **Ollama**, it automatically attempts model pulling (`_handle_model_not_found`) before retrying the request.

### Chat Completion (Asynchronous)

Provides the same functionality as `chat()`, but designed for use in asynchronous contexts, utilizing `await`.

**Method:** `a_chat()`
**Signature:**
```python
@profile_function
async def a_chat(
    messages: Optional[List[Message]] = None,
    prompt: Optional[str] = None,
    *,
    max_response_length: Optional[int] = None,
    callback: Optional[Callable] = None,
    tools: Optional[List[str]] = None,
    headers: Optional[Dict[str, Any]] = None,
    cancellation_token: Optional[CancellationToken] = None,
) -> List[Message]:
```

**Parameters:** (Identical to `chat()`).
**Functionality:** Identical to `chat()`, but calls the asynchronous internal client (`self.a_llm`) and handles cached responses accordingly.

### Embedding Generation

Generates dense vector representations for text content.

**Method:** `embeddings()`
**Signature:**
```python
@profile_function
def embeddings(content: Union[str, List[str]]) -> Any:
```

**Parameters:**

*   `content`: The text to embed. Can be a single string or a list of strings.

**Return Value:**
*   If `content` is a string, returns a single vector (`List[float]`).
*   If `content` is a list of strings, returns a list of vectors (`List[List[float]]`), corresponding to the input order.

## Utility Methods

### Image Generation

Generates an image based on a textual description prompt.

**Method:** `image()`
**Signature:**
```python
@profile_function
def image(prompt: str) -> str:
```

**Parameters:**

*   `prompt`: The text describing the desired image.

**Return Value:** A string representing the generated image URL or data.

### Logging AI Activity

Logs operational messages related to AI interactions if logging is enabled in the settings.

**Method:** `log()`
**Signature:**
```python
def log(message: str, *args: Any) -> None:
```

**Parameters:**

*   `message`: The message string to be logged.
*   `args`: Optional arguments for lazy formatting of the message.

### Model Handling and Error Recovery

The class includes specialized logic for dealing with connectivity failures, particularly when using Ollama.

#### `_is_model_not_found_error(exc)`
A helper function used internally to inspect an exception object (`exc`). It robustly determines if the failure was caused by a model being unavailable, matching patterns like `"model not found"` or `"[]/api/pull"`.

#### `_handle_model_not_found(exc)`
This method executes when `chat()` or `a_chat()` catch a model-not-found error. If the detected provider is **Ollama**, it automatically triggers `_pull_ollama_model()`, attempting to pull the required model before retrying the main chat request.

#### `_pull_ollama_model()`
Dedicated to pulling models from Ollama when needed. It constructs the correct API URL for the Ollama base endpoint, streams the status updates via logging, and confirms successful deployment of the requested model.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/ai/openai_ai.py, codx/junior/ai/ai_logger.py, codx/junior/ai/cancellation.py, codx/junior/profiling/profiler.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/context.py