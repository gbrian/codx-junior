# AI Class Documentation

## Overview

The `AI` class serves as the main orchestrator for managing AI interactions with provider routing capabilities. It intelligently routes chat requests between different providers (SmolAgent for async-native operations or OpenAI_AI for legacy support) based on global settings, while maintaining support for analytics traceability and real-time event listeners.

## Architecture

The class implements a provider abstraction pattern with the following key relationships:

- **Provider Routing**: Routes to either SmolAgent (async-native) or OpenAI_AI (legacy) based on the `use_smol_agent` configuration flag
- **Event Management**: Supports forwarding `AgentRunContext` for real-time tool and lifecycle event listeners
- **Cancellation Handling**: Integrates `CancellationToken` for request cancellation support
- **Logging & Analytics**: Maintains session state and chat identifiers for traceability

## Initialization

### Constructor Parameters

```python
def __init__(
    self,
    settings: CODXJuniorSettings,
    llm_model: Optional[str] = None,
    user: Optional[CodxUser] = None,
    system: Optional[str] = None,
    session: Optional[Any] = None,
) -> None:
```

- **settings**: Configuration object containing provider selection and LLM settings
- **llm_model**: Specific model identifier to use for completions
- **user**: `CodxUser` object representing the interacting user
- **system**: System-level parameters for the AI context
- **session**: Optional session context for tools requiring access to current chat state

The constructor automatically initializes both synchronous and asynchronous chat models (`llm` and `a_llm`) based on the configured provider.

## Core Methods

### Synchronous Chat: `chat()`

Provides a synchronous interface for chat completions by wrapping the async `a_chat()` method:

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
    current_chat: Optional[Any] = None,
) -> List[Message]:
```

**Key Features:**
- Internally uses asyncio to bridge async code for synchronous callers
- Suitable for applications not optimized for high-concurrency scenarios
- Returns a list of processed messages including the AI response
- Properly handles event loop creation and cleanup

### Asynchronous Chat: `a_chat()`

The primary async method for non-blocking chat completions:

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
    current_chat: Optional[Any] = None,
) -> List[Message]:
```

**Behavior:**
- Delegates to the configured provider's async implementation
- Forwards `chat_id` for analytics traceability
- Passes `run_context` to enable event listeners and cancellation
- Preferred method for high-concurrency scenarios
- Automatically initializes message lists and tool arrays if not provided

**Parameters:**
- **messages**: Conversation history
- **prompt**: User input to append as a human message
- **max_response_length**: Token limit for the response
- **callback**: Optional callback function for async operations
- **tools**: List of available tools for function calling
- **headers**: Custom HTTP headers for the LLM request
- **cancellation_token**: Token to cancel ongoing completion
- **chat_id**: Identifier for analytics and traceability
- **run_context**: Shared context carrying event listeners and cancellation
- **current_chat**: Current chat object for tool context

## Provider Initialization

### Synchronous Chat Model: `create_chat_model()`

Creates the appropriate chat completion model based on provider settings:

```python
def create_chat_model(self, llm_model: Optional[str]) -> Callable:
```

- Returns a `Callable` that bridges SmolAgent's async interface to sync callers
- For OpenAI_AI, returns the synchronous `chat_completions` method
- Automatically initializes the selected provider with configured settings

### Asynchronous Chat Model: `create_a_chat_model()`

Initializes the asynchronous chat completion interface:

```python
def create_a_chat_model(self, llm_model: Optional[str]) -> Callable:
```

- Returns the native async callable for the selected provider
- Delegates to `SmolAgent.chat` or `OpenAI_AI.a_chat_completions`
- Properly configures user, system, and session context

## Utility Methods

### Sync Wrapper: `_make_sync_wrapper()`

Static method that creates a synchronous wrapper around async functions:

```python
@staticmethod
def _make_sync_wrapper(async_func: Callable) -> Callable:
```

Handles asyncio event loop management for legacy sync callers attempting to use async providers.

### OpenAI Client Access: `get_openai_chat_client()`

Provides access to the underlying OpenAI client:

```python
def get_openai_chat_client(self, llm_model: Optional[str] = None) -> Any:
```

- Returns the native client from the active provider
- For SmolAgent, returns a generic OpenAI client
- Useful for direct API interactions when needed

### Logging: `log()`

Conditionally logs AI operations:

```python
def log(self, message: str, *args: Any) -> None:
```

Messages are logged only if AI logging is enabled in settings.

## Message Utilities

### `messages_md5()`

Generates an MD5 hash of concatenated message contents:

```python
def messages_md5(messages: List[Message]) -> str:
```

Useful for caching and deduplication of conversation threads.

### `serialize_messages()`

Converts message objects to JSON-compatible dictionary format:

```python
def serialize_messages(messages: List[Message]) -> List[Dict[str, str]]:
```

Returns a list of dictionaries with `type` and `content` fields for each message.

## Message Type

The `Message` type alias represents any LangChain message:

```python
Message = Union[AIMessage, HumanMessage, SystemMessage]
```

Supports responses from AI, user inputs, and system context respectively.

## Error Handling

- **CancelledError**: Raised when a request is cancelled via `cancellation_token`
- **RuntimeError**: Raised during AI processing failures or when attempting sync operations from within async context

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/ai/openai_ai.py, codx/junior/ai/ai_logger.py, codx/junior/ai/cancellation.py, codx/junior/profiling/profiler.py, codx/junior/model/model.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/context.py