# Tutorial Management Module

Handles tutorial operations including definition retrieval, chapter creation, modification, and deletion. Uses chat and message resources to create learning content with nested hierarchies.

A tutorial is a chat with `mode='tutorial'` that can have child chats (chapters) via parent_id references, ordered by child_index.

## Overview

The `TutorialManager` class manages tutorial chats and their nested chapter structure. All tutorial operations use the standard Chat and Message resources from the codx-junior database layer.

### Key Concepts

- **Tutorial**: A root chat with `mode='tutorial'` that serves as the container for a learning module
- **Chapter**: A child chat linked via parent_id that represents content within a tutorial
- **Ordering**: Chapters are ordered by `child_index` to maintain consistent structure

## Initialization

```python
TutorialManager(settings: CODXJuniorSettings)
```

Initialize the tutorial manager with a CODXJuniorSettings instance. Internally creates a ChatManager instance for persistence operations.

**Parameters:**
- `settings`: CODXJuniorSettings instance containing configuration

## Methods

### tutorial_definition

```python
tutorial_definition(tutorial_id: str) -> Dict[str, Any]
```

Returns a JSON object with the complete tutorial definition by recursively reading the chat hierarchy.

**Parameters:**
- `tutorial_id`: ID of the root tutorial chat

**Returns:** Dictionary containing:
- `id`: Tutorial identifier
- `name`: Tutorial name
- `description`: Tutorial description
- `mode`: Always 'tutorial'
- `tags`: Associated tags (empty list if none)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `chapters`: Ordered list of chapter dictionaries with nested content

**Raises:**
- `ValueError`: If tutorial_id not found or not marked as tutorial mode

### _build_chapter_list

```python
_build_chapter_list(parent_id: str) -> List[Dict[str, Any]]
```

Recursively builds a list of chapters for a tutorial or parent chapter, sorted by child_index in ascending order.

**Parameters:**
- `parent_id`: ID of the tutorial or parent chapter

**Returns:** Ordered list of chapter dictionaries, each containing:
- `id`: Chapter identifier
- `title`: Chapter name
- `description`: Chapter description
- `mode`: Chapter mode
- `child_index`: Position in parent's child list
- `tags`: Associated tags
- `message_count`: Number of messages in chapter
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `messages`: List of visible messages (role, content, timestamps)
- `nested_chapters`: Recursively nested chapters

### create_chapter

```python
create_chapter(
    tutorial_id: str,
    name: str,
    description: str = "",
    content: str = "",
    tags: Optional[List[str]] = None,
    child_index: Optional[int] = None,
) -> Chat
```

Creates a new chapter (child chat) within a tutorial.

**Parameters:**
- `tutorial_id`: ID of the parent tutorial or chapter
- `name`: Chapter title
- `description`: Chapter description (optional)
- `content`: Initial message content (optional)
- `tags`: Tags for the chapter (optional)
- `child_index`: Position in siblings - auto-assigned if None (optional)

**Returns:** The created chapter Chat object

**Raises:**
- `ValueError`: If tutorial_id not found

**Behavior:**
- Auto-assigns child_index by calculating the maximum index of existing siblings plus 1
- Creates chapter with mode='chat' by default
- Inherits owner_project_id, board, and column from parent chat
- Appends initial content as an assistant message if provided

### modify_chapter

```python
modify_chapter(
    chapter_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    child_index: Optional[int] = None,
    add_message: Optional[Message] = None,
) -> Chat
```

Modifies a chapter's metadata, content, or structure.

**Parameters:**
- `chapter_id`: ID of the chapter to modify
- `name`: New chapter title (if provided)
- `description`: New description (if provided)
- `tags`: New tags list (if provided)
- `child_index`: New position in sibling order (if provided)
- `add_message`: Message to append to the chapter (if provided)

**Returns:** The modified chapter Chat object

**Raises:**
- `ValueError`: If chapter_id not found

**Behavior:**
- Only updates provided parameters (others remain unchanged)
- Generates UUID for messages without doc_id
- Persists all changes to storage

### delete_chapter

```python
delete_chapter(chapter_id: str) -> None
```

Deletes a chapter from the tutorial.

**Parameters:**
- `chapter_id`: ID of the chapter to delete

**Raises:**
- `ValueError`: If chapter not found or is a tutorial root

**Restrictions:**
- Cannot delete tutorial root chats (mode='tutorial' with no parent_id)
- Only child chapters can be deleted via this method

### move_chapter

```python
move_chapter(
    chapter_id: str,
    new_parent_id: str,
    new_index: Optional[int] = None,
) -> Chat
```

Moves a chapter to a different parent to reorganize tutorial structure.

**Parameters:**
- `chapter_id`: ID of the chapter to move
- `new_parent_id`: ID of the new parent tutorial/chapter
- `new_index`: New position in parent's child list - auto-assigned if None (optional)

**Returns:** The moved chapter Chat object

**Raises:**
- `ValueError`: If chapter or parent not found

**Behavior:**
- Updates parent_id reference
- Auto-assigns new_index by calculating the maximum index of siblings under new parent plus 1
- Persists changes to storage