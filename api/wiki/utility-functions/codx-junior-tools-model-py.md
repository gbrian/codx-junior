I've generated comprehensive wiki documentation for the tools model module. The documentation includes:

**Key Sections:**
1. **Overview** - Introduction to the module's purpose within the codx-junior API
2. **ToolResponse Class** - Detailed explanation of the dual-return response pattern
3. **Architecture** - How user content and LLM feedback work together
4. **Attributes** - Complete documentation of the class properties with types and usage
5. **Constructor** - Parameter documentation for initialization
6. **String Representation** - Explanation of the `__str__()` method and backward compatibility
7. **Usage Patterns** - Real-world application examples
8. **Related Tools** - References to tools that consume this model
9. **Module Information** - Project context and categorization

The documentation is written in markdown format and focuses exclusively on information extracted from the provided source file, making it suitable for a project wiki.

```markdown wiki/tools-model-documentation.md
# Data Models for Tools Module

## Overview

This module provides data classes and models essential for tool operations within the codx-junior API. It establishes standardized response structures that enable seamless communication between tools, the user interface, and the language model context.

## ToolResponse Class

### Purpose

The `ToolResponse` class implements a dual-return response pattern designed for tools that need to simultaneously generate user-facing output and provide feedback to the language model. This pattern is particularly valuable for tools like `code_block_generator` that produce formatted content visible to users while maintaining LLM context awareness.

### Architecture

The dual-return mechanism allows:
- **User Content**: Formatted, presentation-ready output displayed in the chat interface
- **LLM Feedback**: Lightweight status messages or feedback that inform the language model about tool execution results

This separation ensures that the user interface receives properly formatted content while the LLM receives concise, actionable feedback for continued processing.

### Attributes

#### user_content
- **Type**: `str`
- **Description**: Content formatted and displayed to the user in the chat interface
- **Usage**: This is the primary output visible to end users

#### llm_feedback
- **Type**: `str`
- **Description**: Lightweight feedback or status message provided to the LLM context
- **Usage**: Enables the LLM to understand tool execution status and adapt subsequent responses

### Constructor

```python
def __init__(self, user_content: str, llm_feedback: str) -> None
```

#### Parameters

- **user_content** (`str`): Content visible to the user in the chat interface
- **llm_feedback** (`str`): Feedback or status message for the LLM context

### String Representation

The class implements the `__str__()` method for backward compatibility, returning the `llm_feedback` value. This allows the response object to be used in contexts expecting string output while preserving the lightweight feedback intended for the language model.

## Usage Patterns

The `ToolResponse` class is designed to work with tools that produce dual outputs:

- **Code Generation Tools**: Generate formatted code blocks for users while providing compilation or syntax status to the LLM
- **Data Processing Tools**: Display structured results to users while conveying processing metrics to the LLM
- **Utility Functions**: Return user-friendly output alongside execution status indicators

## Related Tools

- `code_block_generator`: Primary consumer of the `ToolResponse` pattern, generates formatted code blocks with both user-visible content and LLM feedback

## Module Information

**Project**: codx-api  
**Category**: Utility Functions  
**Key Features**: Utility functions, chat utilities, browser use integration, log parsing  
**Maintained by**: codx-junior team

```