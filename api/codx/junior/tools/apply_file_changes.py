"""
Tool for applying a list of changes to a file using search and replace patterns.

This module provides functionality to apply multiple changes to a file while
preserving indentation and handling conflicts appropriately.

Made with ❤️ by codx-junior

Process Flow:

```mermaid
graph TD
    A[Start: apply_file_changes] --> B[Validate Settings]
    B -->|Invalid| C[⚠️ Return Error<br/>Missing Settings]
    B -->|Valid| D[Validate File Path]
    D -->|Invalid Path| C
    D -->|Outside Project| C
    D -->|Valid| E[📖 Read File<br/>UTF-8 Encoding]
    E -->|Read Error| C
    E -->|Success| F[✓ Validate All<br/>Changes]
    F -->|Invalid Change| C
    F -->|Valid| G[⚙️ Apply Changes<br/>Sequentially]
    G --> H{All Changes<br/>Applied?}
    H -->|Conflict Found| I[❌ Stop at Failed<br/>Change]
    I --> J[📋 Return Error Info<br/>with Context]
    H -->|Success| K[💾 Write to File<br/>UTF-8 Encoding]
    K -->|Write Error| C
    K -->|Success| L[✅ Return Success<br/>with Summary]
    C --> M[🏁 End] 
    J --> M
    L --> M
```

Change Validation & Application:

```mermaid
graph TD
    A[📝 Change Dict] --> B{"Is Valid?<br/>Has search & replace?"}
    B -->|No| C[❌ Return Error<br/>Missing/Invalid Fields]
    B -->|Yes| D[🔍 Search Pattern<br/>in Content]
    D --> E{"Pattern<br/>Found?"}
    E -->|No| F[❌ Return Error<br/>Pattern Not Found]
    E -->|Yes| G{"Count<br/>Matches"}
    G -->|Multiple| H[❌ Return Error<br/>Ambiguous Match<br/>N occurrences found]
    G -->|Exactly One| I[✂️ Replace Text<br/>With Preserve<br/>Indentation]
    I --> J[✅ Return Success<br/>New Content]
    C --> K[🏁 End]
    F --> K
    H --> K
    J --> K
```

Sequential Application Flow:

```mermaid
graph TD
    A[🔄 Start Sequential<br/>Application] --> B[Loop Through<br/>Each Change]
    B --> C{"Change<br/>Index"}
    C -->|Index 0| D[Apply Change 0]
    C -->|Index 1| E[Apply Change 1]
    C -->|Index N| F[Apply Change N]
    D --> D1{"Success?"}
    E --> E1{"Success?"}
    F --> F1{"Success?"}
    D1 -->|No| D2[❌ Stop & Report<br/>Error at Index 0]
    E1 -->|No| E2[❌ Stop & Report<br/>Error at Index 1]
    F1 -->|No| F2[❌ Stop & Report<br/>Error at Index N]
    D1 -->|Yes| D3[✅ Update Content<br/>Track Applied]
    E1 -->|Yes| E3[✅ Update Content<br/>Track Applied]
    F1 -->|Yes| F3[✅ Update Content<br/>Track Applied]
    D3 --> G{"More<br/>Changes?"}
    E3 --> G
    F3 --> G
    G -->|Yes| B
    G -->|No| H[🎯 All Changes Applied]
    D2 --> I[🏁 End with Error]
    E2 --> I
    F2 --> I
    H --> J[💾 Write to File<br/>& Return Success]
    J --> K[🏁 End Success]
```
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

from codx.junior.settings import CODXJuniorSettings
from .project_tools import path_to_absolute_project_path, _to_relative_path
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Constants
CHANGE_ERROR_TEMPLATE = "error [%s]\nERROR: %s"


def _validate_change(change: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate that a change dict has required fields.

    Args:
        change: The change dictionary to validate.

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not isinstance(change, dict):
        return False, "Change must be a dictionary"

    if "search" not in change:
        return False, "Missing required field: 'search'"

    if "replace" not in change:
        return False, "Missing required field: 'replace'"

    if not isinstance(change["search"], str):
        return False, "Field 'search' must be a string"

    if not isinstance(change["replace"], str):
        return False, "Field 'replace' must be a string"

    return True, None


def _apply_single_change(
    content: str, search: str, replace: str
) -> Tuple[str, Optional[str]]:
    """
    Apply a single search and replace change to content.

    Args:
        content: The current file content.
        search: The text to search for.
        replace: The text to replace with.

    Returns:
        Tuple[str, Optional[str]]: (modified_content, error_message_or_none)
            - If successful: (new_content, None)
            - If conflict: (unchanged_content, error_description)
    """
    if not search:
        return content, "Search pattern cannot be empty"

    if search not in content:
        return content, f"Search pattern not found in file"

    # Count occurrences to detect multiple matches
    occurrences = content.count(search)

    if occurrences > 1:
        error_msg = (
            f"Ambiguous match: search pattern found {occurrences} times in file. "
            "Be more specific to avoid conflicts."
        )
        return content, error_msg

    # Perform the replacement (only one occurrence due to check above)
    new_content = content.replace(search, replace, 1)

    return new_content, None


def apply_file_changes(
    file_path: str,
    changes: List[Dict[str, Any]],
    **kwargs
) -> ToolResponse:
    """
    Apply a list of search and replace changes to a file.

    Each change is a dictionary with 'search' and 'replace' keys. Changes are
    applied sequentially. If any change fails due to conflicts or validation errors,
    the operation stops and returns the error information for the LLM.

    Indentation is automatically preserved as the changes use exact text matching.

    Args:
        file_path: Path to the file to modify.
        changes: List of change dictionaries, each containing:
            - "search" (str): Text pattern to find (must be unique in file)
            - "replace" (str): Text to replace with
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Code block showing the modified file or error.
            - llm_response: Summary of changes applied or conflict details.

    Raises:
        Exception: If project settings are not provided.
        ValueError: If file_path or changes are not provided or invalid.

    Example:
        Apply multiple changes at once:
        >>> apply_file_changes(
        ...     "src/app.py",
        ...     [
        ...         {
        ...             "search": "def old_function():",
        ...             "replace": "def new_function():"
        ...         },
        ...         {
        ...             "search": "return False",
        ...             "replace": "return True"
        ...         }
        ...     ]
        ... )
        # Returns ToolResponse with modified file content and summary
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    if not file_path:
        raise ValueError("file_path must be provided")

    if not changes:
        raise ValueError("changes list must be provided and cannot be empty")

    if not isinstance(changes, list):
        raise ValueError("changes must be a list of dictionaries")

    # Validate file path
    abs_path = path_to_absolute_project_path(settings=settings, file_path=file_path)
    if not abs_path or not abs_path.startswith(settings.abs_project_path):
        error_msg = f"File path must belong to {settings.abs_project_path}"
        logger.error("Invalid file path: %s", file_path)
        error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
        return ToolResponse(
            user_response=error_block,
            llm_response=f"Apply changes failed: {error_msg}",
        )

    # Read the file
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError) as e:
        error_msg = f"Failed to read file: {str(e)}"
        logger.error("Error reading file %s: %s", file_path, error_msg)
        error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
        return ToolResponse(
            user_response=error_block,
            llm_response=f"Apply changes failed: {error_msg}",
        )

    # Validate all changes first
    for idx, change in enumerate(changes):
        is_valid, error = _validate_change(change)
        if not is_valid:
            error_msg = f"Change {idx}: {error}"
            logger.error("Invalid change at index %d: %s", idx, error)
            error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
            return ToolResponse(
                user_response=error_block,
                llm_response=f"Apply changes failed: {error_msg}",
            )

    # Apply changes sequentially
    original_content = content
    applied_changes = []
    failed_at_change = None

    for idx, change in enumerate(changes):
        search = change["search"]
        replace = change["replace"]

        new_content, error = _apply_single_change(content, search, replace)

        if error:
            failed_at_change = {
                "index": idx,
                "search": search,
                "error": error,
            }
            logger.warning("Change %d failed: %s", idx, error)
            break

        content = new_content
        applied_changes.append({
            "index": idx,
            "search_preview": search[:50] + "..." if len(search) > 50 else search,
            "status": "applied",
        })

    # Handle failures
    if failed_at_change:
        error_msg = (
            f"Conflict at change {failed_at_change['index']}: "
            f"{failed_at_change['error']} "
            f"Search pattern: '{failed_at_change['search'][:50]}...'"
        )
        logger.error("Apply changes stopped: %s", error_msg)
        error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
        return ToolResponse(
            user_response=error_block,
            llm_response=f"Apply changes failed at step {failed_at_change['index']}: {failed_at_change['error']}",
        )

    # All changes applied successfully - write to file
    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        rel_path = _to_relative_path(settings=settings, abs_path=abs_path)
        extension = abs_path.split(".")[-1] if "." in abs_path else ""

        # Build responses
        code_block = f"```{extension} {rel_path}\n{content}\n```"

        summary = f"Applied {len(applied_changes)} change(s) to {rel_path}"
        llm_response = f"{summary}"

        logger.info("Successfully applied %d changes to file: %s", len(applied_changes), file_path)

        return ToolResponse(
            user_response=code_block,
            llm_response=llm_response,
        )

    except (IOError, OSError) as e:
        error_msg = f"Failed to write file: {str(e)}"
        logger.error("Error writing to file %s: %s", file_path, error_msg)
        error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
        return ToolResponse(
            user_response=error_block,
            llm_response=f"Apply changes failed during write: {error_msg}",
        )

# Made with ❤️ by codx-junior


# Error Handling & Recovery Flow:
#
# ```mermaid
# graph TD
#     A["🚨 Conflict Detected"] --> B{"Error Type"}
#     B -->|File Error| C["IOError/<br/>OSError"]
#     B -->|Validation| D["Missing Fields/<br/>Invalid Type"]
#     B -->|Not Found| E["Search Pattern<br/>Not in File"]
#     B -->|Ambiguous| F["Multiple<br/>Matches Found"]
#     C --> G["📋 Log Error<br/>with Context"]
#     D --> G
#     E --> G
#     F --> G
#     G --> H["📤 Return ToolResponse<br/>with Error Block"]
#     H --> I["Format Error Message:<br/>error [file_path]<br/>ERROR: message"]
#     I --> J["🏁 Stop Processing<br/>Revert to Original"]
# ```