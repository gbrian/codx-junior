"""
Project structure tool for exploring project organization.

This tool provides information about the project's file and folder structure,
making it easy to understand the project layout and locate components.

Made with ❤️ by codx-junior
"""

import os
import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from pathlib import Path

from .project_tools import list_project_files

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# Tool JSON definitions
PROJECT_STRUCTURE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "project_structure",
        "description": "Get the project structure with files and folders read from disk, including nested (child) projects. Files and folders are filtered using only the repository .gitignore. Returns a tree-like representation of the project organization.",
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
                    "description": "Maximum folder depth to traverse. Folders that reach this depth are shown by name but not expanded, together with the number of files and folders they contain. Leave null for no limit.",
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
        "description": "Read and display the structure of a specific folder within the project, reading files and folders from disk, including nested (child) projects. Files and folders are filtered using only the repository .gitignore. Provides a tree-like view of files and subdirectories at a given path.",
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
    Get the project structure with files and folders read from disk.

    The project's files and folders are read directly from the filesystem,
    including any nested (child) projects. Filtering uses only the repository
    ``.gitignore`` rules, so ignored folders and files are discarded while child
    projects remain navigable.

    When ``max_depth`` is set, the tree is truncated at that depth. Folders that
    reach the limit are still listed by name—so the model knows they exist—but
    are not expanded, and the number of files and folders they contain is shown
    instead.

    Args:
        include_details: If True, includes additional metadata like file counts per folder.
        max_depth: Maximum folder depth to traverse (None = no limit). Folders at
            the limit are shown collapsed with their file and folder counts.
        include_file_sizes: If True, includes file sizes in bytes for each file.
        path: Optional folder path to limit results to. Must be within project or codx path.
        settings: CODXJuniorSettings instance (passed by SmolAgent).

    Returns:
        str: Formatted project structure as a tree-like string representation.

    Raises:
        ValueError: If settings is not provided or path is invalid.

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
        📁 child-project/
          📁 src/
            📄 main.py (1.1 KB)
        📁 tests/
          📄 Button.test.tsx (4.1 KB)

        Limit the traversal depth; folders beyond the limit keep their name and
        expose the number of files and folders they contain:
        >>> result = project_structure(max_depth=1)
        >>> print(result)
        # Project Structure

        📁 src/ (12 files, 4 folders)
        📁 child-project/ (1 file, 1 folder)
        📄 README.md

    Made with ❤️ by codx-junior
    """
    if not settings:
        error_msg = "project_structure requires settings parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        structure_info = _build_structure(
            settings=settings,
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


def _collect_project_files(settings: "CODXJuniorSettings") -> List[str]:
    """
    Collect project-relative file paths from the project and its child projects.

    Files are read from disk and filtered using only the repository
    ``.gitignore`` (see :func:`list_project_files` with
    ``apply_custom_ignores=False``). Child projects discovered under the project
    root (see ``settings.get_sub_projects``) are traversed as well, so their
    files appear in the structure tree even though the project's custom ignore
    patterns would normally exclude them.

    Args:
        settings: CODXJuniorSettings instance with project configuration.

    Returns:
        List[str]: Sorted, de-duplicated project-relative file paths.

    Example:
        >>> _collect_project_files(settings)
        ['README.md', 'codx/junior/tools/project_structure.py',
         'child-project/src/main.py']
    """
    project_root = os.path.abspath(settings.abs_project_path)
    rel_files: set = set()

    # Current project files, honoring only .gitignore
    for rel_path in list_project_files(settings=settings, apply_custom_ignores=False):
        rel_files.add(os.path.normpath(rel_path))

    # Nested child projects, honoring each of their own .gitignore
    try:
        sub_projects = settings.get_sub_projects()
    except Exception as ex:
        logger.warning("Could not resolve child projects: %s", ex)
        sub_projects = []

    for child in sub_projects:
        if child is None:
            continue

        child_root = os.path.abspath(child.abs_project_path)
        prefix = os.path.relpath(child_root, project_root)
        # Skip child projects that live outside this project root
        if prefix.startswith(".."):
            logger.debug("Skipping child project outside project root: %s", child_root)
            continue

        try:
            child_files = list_project_files(
                settings=child, apply_custom_ignores=False
            )
        except Exception as ex:
            logger.warning(
                "Error listing child project '%s': %s",
                getattr(child, "project_name", child_root),
                ex,
            )
            continue

        for rel_path in child_files:
            rel_files.add(os.path.normpath(os.path.join(prefix, rel_path)))

    return sorted(rel_files)


def _build_structure(
    settings: "CODXJuniorSettings",
    include_details: bool = False,
    max_depth: Optional[int] = None,
    include_file_sizes: bool = False,
    path: Optional[str] = None
) -> str:
    """
    Build the project structure representation.

    This internal function constructs the tree-like representation of the
    project's files and folders by reading them directly from disk, including
    nested (child) projects. Only the repository ``.gitignore`` rules are
    applied (through :func:`_collect_project_files`); the project's custom
    ignore patterns are intentionally not used so child projects stay navigable.

    The full tree is always built from every project file. The ``max_depth``
    limit is applied later, while formatting, so that folders sitting at the
    limit are still listed by name together with the number of files and folders
    they contain (see :func:`_format_tree`).

    Args:
        settings: CODXJuniorSettings instance with project configuration.
        include_details: Include additional metadata.
        max_depth: Maximum recursion depth (applied while formatting).
        include_file_sizes: Include file size information.
        path: Optional folder path to limit results to.

    Returns:
        str: Formatted project structure.

    Raises:
        RuntimeError: If the project files cannot be read.
        ValueError: If path is invalid.

    Diagram:
    flowchart TD
        A[_build_structure] --> B[Collect project + child project files from disk]
        B --> C[Filter using only .gitignore]
        C --> D[Filter by path if set]
        D --> E[Build full folder tree structure]
        E --> F[Format as tree representation]
        F --> G[Collapse folders at max_depth and add file/folder counts]
        G --> H[Add metadata if requested]
        H --> I[Return formatted string]
    """
    try:
        project_root = os.path.abspath(settings.abs_project_path)

        # Read the project files directly from disk (including child projects),
        # filtering with only the repository .gitignore.
        project_files: List[str] = _collect_project_files(settings=settings)

        if not project_files:
            return "No files found in the project."

        # Validate and resolve path if provided
        target_path = None
        if path:
            codx_root = getattr(settings, "abs_codx_path", None)
            try:
                target_path = _validate_path(path, project_root, codx_root)
            except ValueError as ex:
                raise ValueError(f"Invalid path parameter: {str(ex)}") from ex

        structure_tree: Dict[str, Any] = {}

        for relative_path in project_files:
            rel_path = Path(relative_path)
            abs_path = os.path.join(project_root, relative_path)

            # Skip if path filter is set and file is not under target path
            if target_path:
                try:
                    Path(abs_path).relative_to(target_path)
                except ValueError:
                    continue

            # Build nested dictionary structure. The full tree is always built;
            # the max_depth limit is applied while formatting so folder names
            # are preserved even when their content is not expanded.
            _add_to_tree(structure_tree, rel_path, abs_path, include_file_sizes)

        # Format and return the structure
        formatted = _format_tree(
            structure_tree,
            include_details=include_details,
            project_root=project_root,
            max_depth=max_depth,
        )

        return formatted

    except ValueError:
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


def _count_tree(node: Dict[str, Any]) -> tuple:
    """
    Recursively count the files and folders contained in a folder node.

    Args:
        node: The ``_children`` dictionary of a folder node.

    Returns:
        tuple: ``(file_count, folder_count)`` counts including all descendants.

    Example:
        >>> _count_tree(folder_node["_children"])
        (12, 4)
    """
    file_count = 0
    folder_count = 0

    for info in node.values():
        if info.get("_type") == "folder":
            folder_count += 1
            child_files, child_folders = _count_tree(info.get("_children", {}))
            file_count += child_files
            folder_count += child_folders
        elif info.get("_type") == "file":
            file_count += 1

    return file_count, folder_count


def _format_children_summary(file_count: int, folder_count: int) -> str:
    """
    Build a human-readable summary of a collapsed (not expanded) folder.

    Args:
        file_count: Number of files contained in the folder.
        folder_count: Number of folders contained in the folder.

    Returns:
        str: Summary label such as ``(1 file, 2 folders)``.

    Example:
        >>> _format_children_summary(1, 0)
        '(1 file, 0 folders)'
    """
    file_label = "file" if file_count == 1 else "files"
    folder_label = "folder" if folder_count == 1 else "folders"
    return f"({file_count} {file_label}, {folder_count} {folder_label})"


def _format_tree(
    tree: Dict[str, Any],
    include_details: bool = False,
    project_root: str = "",
    prefix: str = "",
    is_last: bool = True,
    max_depth: Optional[int] = None,
    depth: int = 1
) -> str:
    """
    Format the tree structure as a string representation.

    When ``max_depth`` is set, folders at or beyond the limit are rendered
    collapsed: their name is kept so the reader knows the folder exists, but
    their content is replaced by the count of files and folders they contain.

    Args:
        tree: The tree dictionary to format.
        include_details: Include additional metadata.
        project_root: Project root path for reference.
        prefix: Prefix for tree formatting (internal use).
        is_last: Whether this is the last item (internal use).
        max_depth: Maximum folder depth to display (None = no limit).
        depth: Depth of the items in ``tree`` (internal use, root items = 1).

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
            children = info.get("_children", {})

            # Depth limit reached: keep the folder name but do not expand it.
            # Show how many files and folders it contains so the model knows
            # the folder exists and how much it holds.
            if max_depth and depth >= max_depth:
                file_count, folder_count = _count_tree(children)
                summary = _format_children_summary(file_count, folder_count)
                lines.append(f"{prefix}{current_prefix}📁 **{name}**/ {summary}")
                continue

            # Format folder
            lines.append(f"{prefix}{current_prefix}📁 **{name}**/")

            # Recursively format children
            if children:
                child_lines = _format_tree(
                    children,
                    include_details=include_details,
                    project_root=project_root,
                    prefix=prefix + next_prefix,
                    is_last=is_last_item,
                    max_depth=max_depth,
                    depth=depth + 1
                )
                lines.append(child_lines)

        elif info.get("_type") == "file":
            # Only reached for expanded levels; guard against over-deep files
            if max_depth and depth > max_depth:
                continue

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