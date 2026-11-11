"""
Constants and tool policy for the project atlas.

The atlas is the codebase's navigation index. It is deliberately independent
from LangChain, Milvus and the AI layer: indexing is AST/regex based and the
store is plain SQLite. That keeps the first query fast and makes the atlas
usable even when the knowledge base or the LLM provider is unavailable.

Tool policy lives here (and not in ``codx.junior.tools``) so the agent runtime
can enforce atlas-first discovery without importing the whole tool registry.
"""

from __future__ import annotations

from typing import Any, Iterable

ATLAS_DIRNAME = "atlas"
ATLAS_DB_FILENAME = "atlas.db"
ATLAS_INDEX_VERSION = 1

#: Read-only tools that replace grep/glob/search for project discovery.
ATLAS_TOOL_NAMES: tuple[str, ...] = (
    "project_map",
    "project_locate",
    "project_trace",
    "project_impact",
    "project_health",
)

#: Discovery tools hidden from the model while the atlas is enforced.
LEGACY_DISCOVERY_TOOL_NAMES: tuple[str, ...] = (
    "project_grep",
    "project_glob",
    "project_search",
    "project_structure",
)

#: Default cap. Above this the atlas reports ``truncated`` in its health output.
DEFAULT_MAX_FILES = 5000
#: How long a freshness check is reused within one process.
DEFAULT_TTL_SECONDS = 5


def atlas_enabled(settings: Any) -> bool:
    """Return True when the project atlas should be available for ``settings``."""
    if settings is None:
        return False
    return bool(getattr(settings, "project_atlas_enabled", False))


def atlas_forced(settings: Any) -> bool:
    """Return True when legacy discovery tools must be hidden from the model."""
    if not atlas_enabled(settings):
        return False
    return bool(getattr(settings, "project_atlas_force", True))


def apply_atlas_policy(
    tool_names: Iterable[str],
    settings: Any,
) -> set[str]:
    """
    Apply the atlas tool policy to a concrete tool-name set.

    The atlas tools are always added when the atlas is enabled, even when a
    profile allowlist predates them. When ``project_atlas_force`` is set (the
    default) the legacy discovery tools are removed, so the model cannot fall
    back to grep/glob/semantic search.
    """
    names = {str(name) for name in (tool_names or []) if name}
    if not atlas_enabled(settings):
        return names

    # The atlas reads project files. Do not grant it to a profile that has no
    # project-reading capability: that would widen its permissions.
    read_tools = {
        "project_read_file", "project_structure",
        "project_grep", "project_glob", "project_search",
    }
    if not names.intersection(read_tools):
        return names

    names.update(ATLAS_TOOL_NAMES)
    if atlas_forced(settings):
        names.difference_update(LEGACY_DISCOVERY_TOOL_NAMES)
    return names
