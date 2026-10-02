# Tutorial Tools

Tools for managing tutorial content with nested chapter structure. Provides operations for querying, creating, modifying, and deleting chapters.

## Overview

The Tutorial Tools module provides a comprehensive set of functions for managing hierarchical tutorial content. Each tutorial can contain nested chapters with their own content, metadata, and messages.

## Functions

### tutorial_definition

Retrieve the complete tutorial definition as JSON.

**Description:**
Returns a hierarchical representation of the tutorial including all chapters, nested content, messages, and metadata.

**Parameters:**
- `tutorial_id` (str): ID of the root tutorial chat (mode='tutorial')
- `settings` (Optional[CODXJuniorSettings]): CODXJuniorSettings instance

**Returns:**
- Dict with tutorial definition (chapters, content, metadata)

**Exceptions:**
- `ValueError`: If tutorial not found or not marked as mode='tutorial'
- `RuntimeError`: If chat manager is unavailable

**Example Usage:**
```python
definition = tutorial_definition(
    tutorial_id="tutorial_123",
    settings=settings
)
```

---

### create_chapter

Create a new chapter in a tutorial.

**Description:**
Adds a new chapter to an existing tutorial or parent chapter with optional initial content and metadata.

**Parameters:**
- `tutorial_id` (str): ID of parent tutorial/chapter
- `name` (str): Chapter title
- `description` (str): Chapter description (optional, default: "")
- `content` (str): Initial message content (optional, default: "")
- `tags` (Optional[List[str]]): Chapter tags (optional)
- `settings` (Optional[CODXJuniorSettings]): CODXJuniorSettings instance

**Returns:**
- `ToolResponse` with creation status and chapter details

**Example Usage:**
```python
response = create_chapter(
    tutorial_id="parent_id",
    name="Getting Started",
    description="Introduction to basics",
    content="Welcome to the tutorial",
    tags=["intro", "basics"],
    settings=settings
)
```

---

### modify_chapter

Modify a chapter's content or metadata.

**Description:**
Updates chapter properties including name, description, tags, and allows appending new message content.

**Parameters:**
- `chapter_id` (str): ID of the chapter to modify
- `name` (Optional[str]): New chapter title
- `description` (Optional[str]): New description
- `tags` (Optional[List[str]]): New tags
- `content` (Optional[str]): Message content to append
- `settings` (Optional[CODXJuniorSettings]): CODXJuniorSettings instance

**Returns:**
- `ToolResponse` with modification status

**Example Usage:**
```python
response = modify_chapter(
    chapter_id="chapter_123",
    name="Updated Title",
    description="Updated description",
    tags=["updated", "modified"],
    settings=settings
)
```

---

### delete_chapter

Delete a chapter from the tutorial.

**Description:**
Removes a chapter from the tutorial hierarchy. The main tutorial root (mode='tutorial' with no parent) cannot be deleted.

**Parameters:**
- `chapter_id` (str): ID of the chapter to delete
- `settings` (Optional[CODXJuniorSettings]): CODXJuniorSettings instance

**Returns:**
- `ToolResponse` with deletion status

**Exceptions:**
- `ValueError`: If chapter is tutorial root or not found

**Example Usage:**
```python
response = delete_chapter(
    chapter_id="chapter_123",
    settings=settings
)
```

---

## ToolResponse

All modification functions return a `ToolResponse` object containing:
- `user_response`: Human-friendly message describing the operation result
- `llm_response`: Detailed response for language model consumption

## Error Handling

All functions include comprehensive error handling:
- Missing `settings` parameter raises `ValueError`
- Operation failures raise `RuntimeError` with descriptive messages
- Exceptions are logged with full context for debugging