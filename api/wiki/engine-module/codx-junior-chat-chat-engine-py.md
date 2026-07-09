The provided code is a Python class implementation for a chat engine, which seems to be part of a conversational AI platform. The class provides methods for handling chat interactions with AI models, including message processing, knowledge search, context building, and AI response generation.

Here's how the documentation can be generated based on the provided document:

```markdown
# Chat Engine Documentation

## Overview

The `ChatEngine` class is a core component of the codx-junior conversational AI platform. It handles message processing, knowledge search, context building, and AI response generation for various chat modes.

### Classes

#### ChatEngine

*   **Methods**

    *   \*   `__init__`: Initializes the `ChatEngine` instance with project settings, event manager, and optional user.
    *   `_get_global_system`: Returns the global system instructions for the current project.
    *   `get_profile_manager`: Returns a `ProfileManager` instance for the current settings.
    *   `get_chat_manager`: Returns a `ChatManager` instance for the current chat, optionally scoped to a specific project.
    *   ...

### Methods

#### `_resolve_chat_mode_flags`

Resolves boolean flags that drive branching logic from the chat mode and task item.

*   **Parameters**

    *   `chat`: The current chat object.
    *   `chat_mode`: Explicit mode override (may be None).
    *   `task_item`: Task item from the latest user message.
*   **Returns** A dict with keys: `chat_mode`, `is_refine`, `is_agent`, `is_vibe`, `is_search`, and `needs_pre_search`.

#### `_build_message_history`

Converts all non-hidden, non-improvement chat messages (excluding the last) into LangChain message objects.

*   **Parameters**

    *   `chat`: The chat whose history to convert.
*   **Returns** A list of LangChain message objects.

#### ...

## Usage

The `ChatEngine` class can be used as follows:

```python
from codx.junior.chat_engine import ChatEngine

# Create a new ChatEngine instance with project settings, event manager, and optional user
engine = ChatEngine(settings=codx_settings, event_manager=event_manager, user=user)

# Get the profile manager instance for the current settings
profile_manager = engine.get_profile_manager()

# Get the chat manager instance for the current chat, optionally scoped to a specific project
chat_manager = engine.get_chat_manager(project_id=project_id)
```

## API

The `ChatEngine` class provides the following API:

### Methods

#### `__init__

Initialize the `ChatEngine` instance with project settings, event manager, and optional user.

#### `_get_global_system`
Returns the global system instructions for the current project.

#### `get_profile_manager`
Returns a `ProfileManager` instance for the current settings.

#### `get_chat_manager`
Returns a `ChatManager` instance for the current chat, optionally scoped to a specific project.

### Properties

#### `chat`

The current chat object.

#### ...

## Troubleshooting

If you encounter any issues with the `ChatEngine`, refer to the documentation or seek help from the codx-junior community.
```

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/ai/cancellation.py, codx/junior/chat_manager.py, codx/junior/context.py, codx/junior/db.py, codx/junior/globals.py, codx/junior/project/project_discover.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/profiles/profile_manager.py, codx/junior/profiling/profiler.py, codx/junior/settings.py, codx/junior/utils/chat_utils.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/chat/chat_knowledge.py
**Imported by:** codx/junior/engine/chat_engine_actions.py, codx/junior/mentions/mention_manager.py, codx/junior/tools/code_writer.py, tests/chat/test_chat_manager.py