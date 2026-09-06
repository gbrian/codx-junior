# apply_file_changes Tool Documentation

## Overview

The `apply_file_changes` tool provides functionality to apply multiple search and replace changes to a file safely and predictably. Changes are validated and applied sequentially in memory, with atomic file writing to ensure data integrity.

## Key Features

- **Exact Text Matching**: Uses complete text patterns to ensure precise, unambiguous replacements
- **Sequential Application**: Applies changes one after another, stopping immediately on any conflict
- **Atomic Writing**: Uses temporary files and atomic rename to prevent partial writes
- **Comprehensive Validation**: Validates file access, path security, and change integrity before processing
- **Detailed Error Reporting**: Provides context-aware error messages with line numbers and surrounding content
- **Safe Path Handling**: Prevents path traversal attacks by validating all paths against project boundaries

## Function Signature

```python
apply_file_changes(
    file_path: str,
    changes: List[Dict[str, Any]],
    **kwargs
) -> ToolResponse
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | str | Yes | Path to the file to modify (relative or absolute) |
| `changes` | List[Dict[str, Any]] | Yes | List of change dictionaries with `search` and `replace` keys |
| `settings` (kwargs) | CODXJuniorSettings | Yes | Project settings containing project path |

### Change Dictionary Structure

Each change must contain:

```python
{
    "search": str,   # Exact text pattern to find (must be unique in file)
    "replace": str   # Text to replace with (include all formatting/indentation)
}
```

## Return Value

Returns a `ToolResponse` object containing:

- **user_response**: Code block showing modified file content or error details
- **llm_response**: Summary of changes applied or conflict details

## Processing Flow

### Validation Phase

1. Validates project settings are provided
2. Validates file path and resolves to absolute path
3. Checks path is within project directory (security check)
4. Validates file exists, is regular file, and not binary
5. Checks file size doesn't exceed 10 MB limit
6. Validates all changes have required fields (`search` and `replace`)

### Application Phase

1. Reads file content with UTF-8 encoding
2. Applies each change sequentially to in-memory content
3. For each change:
   - Verifies search pattern exists exactly once in content
   - Performs replacement if no conflicts detected
   - Stops immediately if pattern not found or matches multiple times
4. If all changes succeed, writes modified content atomically to file

### Conflict Detection

The tool detects and reports:

- **Missing Patterns**: Search text not found in file
- **Ambiguous Matches**: Search pattern found multiple times (shows line numbers)
- **Invalid Changes**: Missing required fields or wrong data types

## Important Usage Guidelines

### Search Pattern Completeness

Include complete surrounding context in search patterns to ensure exact matching:

```python
# ✅ GOOD - Includes surrounding code for uniqueness
{
    "search": "def old_function():\n    return False",
    "replace": "def new_function():\n    return True"
}

# ❌ BAD - Too generic, may match multiple times
{
    "search": "return False",
    "replace": "return True"
}
```

### Indentation Handling

Do not rely on automatic indentation preservation. Include exact indentation explicitly:

```python
# ✅ GOOD - Explicit indentation in both strings
{
    "search": "    if condition:\n        do_something()",
    "replace": "    if condition:\n        do_something_else()"
}
```

### Multi-line Changes

Include full line context for multi-line patterns:

```python
{
    "search": "import old_module\nimport another_module",
    "replace": "import new_module\nimport another_module"
}
```

## Error Handling

When a change fails:

- No changes are written to disk
- Complete error context is provided including:
  - Specific change index that failed
  - Reason for failure
  - Line numbers where similar patterns were found
- LLM receives detailed error information to adjust the change

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| Search pattern not found | Text doesn't exist in file | Verify exact text and indentation |
| Ambiguous match (N occurrences) | Pattern matches multiple times | Add more surrounding context to unique identify location |
| File appears to be binary | File contains binary data | Use on text files only |
| File path must belong to project | Path outside project directory | Use paths relative to project root |

## File Size and Encoding

- **Maximum file size**: 10 MB
- **Encoding**: UTF-8 with explicit newline handling
- **Newline preservation**: Original line endings are preserved during read/write

## Security Features

- **Path Traversal Prevention**: All paths normalized and validated against project boundaries
- **Atomic Writing**: Uses temporary files to prevent corruption if process interrupts
- **Binary Detection**: Refuses to process binary files
- **Encoding Validation**: Enforces UTF-8 encoding

## Example Usage

```python
apply_file_changes(
    "src/app.py",
    [
        {
            "search": "def old_function():\n    return False",
            "replace": "def new_function():\n    return True"
        },
        {
            "search": "import old_module",
            "replace": "import new_module"
        }
    ],
    settings=project_settings
)
```

## See Also

- Path resolution utilities: `path_to_absolute_project_path`, `_to_relative_path`
- Settings validation: `CODXJuniorSettings`
- Tool response format: `ToolResponse`