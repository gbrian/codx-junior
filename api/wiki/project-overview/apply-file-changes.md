# File Changes Application Tool

## Overview

The `apply_file_changes` tool enables safe application of multiple search-and-replace changes to files within a project. It validates all changes before execution and prevents ambiguous modifications through exact pattern matching.

## Key Features

- **Sequential Change Application**: Changes are applied one at a time with immediate failure reporting
- **Exact Pattern Matching**: Requires unique search patterns to prevent unintended modifications
- **Atomic File Writing**: Uses temporary files and atomic rename operations for data safety
- **Content Caching**: Maintains file state across tool calls within a conversation
- **Comprehensive Validation**: Checks file access, size, encoding, and change validity before processing
- **Contextual Error Reporting**: Provides line numbers and context when patterns fail to match

## Usage

### Basic Syntax

```python
apply_file_changes(
    file_path="path/to/file.py",
    changes=[
        {
            "search": "text to find",
            "replace": "replacement text"
        }
    ]
)
```

### Parameters

- **file_path** (str): Relative or absolute path to the file to modify
- **changes** (list): List of change dictionaries containing:
  - `search` (str): Exact text pattern to locate (must be unique in file)
  - `replace` (str): Replacement text (including all formatting and indentation)
- **tool_cache** (optional): Cache instance for file content persistence
- **settings** (CODXJuniorSettings): Project configuration (required via kwargs)

## Change Validation Process

Each change undergoes validation to ensure:

1. **Structure Validation**: Change must be a dictionary with `search` and `replace` keys
2. **Type Validation**: Both `search` and `replace` must be strings
3. **Pattern Matching**: Search pattern must exist in the file
4. **Uniqueness**: Search pattern must match exactly once (no ambiguous matches)

If validation fails at any step, the operation stops and returns error details with contextual information.

## Important Guidelines

### Exact Pattern Matching

Search patterns must include complete surrounding context to ensure unique identification:

- Include surrounding lines of code
- Preserve exact indentation in both `search` and `replace` strings
- Do not rely on the tool to infer missing indentation
- Use longer patterns when the target appears multiple times

### Example: Correct Pattern

```python
{
    "search": "def old_function():\n    return False",
    "replace": "def new_function():\n    return True"
}
```

### Error Handling

The tool provides specific error messages for:

- **Pattern Not Found**: Lists similar lines where expected text was found
- **Ambiguous Match**: Shows line numbers of all occurrences and suggests using more context
- **File Access Issues**: Reports size, encoding, or permission problems

## File Processing

### Size and Type Restrictions

- Maximum file size: 10 MB
- Files must be text-based (not binary)
- Must be regular files, not directories or special files

### Path Security

File paths are validated to ensure they remain within the project directory, preventing path traversal attacks through path normalization.

### Encoding

Files are read and written using UTF-8 encoding with newline handling to preserve platform-specific line endings.

## Content Caching

Modified file content is cached using the key format `file_content:{abs_path}`. This allows:

- Multiple sequential changes without disk I/O between operations
- Persistence of modifications within a single conversation
- Faster processing for large files

## Response Format

### Success Response

Returns a code block with the modified file content:

```
```extension relative/path
modified content here
```
```

The LLM receives a summary of changes applied.

### Error Response

Returns an error block with format:

```
error [file_path]
ERROR: error description
```

The LLM receives details about which change failed and why.

## Process Flow

1. **Validate Settings**: Verify project configuration is provided
2. **Validate Path**: Ensure file is within project and accessible
3. **Read File**: Retrieve content from disk or cache
4. **Validate Changes**: Check all changes before any modification
5. **Apply Changes**: Execute each change sequentially in memory
6. **Handle Conflicts**: Stop at first failure with detailed error
7. **Write Atomically**: Update disk file only if all changes succeeded
8. **Update Cache**: Store modified content for subsequent calls

## Limitations

- Changes cannot resolve to multiple locations (must be unique)
- File size cannot exceed 10 MB
- Binary files are not supported
- Each change must be valid independently