# Wiki Documentation: AI Core Module

## Overview
The `AI` class functions as the central orchestration layer for managing artificial intelligence interactions, request routing, caching, and recovery mechanisms within the Codx Junior framework. It abstracts lower-level LangChain message structures and provides a unified interface for synchronous/asynchronous chat completions, embeddings generation, and image synthesis.

## Architecture & Provider Routing
- **Dynamic Instantiation**: The class uses factory methods to route requests to underlying provider implementations (`OpenAI_AI`) based on configuration. This applies to both synchronous (`create_chat_model`) and asynchronous (`create_a_chat_model`) execution targets `[Ref: def create_chat_model()]`, `[Ref: def create_a_chat_model()]`.
- **Provider Resolution**: The `_get_provider()` helper safely extracts the active provider identifier by checking for attribute access on `llm_settings` or dictionary key lookup, defaulting to an empty string if absent `[Ref: def _get_provider()]`.

## Class Initialization & State Management
The constructor (`__init__`) establishes the operational context and initializes core state variables:
- **Parameters**: Accepts `settings`, optional `llm_model`, `user`, and `system` parameters `[Ref: class AI.__init__]`.
- **Configuration Parsing**: Retrieves dynamic LLM configurations via `settings.get_llm_settings(llm_model=llm_model)` stored in `self.llm_settings` `[Ref: self.llm_settings]`.
- **Execution Callables**: Instantiates sync (`self.llm`) and async (`self.a_llm`) chat callables by invoking their respective factory methods `[Ref: self.llm / self.a_llm]`.
- **Caching & Logging**: Initializes `self.cache` (boolean or dict) and `self.ai_logger` for conditional logging `[Ref: Cache State]`, `[Ref: Logger Configuration]`.
- **Lazy Embeddings**: Defers embeddings model instantiation until first use via `self.embeddings_model` to prevent premature resource allocation `[Ref: Lazy Embeddings Init]`.

## Chat Execution (Synchronous & Asynchronous)
The `chat()` and `a_chat()` methods share an identical execution pipeline:
1. **Input Normalization**: Ensures `messages`, `tools`, and `headers` are initialized as empty lists/dicts if not provided. Appends `prompt` as a `HumanMessage` when present `[Ref: Message Construction]`.
2. **Cache Lookup**: Generates a cache key using `messages_md5(messages)`. If caching is active and the key exists, retrieves the stored AI response directly from JSON data `[Ref: Cache Hit Logic]`.
3. **Request Dispatch**: Invokes `self.llm()` or `self.a_llm()` with a config dictionary containing callbacks, headers, tools, and optional `cancellation_token` `[Ref: Request Execution]`.
4. **Cancellation Handling**: Explicitly catches and propagates `CancelledError` to respect client-side abort requests `[Ref: Cancellation Handling]`.
5. **Error Recovery**: Intercepts standard exceptions and checks for model-not-found conditions. If detected, triggers automatic provider-specific recovery (Ollama model pulling) before executing a single retry attempt `[Ref: Automatic Model Recovery]`.
6. **Cache Persistence**: On success, serializes the conversation history and response content into JSON format and stores it in `self.cache` using the MD5 key `[Ref: Cache Storage Logic]`.

## Embeddings & Image Generation
- **Embeddings (`embeddings()`)**: Generates dense vector representations for text inputs. Handles both single strings and lists of strings by routing to `embed_documents()` or `embed_query()`. Automatically falls back between methods based on available client attributes `[Ref: def embeddings()]`.
- **Image Generation (`image()`)**: Delegates synchronous image synthesis directly to the underlying LLM provider's `generate_image()` interface `[Ref: def image()]`.

## Automatic Error Detection & Recovery
The module implements a dedicated recovery workflow for missing local models:
- **Pattern Matching (`_is_model_not_found_error()`)**: Inspects exception strings for specific patterns including `"model_not_found"`, `"model not found"`, and API-native `"not_found_error"` types `[Ref: def _is_model_not_found_error()]`.
- **Automated Pulling (`_pull_ollama_model()`)**: Extracts the target model name (stripping `ollama/` prefix if present), isolates the base URL by removing path components from `api_url`, and streams progress via HTTP POST to `/api/pull`. Raises a descriptive `RuntimeError` on failure `[Ref: def _pull_ollama_model()]`.
- **Recovery Trigger (`_handle_model_not_found()`)**: Validates the active provider type. Executes the pull routine only for Ollama environments, wrapping any upstream failures in a runtime exception `[Ref: def _handle_model_not_found()]`.

## Utility & Serialization Functions
- **`log()`**: Conditionally writes informational messages to `ai_logger` only when `get_log_ai()` confirms logging is enabled `[Ref: def log()]`.
- **`get_openai_chat_client()`**: Instantiates the underlying provider client and returns it for direct access `[Ref: def get_openai_chat_client()]`.
- **`create_embeddings_model()`**: Returns a fresh embeddings instance from the provider layer `[Ref: def create_embeddings_model()]`.
- **`messages_md5()`**: Concatenates string representations of message contents and produces an MD5 hexadecimal digest for deterministic cache key generation `[Ref: def messages_md5()]`.
- **`serialize_messages()`**: Converts message objects into JSON-compatible dictionaries containing the original type name and content string `[Ref: def serialize_messages()]`.

## External Dependencies
The module relies on the following libraries and framework components as defined in its imports `[Ref: Top-level Imports]`:
- **LangChain**: `BaseChatModel` base class, `AIMessage`, `HumanMessage`, `SystemMessage` for structured conversation history.
- **Codx Framework**: `CODXJuniorSettings` for configuration management, `CodxUser` for interaction context, `AILogger` and `CancellationToken`/`CancelledError` for operational utilities.
- **Standard Library & Third-Party**: `logging`, `hashlib`, `json`, `requests` (for streaming API pulls), `urllib.parse.urlparse` (for URL normalization), and `profile_function` decorator from the internal profiling suite.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/ai/openai_ai.py, codx/junior/ai/ai_logger.py, codx/junior/ai/cancellation.py, codx/junior/profiling/profiler.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/context.py