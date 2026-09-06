"""
Tool for applying a list of changes to a file using search and replace patterns.

This module provides functionality to apply multiple changes to a file while
handling conflicts appropriately. Changes use exact text matching to ensure
safety and predictability.

IMPORTANT: Include complete surrounding context in search patterns to ensure
exact, unique matches. Do not rely on indentation preservation—include the
intended indentation explicitly in both search and replace strings.

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
        H -->|Success| K[💾 Write to File<br/>Atomically]
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
         E -->|No| F[❌ Return Error<br/>Pattern Not Found<br/>+ Context]
         E -->|Yes| G{"Count<br/>Matches"}
         G -->|Multiple| H[❌ Return Error<br/>Ambiguous Match<br/>N occurrences found<br/>+ Line Numbers]
         G -->|Exactly One| I[✂️ Replace Text<br/>Exact Matching]
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
        H --> J[💾 Write to File<br/>Atomically<br/>& Return Success]
        J --> K[🏁 End Success]
    ```
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from codx.junior.settings import CODXJuniorSettings
from .project_tools import path_to_absolute_project_path, _to_relative_path
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Constants
CHANGE_ERROR_TEMPLATE = "error [%s]\nERROR: %s"
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PREVIEW_LENGTH = 80


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


def _find_match_context(
    content: str, search: str, context_lines: int = 2
) -> List[Dict[str, Any]]:
    """
    Find all occurrences of search pattern and return context for each.

    Args:
        content: The file content to search.
        search: The pattern to find.
        context_lines: Number of lines of context around each match.

    Returns:
        List of dictionaries with match info: line_number, line_content, context
    """
    matches = []
    lines = content.split("\n")
    search_lines = search.split("\n")
    
    # Simple line-based matching for context
    for line_idx, line in enumerate(lines):
        if search.split("\n")[0] in line:
            # Found potential match on this line
            start_idx = max(0, line_idx - context_lines)
            end_idx = min(len(lines), line_idx + context_lines + 1)
            
            context = "\n".join(lines[start_idx:end_idx])
            matches.append({
                "line_number": line_idx + 1,
                "line_content": line,
                "context": context,
            })
    
    return matches


def _apply_single_change(
    content: str, search: str, replace: str
) -> Tuple[str, Optional[str]]:
    """
    Apply a single search and replace change to content.

    Args:
        content: The current file content.
        search: The text to search for (must match exactly once).
        replace: The text to replace with.

    Returns:
        Tuple[str, Optional[str]]: (modified_content, error_message_or_none)
            - If successful: (new_content, None)
            - If conflict: (unchanged_content, error_description)
    """
    if not search:
        return content, "Search pattern cannot be empty"

    if search not in content:
        # Provide context about what was expected
        matches = _find_match_context(content, search)
        context_info = ""
        if matches:
            context_info = f" Similar lines found at: {', '.join(str(m['line_number']) for m in matches[:3])}"
        
        error_msg = f"Search pattern not found in file.{context_info}"
        return content, error_msg

    # Count occurrences to detect multiple matches
    occurrences = content.count(search)

    if occurrences > 1:
        # Find line numbers of all matches
        matches = _find_match_context(content, search)
        line_numbers = [str(m["line_number"]) for m in matches[:5]]
        lines_str = ", ".join(line_numbers)
        if len(matches) > 5:
            lines_str += f", ... ({len(matches)} total)"
        
        error_msg = (
            f"Ambiguous match: search pattern found {occurrences} times in file "
            f"(at lines: {lines_str}). Use a larger surrounding code block to uniquely identify the intended location."
        )
        return content, error_msg

    # Perform the replacement (only one occurrence due to check above)
    new_content = content.replace(search, replace, 1)

    return new_content, None


def _validate_file_access(abs_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate file type, size, and encoding before processing.

    Args:
        abs_path: Absolute path to the file.

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Check if path is a regular file
    if not os.path.isfile(abs_path):
        return False, "Path must be a regular file"

    # Check file size
    try:
        file_size = os.path.getsize(abs_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            return False, f"File size ({file_size} bytes) exceeds maximum ({MAX_FILE_SIZE_BYTES} bytes)"
    except OSError as e:
        return False, f"Cannot access file: {str(e)}"

    # Check for binary content by attempting to read a sample
    try:
        with open(abs_path, "rb") as f:
            sample = f.read(8192)
            if b"\x00" in sample:
                return False, "File appears to be binary"
    except OSError as e:
        return False, f"Cannot read file: {str(e)}"

    return True, None


def _secure_path_check(settings: CODXJuniorSettings, abs_path: str) -> Tuple[bool, Optional[str]]:
    """
    Securely validate that abs_path is within the project directory.

    Uses normalized resolved paths to prevent path traversal attacks.

    Args:
        settings: Project settings containing abs_project_path.
        abs_path: Absolute path to validate.

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        project_path = Path(settings.abs_project_path).resolve()
        target_path = Path(abs_path).resolve()
        
        # Attempt to get relative path; raises ValueError if outside project
        target_path.relative_to(project_path)
        return True, None
    except (ValueError, OSError):
        return False, f"File path must belong to {settings.abs_project_path}"


def _write_file_atomically(abs_path: str, content: str) -> Tuple[bool, Optional[str]]:
    """
    Write content to file atomically using temp file + rename.

    Args:
        abs_path: Absolute path to target file.
        content: Content to write.

    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
    """
    directory = os.path.dirname(abs_path) or "."
    
    try:
        # Create temp file in same directory for atomic rename
        fd, temp_path = tempfile.mkstemp(
            dir=directory,
            prefix=".apply-file-changes-",
            text=False
        )

        try:
            # Write to temp file with explicit newline handling
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as temp_file:
                temp_file.write(content)

            # Atomic replace
            os.replace(temp_path, abs_path)
            return True, None

        except (IOError, OSError) as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            return False, f"Failed to write file: {str(e)}"

    except (IOError, OSError) as e:
        return False, f"Failed to create temp file: {str(e)}"


def apply_file_changes(
    file_path: str,
    changes: List[Dict[str, Any]],
    **kwargs
) -> ToolResponse:
    """
    Apply a list of search and replace changes to a file.

    Each change is a dictionary with 'search' and 'replace' keys. Changes are
    applied sequentially in memory. If any change fails due to conflicts or
    validation errors, NO changes are written to disk and error information
    is returned for the LLM to handle.

    IMPORTANT: Search patterns must be exact matches. Include complete surrounding
    context to ensure uniqueness. Do NOT rely on indentation preservation—include
    the exact indentation in both search and replace strings.

    Args:
        file_path: Path to the file to modify (relative or absolute).
        changes: List of change dictionaries, each containing:
            - "search" (str): Exact text pattern to find (must be unique in file)
            - "replace" (str): Text to replace with (include all formatting)
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Code block showing the modified file or error.
            - llm_response: Summary of changes applied or conflict details.

    Raises:
        Exception: If project settings are not provided.
        ValueError: If file_path or changes are not provided or invalid type.

    Example:
        Apply multiple changes at once:
        >>> apply_file_changes(
        ...     "src/app.py",
        ...     [
        ...         {
        ...             "search": "def old_function():\\n    return False",
        ...             "replace": "def new_function():\\n    return True"
        ...         },
        ...         {
        ...             "search": "import old_module",
        ...             "replace": "import new_module"
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

    # Validate file path with secure resolution
    abs_path = path_to_absolute_project_path(settings=settings, file_path=file_path)
    
    is_valid, error_msg = _secure_path_check(settings, abs_path)
    if not is_valid:
        logger.error("Invalid file path: %s", file_path)
        error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
        return ToolResponse(
            user_response=error_block,
            llm_response=f"Apply changes failed: {error_msg}",
        )

    # Validate file access before processing
    is_valid, error_msg = _validate_file_access(abs_path)
    if not is_valid:
        logger.error("File access validation failed for %s: %s", file_path, error_msg)
        error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
        return ToolResponse(
            user_response=error_block,
            llm_response=f"Apply changes failed: {error_msg}",
        )

    # Read the file with explicit newline handling
    try:
        with open(abs_path, "r", encoding="utf-8", newline="") as f:
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

    # Apply changes sequentially in memory
    applied_changes = []
    failed_at_change = None

    for idx, change in enumerate(changes):
        search = change["search"]
        replace = change["replace"]

        new_content, error = _apply_single_change(content, search, replace)

        if error:
            failed_at_change = {
                "index": idx,
                "search_preview": search[:MAX_PREVIEW_LENGTH],
                "error": error,
            }
            logger.warning("Change %d failed: %s", idx, error)
            break

        content = new_content
        applied_changes.append({
            "index": idx,
            "status": "applied",
        })

    # Handle failures - no file written
    if failed_at_change:
        error_msg = (
            f"Conflict at change {failed_at_change['index']}: "
            f"{failed_at_change['error']}"
        )
        logger.error("Apply changes stopped: %s", error_msg)
        error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
        return ToolResponse(
            user_response=error_block,
            llm_response=f"Apply changes failed at step {failed_at_change['index']}: {failed_at_change['error']}",
        )

    # All changes applied successfully - write to file atomically
    success, write_error = _write_file_atomically(abs_path, content)
    
    if not success:
        error_msg = write_error or "Unknown write error"
        logger.error("Error writing to file %s: %s", file_path, error_msg)
        error_block = CHANGE_ERROR_TEMPLATE % (file_path, error_msg)
        return ToolResponse(
            user_response=error_block,
            llm_response=f"Apply changes failed during write: {error_msg}",
        )

    # Success - build response
    rel_path = _to_relative_path(settings=settings, abs_path=abs_path)
    extension = abs_path.split(".")[-1] if "." in abs_path else ""

    code_block = f"```{extension} {rel_path}\n{content}\n```"

    summary = f"Applied {len(applied_changes)} change(s) to {rel_path}"
    llm_response = f"{summary}"

    logger.info("Successfully applied %d changes to file: %s", len(applied_changes), file_path)

    return ToolResponse(
        user_response=code_block,
        llm_response=llm_response,
    )

# Made with ❤️ by codx-junior