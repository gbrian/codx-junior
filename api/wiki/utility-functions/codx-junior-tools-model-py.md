# ToolResponse

## Overview

`ToolResponse` is a data model class that enables tools to provide dual-return responses, allowing simultaneous delivery of user-facing output and LLM-context feedback.

## Purpose

This class facilitates tools that need to produce two distinct outputs:
- **User-facing output**: Formatted content displayed in the chat interface
- **LLM feedback**: Lightweight context information for continued language model processing

This dual-response pattern is particularly useful for tools like code block generators that need to present formatted results to users while maintaining conversational context with the language model.

## Class Definition

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `user_response` | `str` | Formatted content displayed to the user in the chat interface |
| `llm_response` | `str` | Lightweight feedback or status message for the LLM context |

### Constructor

```python
__init__(user_response: str, llm_response: str) -> None
```

Initializes a dual-return tool response with the provided user and LLM response strings.

**Parameters:**
- `user_response` (`str`): Content visible to the user
- `llm_response` (`str`): Feedback/status message for the LLM

### Methods

#### `__str__()`

Returns the LLM feedback string representation of the response.

**Returns:** `str` - The `llm_response` value (provides backward compatibility)

## Usage Example

```python
response = ToolResponse(
    user_response="Here is your formatted code block...",
    llm_response="Code block generated successfully"
)
```

## Notes

- The `__str__()` method returns `llm_response` for backward compatibility with string context expectations
- This design pattern separates concerns between user presentation and language model context management