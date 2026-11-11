"""Project atlas: a verified, incremental navigation index for the codebase."""

from .constants import (
    ATLAS_TOOL_NAMES,
    LEGACY_DISCOVERY_TOOL_NAMES,
    apply_atlas_policy,
    atlas_enabled,
    atlas_forced,
)
from .indexer import AtlasIndexer, index_project
from .models import AtlasHealth, AtlasPacket, Evidence
from .query import ProjectAtlas, atlas_db_path, atlas_ready
from .related import find_related_project, related_projects
from .store import AtlasStore

__all__ = [
    "ATLAS_TOOL_NAMES",
    "LEGACY_DISCOVERY_TOOL_NAMES",
    "apply_atlas_policy",
    "atlas_enabled",
    "atlas_forced",
    "AtlasIndexer",
    "AtlasStore",
    "AtlasHealth",
    "AtlasPacket",
    "Evidence",
    "ProjectAtlas",
    "atlas_db_path",
    "atlas_ready",
    "find_related_project",
    "index_project",
    "related_projects",
]
