# apply_file_changes Tool Documentation

## Overview

The `apply_file_changes` tool provides functionality to safely apply multiple search-and-replace changes to files within a project. Changes are applied sequentially in memory and only written to disk if all changes succeed, preventing partial modifications in case of conflicts.

## Key Features

- **Exact Text Matching**: Uses precise pattern matching to ensure safety and predictability
- **Atomic Writing**: Implements atomic file writes using temporary files and rename operations
- **Sequential Application**: Applies changes one at a time, stopping at the first conflict
- **Context-Aware Errors**: Provides detailed error messages with line numbers and surrounding context
- **Security**: Validates file paths to prevent directory traversal attacks
- **Binary Detection**: Automatically detects and rejects binary files

## Core Concepts

### Change Dictionary Format

Each change must be a dictionary containing exactly two required fields:

- **`search`** (string): The exact text pattern to find. Must match exactly once in the file. Include complete surrounding context to ensure uniqueness.
- **`replace`** (string): The replacement text. Must include all intended formatting and indentation explicitly.

**Important**: Do not rely on indentation preservation. Include the exact indentation in both search and replace strings.

### Validation Process

Before applying any changes, the tool validates:

1. **Settings Validation**: Verifies project settings are provided
2. **File Path Validation**: Ensures the path is within the project directory
3. **File Access Validation**: Checks that the file is:
   - A regular file (not directory)
   - Not binary
   - Within size limits (10 MB maximum)
   - Readable with UTF-8 encoding
4. **Change Validation**: Confirms each change dictionary has required fields of correct type

### Sequential Application Flow

Changes are applied in order with the following logic:

1. Each change is applied to the in-memory content from the previous change
2. If a change fails (pattern not found or ambiguous match), processing stops immediately
3. No file is written if any change fails
4. All changes must succeed before the file is updated

## Error Handling

The tool detects and reports the following error conditions:

### Pattern Not Found
Occurs when the search pattern doesn't exist in the file. The error message includes line numbers of similar content found nearby to help refine the search pattern.

### Ambiguous Match
Occurs when the search pattern matches multiple times in the file. The error message lists line numbers of all occurrences (limited to first 5 shown, with total count). To resolve, expand the search pattern with more surrounding context to make it unique.

### Invalid Change Structure
Reported if a change dictionary is missing required fields or contains invalid field types.

### File Access Issues
Reported for binary files, oversized files, encoding problems, or path traversal attempts.

### Write Failures
Reported if the atomic write operation fails.

## Function Signature

```python
def apply_file_changes(
    file_path: str,
    changes: List[Dict[str, Any]],
    **kwargs
) -> ToolResponse
```

### Parameters

- **`file_path`** (string): Path to the file to modify, relative or absolute to project root
- **`changes`** (list): List of change dictionaries, each with "search" and "replace" keys
- **`**kwargs`**: Additional arguments including `settings` (CODXJuniorSettings) - required

### Return Value

Returns a `ToolResponse` containing:

- **`user_response`**: Code block showing the modified file content on success, or formatted error message on failure
- **`llm_response`**: Summary of changes applied or detailed conflict information

## Usage Example

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

## Best Practices

1. **Use Surrounding Context**: Include lines before and after the code you're changing to ensure uniqueness
2. **Explicit Formatting**: Include exact indentation, newlines, and spacing in both search and replace strings
3. **Single Responsibility**: Each change should modify one logical unit
4. **Test Patterns**: Verify search patterns are unique in the file before requesting changes
5. **Preserve Structure**: Maintain file formatting conventions and indentation levels

## Constraints

- Maximum file size: 10 MB
- File must be valid UTF-8 text
- Binary files are not supported
- File path must be within the project directory
- Each search pattern must match exactly once in the file

## Internal Helpers

See relevant sections for implementation details:

- **`_validate_change()`**: Validates change dictionary structure
- **`_apply_single_change()`**: Applies a single change with conflict detection
- **`_find_match_context()`**: Locates matches and provides context lines
- **`_validate_file_access()`**: Checks file type, size, and encoding
- **`_secure_path_check()`**: Prevents path traversal attacks
- **`_write_file_atomically()`**: Safely writes changes using temporary file mechanism