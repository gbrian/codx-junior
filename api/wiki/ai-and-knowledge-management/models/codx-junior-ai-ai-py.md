# AI Module Documentation

## Overview

The AI module serves as the main orchestrator for managing AI interactions with provider routing capabilities. It intelligently routes chat requests to either SmolAgent (async-native) or OpenAI_AI (legacy) based on global settings flags, while supporting advanced features like cancellation tokens, event listeners, and analytics traceability.

## Class: AI

### Purpose

The `AI` class is the primary interface for managing AI-powered conversations with configurable provider routing and comprehensive feature support.

### Initialization

```python
def __init__(
    self,
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None,
) -> None
```

**Parameters:**
- `settings`: Configuration settings that include the provider routing flag
- `llm_model`: Specifies which language model to use (optional)
- `user`: The user object interacting with the AI
- `system`: System-level parameters

The initialization creates appropriate chat models and sets up the AI logger based on configuration.

### Core Methods

#### Synchronous Chat

```python
def chat(
    self,
    messages: Optional[List[Message]] = None,
    prompt: Optional[str] = None,
    *,
    max_response_length: Optional[int] = None,
    callback: Optional[Callable] = None,
    tools: Optional[List[str]] = None,
    headers: Optional[Dict[str, Any]] = None,
    cancellation_token: Optional[CancellationToken] = None,
    chat_id: Optional[str] = None,
    run_context: Optional[AgentRunContext] = None,
) -> List[Message]
```

A synchronous wrapper that provides consistent behavior across both providers (SmolAgent and OpenAI_AI). This method internally delegates to `a_chat()` using asyncio to bridge async code.

**Parameters:**
- `messages`: History of conversation messages
- `prompt`: User prompt to append as a human message
- `max_response_length`: Maximum token limit for the response
- `callback`: Optional callback function for processing
- `tools`: List of tools available for function calling
- `headers`: Custom headers for the LLM request
- `cancellation_token`: Token to cancel ongoing completion
- `chat_id`: Identifier for analytics traceability
- `run_context`: Shared context carrying event listeners and cancellation information

**Returns:** List of processed messages including the AI reply

**Raises:**
- `CancelledError`: If the request is cancelled
- `RuntimeError`: If AI processing fails

#### Asynchronous Chat

```python
async def a_chat(
    self,
    messages: Optional[List[Message]] = None,
    prompt: Optional[str] = None,
    *,
    max_response_length: Optional[int] = None,
    callback: Optional[Callable] = None,
    tools: Optional[List[str]] = None,
    headers: Optional[Dict[str, Any]] = None,
    cancellation_token: Optional[CancellationToken] = None,
    chat_id: Optional[str] = None,
    run_context: Optional[AgentRunContext] = None,
) -> List[Message]
```

The primary asynchronous method for processing user inputs and returning AI responses. This method delegates to the configured provider and ensures event and cancellation information flows through the system.

**Parameters:** Same as synchronous `chat()` method

**Returns:** List of processed messages including the AI reply

**Raises:** Same as synchronous `chat()` method

#### Logging

```python
def log(self, message: str, *args: Any) -> None
```

Logs messages using the AI Logger when logging is enabled in settings. Supports lazy string formatting with optional arguments.

### Provider Management

#### Create Chat Model

```python
def create_chat_model(self, llm_model: Optional[str]) -> Callable
```

Initializes the appropriate chat completions model based on the `use_smol_agent` settings flag. Returns a callable that bridges the provider's interface to the sync interface.

#### Create Asynchronous Chat Model

```python
def create_a_chat_model(self, llm_model: Optional[str]) -> Callable
```

Initializes the appropriate asynchronous chat completions model based on the `use_smol_agent` settings flag.

#### Get OpenAI Chat Client

```python
def get_openai_chat_client(self, llm_model: Optional[str] = None) -> Any
```

Retrieves the underlying OpenAI client instance. When using SmolAgent provider, returns the generic OpenAI client from SmolAgent.

### Internal Utilities

#### Synchronous Wrapper

```python
@staticmethod
def _make_sync_wrapper(async_func: Callable) -> Callable
```

Creates a synchronous wrapper around async functions to support legacy synchronous callers. This bridges SmolAgent's async-only interface with sync code paths.

## Utility Functions

### Message MD5 Hash

```python
def messages_md5(messages: List[Message]) -> str
```

Creates an MD5 hash from conversation messages for caching or deduplication purposes. Concatenates all message contents and returns the hexadecimal digest.

### Serialize Messages

```python
def serialize_messages(messages: List[Message]) -> List[Dict[str, str]]
```

Converts message objects to a JSON-compatible format. Each message is transformed into a dictionary containing its type and content.

## Message Types

The module uses LangChain message types:
- `AIMessage`: Messages generated by the AI
- `HumanMessage`: Messages from users
- `SystemMessage`: System-level messages

The type alias `Message` represents any of these types.

## Architecture

The module follows a provider routing pattern where:
- **SmolAgent**: Used when `use_smol_agent` is True (async-native provider)
- **OpenAI_AI**: Used when `use_smol_agent` is False (legacy provider)

Both providers are abstracted behind a consistent interface, allowing seamless switching between them without affecting caller code.

## Features

- **Provider Routing**: Automatic delegation to SmolAgent or OpenAI_AI based on settings
- **Async Support**: Full async/await support with sync wrapper for backwards compatibility
- **Cancellation**: Built-in cancellation token support for long-running requests
- **Event Listeners**: Integration with `AgentRunContext` for real-time event tracking
- **Analytics Traceability**: Chat ID forwarding for tracking conversation analytics
- **Tool Support**: Function calling capabilities with configurable tool lists
- **Custom Headers**: Support for custom request headers per call
- **Logging**: Integrated AI logger for operation tracking

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/ai/openai_ai.py, codx/junior/ai/ai_logger.py, codx/junior/ai/cancellation.py, codx/junior/profiling/profiler.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/context.py