# AI Service Module

The `AI` class serves as the central manager for AI interactions, routing, and configuration within the `codx-api` project. It provides a unified interface for chat completions, image generation, and embedding creation, supporting different providers and handling automatic recovery for specific errors.

## Overview
The module integrates with multiple AI providers (such as OpenAI and Ollama) and utilizes the `AILogger` for tracking operations. It is designed to work with `langchain` message structures and supports both synchronous and asynchronous workflows.

### Key Components
*   **`AI` Class**: The primary controller for AI interactions.
*   **Provider Routing**: Dynamically resolves providers (e.g., "openai", "vllm", "ollama") based on configuration settings.
*   **Caching**: Supports MD5-based request/response caching to improve efficiency.
*   **Recovery Mechanisms**: Includes logic to automatically pull missing models for the Ollama provider if a "model not found" error occurs.

---

## Core Functionality

### Chat Completions
The class provides two methods for generating AI responses:
*   **`chat()`**: Synchronous chat functionality.
*   **`a_chat()`**: Asynchronous chat functionality.

Both methods accept a list of messages, optional prompts, and tools. They also support `CancellationToken` for aborting ongoing requests. If caching is enabled, the system first checks for an existing response in the cache before invoking the LLM provider.

### Model Recovery
If a request fails due to a `model_not_found` error, the `_handle_model_not_found` method is triggered. For providers configured as `ollama`, the system executes `_pull_ollama_model` to attempt a recovery, fetching the missing model from the configured `api_url` before retrying the original request.

### Embeddings
The `embeddings()` method generates dense vector representations of input content.
*   Supports both single `str` inputs (returning a `List[float]`) and `list` inputs (returning `List[List[float]]`).
*   Delegates to the configured embeddings model (initialized via `create_embeddings_model`).

### Image Generation
The `image()` method interfaces with the underlying LLM to generate image data or URLs based on a descriptive text prompt.

---

## Utility Functions
The module includes helper utilities for data processing:
*   **`messages_md5()`**: Generates an MD5 hash of the conversation history for cache key generation.
*   **`serialize_messages()`**: Converts `langchain` message objects into a JSON-compatible dictionary format.

---

## Configuration & Initialization
Initialization requires `CODXJuniorSettings`, an optional `llm_model`, a `CodxUser`, and optional system parameters. Configuration settings are accessed via the `settings` object to determine provider specifics, logging preferences, and embedding settings.

### References
*   **Class Definition**: `class AI`
*   **Model Recovery**: `_handle_model_not_found`, `_pull_ollama_model`
*   **Chat Methods**: `chat`, `a_chat`
*   **Embedding Logic**: `embeddings`
*   **Utilities**: `messages_md5`, `serialize_messages`

---
*Generated based on the provided project code structure.*

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/ai/openai_ai.py, codx/junior/ai/ai_logger.py, codx/junior/ai/cancellation.py, codx/junior/profiling/profiler.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/context.py