# AI Module Documentation

The `AI` class serves as the central management hub for AI interactions, handling routing between different providers, message management, caching, and automated recovery for missing models.

## Overview
The `AI` system is designed to facilitate both synchronous and asynchronous interactions with Large Language Models (LLMs). It supports image generation, chat completions, and embedding vector creation.

**Architecture:**
*   **Routing:** The system routes requests based on the configured provider (e.g., `OpenAI_AI`).
*   **Logging:** Integration with `AILogger` allows for tracking AI interactions when enabled in `CODXJuniorSettings`.

## Core Functionality

### Chat Interactions
The module provides two primary methods for generating AI responses:
*   **`chat()`**: Synchronous interface for processing user inputs and history.
*   **`a_chat()`**: Asynchronous interface for high-performance, non-blocking completions.

Both methods accept a list of messages (supporting `AIMessage`, `HumanMessage`, and `SystemMessage`) and support optional parameters such as `max_response_length`, `tools`, and custom `headers`.

#### Caching
Both `chat` and `a_chat` support a caching mechanism. When enabled, the system uses an MD5 hash of the message history (`messages_md5`) to retrieve stored responses, reducing redundant API calls.

#### Error Handling and Recovery
The system includes logic to detect `model_not_found` errors. If the provider is set to "ollama" and a model is missing, the system automatically triggers `_pull_ollama_model` to attempt a recovery by pulling the required model from the specified `api_url`.

### Image Generation
The `image(prompt: str)` method provides a simple interface to generate images based on a text description, delegating the operation to the configured LLM provider.

### Embeddings
The `embeddings(content)` method generates dense embedding vectors for input text.
*   **Single String:** Returns a `List[float]`.
*   **List of Strings:** Returns a `List[List[float]]`.
The method intelligently delegates to either `embed_documents` or `embed_query` depending on the input type and the capabilities of the underlying model.

## Configuration and Initialization
The `AI` class is initialized with:
*   **`settings`**: Configuration object (`CODXJuniorSettings`).
*   **`llm_model`**: Optional specific model identifier.
*   **`user`**: Optional `CodxUser` object for user-contextualized interactions.
*   **`system`**: Optional system-level parameters.

The system dynamically creates the appropriate chat and embedding clients during initialization based on these settings.

## Utility Functions
*   **`messages_md5(messages)`**: Generates a unique hash for conversation history to facilitate caching.
*   **`serialize_messages(messages)`**: Converts list of `Message` objects into a JSON-compatible format for storage.

## References
*   **Class Definition**: `class AI`
*   **Error Recovery**: `_is_model_not_found_error`, `_handle_model_not_found`, and `_pull_ollama_model`
*   **Chat Implementation**: `chat()` and `a_chat()`
*   **Embeddings**: `embeddings()`
*   **Serialization**: `serialize_messages()` and `messages_md5()`

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/ai/openai_ai.py, codx/junior/ai/ai_logger.py, codx/junior/ai/cancellation.py, codx/junior/profiling/profiler.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/context.py