"""
Project structure tool for exploring project organization.

This tool provides information about the project's file and folder structure,
making it easy to understand the project layout and locate components.

Made with ❤️ by codx-junior
"""

import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# Tool JSON definitions
PROJECT_STRUCTURE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "project_structure",
        "description": "Get the project structure with files and folders, excluding invalid files. Returns a tree-like representation of the project organization.",
        "parameters": {
            "type": "object",
            "properties": {
                "include_details": {
                    "type": "boolean",
                    "description": "If true, includes additional metadata like file counts and folder statistics.",
                    "default": False
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum folder depth to traverse. Leave null for no limit.",
                    "default": None
                },
                "include_file_sizes": {
                    "type": "boolean",
                    "description": "If true, includes file sizes in bytes for each file.",
                    "default": False
                },
                "path": {
                    "type": "string",
                    "description": "Optional folder path to limit results to a specific directory. Must be within the project's path or codx path."
                }
            },
            "required": []
        }
    }
}

READ_FOLDER_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "read_folder",
        "description": "Read and display the structure of a specific folder within the project. Provides a tree-like view of files and subdirectories at a given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Folder path to read. Must be within the project's path or codx path."
                },
                "include_details": {
                    "type": "boolean",
                    "description": "If true, includes additional metadata like file counts and folder statistics.",
                    "default": False
                },
                "include_file_sizes": {
                    "type": "boolean",
                    "description": "If true, includes file sizes in bytes for each file.",
                    "default": False
                }
            },
            "required": ["path"]
        }
    }
}


def project_structure(
    include_details: bool = False,
    max_depth: Optional[int] = None,
    include_file_sizes: bool = False,
    path: Optional[str] = None,
    settings: Optional["CODXJuniorSettings"] = None,
) -> str:
    """
    Get the project structure with files and folders.

    This tool returns the project's file and folder organization,
    excluding invalid files and ignored patterns defined in project settings.

    Args:
        include_details: If True, includes additional metadata like file counts per folder.
        max_depth: Maximum folder depth to traverse (None = no limit).
        include_file_sizes: If True, includes file sizes in bytes for each file.
        path: Optional folder path to limit results to. Must be within project or codx path.
        settings: CODXJuniorSettings instance (passed by SmolAgent).

    Returns:
        str: Formatted project structure as a tree-like string representation.

    Raises:
        ValueError: If settings is not provided or path is invalid.
        RuntimeError: If project context is unavailable.

    Example:
        >>> result = project_structure(include_details=True)
        >>> print(result)
        # Project Structure
        
        📁 src/
          📁 components/
            📄 Button.tsx (2.5 KB)
            📄 Card.tsx (1.8 KB)
          📁 utils/
            📄 helpers.ts (3.2 KB)
        📁 tests/
          📄 Button.test.tsx (4.1 KB)

    Made with ❤️ by codx-junior
    """
    if not settings:
        error_msg = "project_structure requires settings parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Get the active session from settings (injected by SmolAgent runtime)
        session = getattr(settings, "_active_session", None)
        if not session:
            raise RuntimeError(
                "project_structure: no active session in settings. "
                "The SmolAgent runtime must inject session context."
            )

        structure_info = _build_structure(
            session=session,
            include_details=include_details,
            max_depth=max_depth,
            include_file_sizes=include_file_sizes,
            path=path
        )

        logger.info("Project structure retrieved successfully")
        return structure_info

    except ValueError:
        raise
    except RuntimeError:
        raise
    except Exception as ex:
        logger.exception("Error retrieving project structure: %s", ex)
        error_msg = f"Error retrieving project structure: {str(ex)}"
        return error_msg


def read_folder(
    path: str,
    include_details: bool = False,
    include_file_sizes: bool = False,
    settings: Optional["CODXJuniorSettings"] = None,
) -> str:
    """
    Read and display the structure of a specific folder within the project.

    This tool provides a focused view of a particular directory, making it easy
    to explore specific areas of the project structure.

    Args:
        path: Folder path to read. Must be within project or codx path.
        include_details: If True, includes additional metadata like file counts per folder.
        include_file_sizes: If True, includes file sizes in bytes for each file.
        settings: CODXJuniorSettings instance (passed by SmolAgent).

    Returns:
        str: Formatted folder structure as a tree-like string representation.

    Raises:
        ValueError: If settings is not provided or path is invalid.
        RuntimeError: If project context is unavailable.

    Example:
        >>> result = read_folder(path="src/components", include_file_sizes=True)
        >>> print(result)
        # Project Structure
        
        📁 components/
          📄 Button.tsx (2.5 KB)
          📄 Card.tsx (1.8 KB)

    Made with ❤️ by codx-junior
    """
    return project_structure(
        include_details=include_details,
        max_depth=None,
        include_file_sizes=include_file_sizes,
        path=path,
        settings=settings,
    )


def _validate_path(path_str: str, project_root: str, codx_root: Optional[str] = None) -> Path:
    """
    Validate that a path is within project or codx boundaries.

    Args:
        path_str: Path string to validate.
        project_root: Project root path.
        codx_root: Optional codx root path.

    Returns:
        Path: Resolved path object.

    Raises:
        ValueError: If path is not within allowed boundaries.
    """
    # Resolve the path
    resolved_path = (Path(project_root) / path_str).resolve()
    project_root_resolved = Path(project_root).resolve()
    
    # Check if path is within project root
    try:
        resolved_path.relative_to(project_root_resolved)
        return resolved_path
    except ValueError:
        pass
    
    # Check if path is within codx root if provided
    if codx_root:
        codx_root_resolved = Path(codx_root).resolve()
        try:
            resolved_path.relative_to(codx_root_resolved)
            return resolved_path
        except ValueError:
            pass
    
    raise ValueError(
        f"Path '{path_str}' is not within project root '{project_root}' "
        f"or codx root '{codx_root or 'not provided'}'"
    )


def _build_structure(
    session: Any,
    include_details: bool = False,
    max_depth: Optional[int] = None,
    include_file_sizes: bool = False,
    path: Optional[str] = None
) -> str:
    """
    Build the project structure representation.

    This internal function constructs the tree-like representation of the
    project's files and folders, using the knowledge base to get valid files.

    Args:
        session: CODXJuniorSession instance with project configuration.
        include_details: Include additional metadata.
        max_depth: Maximum recursion depth.
        include_file_sizes: Include file size information.
        path: Optional folder path to limit results to.

    Returns:
        str: Formatted project structure.

    Raises:
        RuntimeError: If knowledge base is not available.
        ValueError: If path is invalid.

    Diagram:
    flowchart TD
        A[_build_structure] --> B[Get all valid sources from Knowledge]
        B --> C[Build folder tree structure]
        C --> D[Filter by max_depth if set]
        D --> E[Filter by path if set]
        E --> F[Format as tree representation]
        F --> G[Add metadata if requested]
        G --> H[Return formatted string]
    """
    try:
        # Get knowledge base instance from session
        knowledge = session.knowledge
        if not knowledge:
            raise RuntimeError("Knowledge base not initialized in session")

        # Get all valid indexed sources
        all_sources: List[str] = knowledge.get_all_sources()

        if not all_sources:
            return "No files indexed in the project yet. Run a knowledge reload first."

        # Build folder hierarchy
        project_root = knowledge.settings.abs_project_path
        
        # Validate and resolve path if provided
        target_path = None
        if path:
            codx_root = getattr(knowledge.settings, "abs_codx_path", None)
            try:
                target_path = _validate_path(path, project_root, codx_root)
            except ValueError as ex:
                raise ValueError(f"Invalid path parameter: {str(ex)}") from ex
        
        structure_tree: Dict[str, Any] = {}

        for source in all_sources:
            # Get relative path from project root
            try:
                relative_path = Path(source).relative_to(project_root)
            except ValueError:
                relative_path = Path(source)

            # Skip if max_depth is set
            if max_depth and len(relative_path.parts) > max_depth:
                continue

            # Skip if path filter is set and source is not under target path
            if target_path:
                try:
                    Path(source).relative_to(target_path)
                except ValueError:
                    continue

            # Build nested dictionary structure
            _add_to_tree(structure_tree, relative_path, source, include_file_sizes)

        # Format and return the structure
        formatted = _format_tree(
            structure_tree,
            include_details=include_details,
            project_root=project_root
        )

        return formatted

    except ValueError:
        raise
    except RuntimeError:
        raise
    except Exception as ex:
        logger.exception("Error building project structure: %s", ex)
        raise RuntimeError(f"Error building project structure: {str(ex)}") from ex


def _add_to_tree(
    tree: Dict[str, Any],
    path: Path,
    full_path: str,
    include_file_sizes: bool = False
) -> None:
    """
    Add a file path to the folder tree structure.

    Args:
        tree: The tree dictionary to update.
        path: Relative Path object.
        full_path: Full path to the file.
        include_file_sizes: Whether to include file size.
    """
    parts = path.parts
    current = tree

    # Navigate/create folders
    for part in parts[:-1]:
        if part not in current:
            current[part] = {"_type": "folder", "_children": {}}
        current = current[part]["_children"]

    # Add file
    file_name = parts[-1]
    file_info: Dict[str, Any] = {"_type": "file", "_path": full_path}

    if include_file_sizes:
        try:
            file_size = Path(full_path).stat().st_size
            file_info["_size"] = file_size
        except (OSError, IOError) as ex:
            logger.warning("Could not get file size for %s: %s", full_path, ex)

    current[file_name] = file_info


def _format_tree(
    tree: Dict[str, Any],
    include_details: bool = False,
    project_root: str = "",
    prefix: str = "",
    is_last: bool = True
) -> str:
    """
    Format the tree structure as a string representation.

    Args:
        tree: The tree dictionary to format.
        include_details: Include additional metadata.
        project_root: Project root path for reference.
        prefix: Prefix for tree formatting (internal use).
        is_last: Whether this is the last item (internal use).

    Returns:
        str: Formatted tree representation.
    """
    lines = []

    if not prefix:  # Root level
        lines.append("# Project Structure\n")
        if project_root:
            lines.append(f"**Root**: `{project_root}`\n")

    items = sorted(tree.items())

    for idx, (name, info) in enumerate(items):
        is_last_item = (idx == len(items) - 1)

        # Build tree characters
        current_prefix = "└── " if is_last_item else "├── "
        next_prefix = "    " if is_last_item else "│   "

        if info.get("_type") == "folder":
            # Format folder
            lines.append(f"{prefix}{current_prefix}📁 **{name}**/")

            # Recursively format children
            children = info.get("_children", {})
            if children:
                child_lines = _format_tree(
                    children,
                    include_details=include_details,
                    project_root=project_root,
                    prefix=prefix + next_prefix,
                    is_last=is_last_item
                )
                lines.append(child_lines)

        elif info.get("_type") == "file":
            # Format file
            file_name = name
            file_path = info.get("_path", "")

            size_info = ""
            if include_details and "_size" in info:
                size_bytes = info["_size"]
                size_str = _format_file_size(size_bytes)
                size_info = f" ({size_str})"

            # Determine file icon based on extension
            file_icon = _get_file_icon(name)
            lines.append(f"{prefix}{current_prefix}{file_icon} {file_name}{size_info}")

    return "\n".join(lines)


def _get_file_icon(file_name: str) -> str:
    """
    Get an appropriate icon/emoji for a file based on its extension.

    Args:
        file_name: The file name to determine icon for.

    Returns:
        str: An emoji/icon representation of the file type.
    """
    extension_map = {
        "py": "🐍",
        "js": "📜",
        "ts": "📘",
        "tsx": "⚛️",
        "jsx": "⚛️",
        "json": "📦",
        "yaml": "⚙️",
        "yml": "⚙️",
        "md": "📝",
        "txt": "📄",
        "html": "🌐",
        "css": "🎨",
        "sql": "🗄️",
        "java": "☕",
        "cpp": "⚙️",
        "c": "⚙️",
        "go": "🐹",
        "rs": "🦀",
        "sh": "📛",
        "bash": "📛",
        "dockerfile": "🐳",
        "makefile": "🔨",
    }

    if "." in file_name:
        ext = file_name.split(".")[-1].lower()
    else:
        ext = ""

    return extension_map.get(ext, "📄")


def _format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes.

    Returns:
        str: Formatted size string (e.g., "2.5 KB").
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.1f} TB"


# Made with ❤️ by codx-junior