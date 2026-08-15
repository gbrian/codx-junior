"""
Global Settings API router.

Provides endpoints for reading and updating GlobalSettings:
- Full read/write for backward compatibility.
- Granular GET/PUT by section name via GlobalSettingsManager.
- Version history listing and rollback per section.

Made with ❤️ by codx-junior
"""

import logging
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Request

from codx.junior.model.model import CodxUser, GlobalSettings
from codx.junior.plugins.plugin_manager import PluginManager, Plugin
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.settings_manager import GlobalSettingsManager, SectionVersion
from codx.junior.global_settings import (
    get_global_settings,
    read_global_settings,
    write_global_settings,
    write_settings_section,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def is_admin_user(user: CodxUser = Depends(get_authenticated_user)) -> CodxUser:
    """Raise 403 if the authenticated user is not an admin."""
    if user.role != "admin":
        logger.error("Access denied for user: %s", user)
        raise HTTPException(status_code=403, detail="Access denied. Admins only.")
    return user


def get_settings_manager() -> GlobalSettingsManager:
    """Return a GlobalSettingsManager instance."""
    return GlobalSettingsManager()


# ===========================================================================
# Full settings — backward compatibility
# ===========================================================================

@router.get("/global/settings")
async def get_all_settings(
    user: CodxUser = Depends(is_admin_user),
) -> GlobalSettings:
    """Return the full GlobalSettings object assembled from all section files."""
    return read_global_settings()


@router.put("/global/settings")
async def update_all_settings(
    request: Request,
    user: CodxUser = Depends(is_admin_user),
) -> GlobalSettings:
    """Overwrite all settings sections at once from a full GlobalSettings payload."""
    data = await request.json()
    try:
        new_settings = GlobalSettings(**data)
    except (ValueError, TypeError) as ex:
        raise HTTPException(status_code=422, detail=str(ex)) from ex

    write_global_settings(new_settings)
    logger.info("All settings updated by user '%s'", user.username)
    return new_settings


# ===========================================================================
# Granular section endpoints
# ===========================================================================

@router.get("/global/settings/section/{section}")
async def get_section(
    section: str,
    user: CodxUser = Depends(is_admin_user),
    manager: GlobalSettingsManager = Depends(get_settings_manager),
) -> Any:
    """
    Return raw data for a specific GlobalSettings section.

    Args:
        section: Field name from GlobalSettings (e.g. 'ai_models', 'plugins', 'git').
    """
    data = manager.read_section_raw(section)
    if data is None:
        # Fall back to the default value from a fresh GlobalSettings instance
        defaults = GlobalSettings().dict()
        if section not in defaults:
            raise HTTPException(
                status_code=404,
                detail=f"Section '{section}' not found in GlobalSettings.",
            )
        data = defaults[section]
        logger.info("Section '%s' not persisted yet, returning default.", section)

    return data


@router.put("/global/settings/section/{section}")
async def update_section(
    section: str,
    request: Request,
    user: CodxUser = Depends(is_admin_user),
) -> Any:
    """
    Update a specific GlobalSettings section without affecting others.

    Args:
        section: Field name from GlobalSettings (e.g. 'ai_models', 'plugins', 'git').

    Body:
        JSON value matching the section's expected type.
    """
    # Validate the section name against GlobalSettings fields
    valid_sections = GlobalSettings.__fields__.keys()
    if section not in valid_sections:
        raise HTTPException(
            status_code=404,
            detail=f"Section '{section}' not found in GlobalSettings.",
        )

    data = await request.json()
    write_settings_section(section, data)
    logger.info("Section '%s' updated by user '%s'", section, user.username)
    return data


# ===========================================================================
# Version history and rollback
# ===========================================================================

@router.get("/global/settings//history/{section}")
async def get_section_history(
    section: str,
    user: CodxUser = Depends(is_admin_user),
    manager: GlobalSettingsManager = Depends(get_settings_manager),
) -> List[SectionVersion]:
    """
    List available version snapshots for a settings section, newest first.

    Args:
        section: Section name (e.g. 'ai_models', 'plugins').
    """
    history = manager.list_history(section)
    logger.info("Listing history for section '%s': %d entries found.", section, len(history))
    return history


@router.get("/global/settings//history/{section}/{timestamp}")
async def get_section_version(
    section: str,
    timestamp: str,
    user: CodxUser = Depends(is_admin_user),
    manager: GlobalSettingsManager = Depends(get_settings_manager),
) -> Any:
    """
    Retrieve the content of a specific version snapshot.

    Args:
        section: Section name.
        timestamp: Version timestamp (stem of the snapshot filename).
    """
    version_data = manager.get_version(section, timestamp)
    if version_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version '{timestamp}' not found for section '{section}'.",
        )
    return version_data


@router.post("/global/settings//history/{section}/{timestamp}/rollback")
async def rollback_section(
    section: str,
    timestamp: str,
    user: CodxUser = Depends(is_admin_user),
    manager: GlobalSettingsManager = Depends(get_settings_manager),
) -> dict:
    """
    Rollback a settings section to a specific historical version.

    The current state is preserved as a new snapshot before rolling back.

    Args:
        section: Section name.
        timestamp: Version timestamp to restore.
    """
    success = manager.rollback(section, timestamp)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot rollback: version '{timestamp}' not found for section '{section}'.",
        )

    # Refresh in-memory settings after rollback
    read_global_settings()
    logger.info(
        "Section '%s' rolled back to version '%s' by user '%s'.",
        section, timestamp, user.username,
    )
    return {"message": f"Section '{section}' rolled back to version '{timestamp}' successfully."}


# ===========================================================================
# Plugins — kept from original router
# ===========================================================================

@router.get("/global/settings//plugins")
async def read_plugins(
    user: CodxUser = Depends(is_admin_user),
) -> List[Plugin]:
    """List all registered plugins."""
    plugin_manager = PluginManager()
    return plugin_manager.list_plugins()


@router.post("/global/settings//plugins")
async def add_plugin(
    request: Request,
    user: CodxUser = Depends(is_admin_user),
) -> dict:
    """Add a new plugin."""
    plugin_manager = PluginManager()
    plugin_data = await request.json()
    plugin = Plugin(**plugin_data)
    plugin_manager.add_plugin(plugin)
    return {"message": "Plugin added successfully"}


@router.delete("/global/settings//plugins/{plugin_name}")
async def remove_plugin(
    plugin_name: str,
    user: CodxUser = Depends(is_admin_user),
) -> dict:
    """Remove a plugin by name."""
    plugin_manager = PluginManager()
    plugin_manager.remove_plugin(plugin_name)
    return {"message": "Plugin removed successfully"}


@router.post("/global/settings//plugins/{plugin_id}/exec")
async def exec_plugin(
    plugin_id: str,
    request: Request,
    user: CodxUser = Depends(is_admin_user),
) -> dict:
    """Execute a plugin by plugin_id."""
    codx_junior_session = request.state.codx_junior_session
    settings = codx_junior_session.settings
    plugin_manager = PluginManager(project_settings=settings, user=user)
    context = await request.json()
    result = await plugin_manager.exec_plugin(plugin_id=plugin_id, context=context)
    return {"message": "Plugin executed successfully", "result": result}


@router.get("/global/settings//plugins/load_from_file")
async def load_plugins_from_file(
    request: Request,
    user: CodxUser = Depends(is_admin_user),
) -> dict:
    """Load plugins from a file path provided as a query parameter."""
    plugin_manager = PluginManager()
    file_path = request.query_params.get("file_path")
    plugin_manager.load_from_file(file_path)
    return {"message": "Plugins loaded from file successfully"}