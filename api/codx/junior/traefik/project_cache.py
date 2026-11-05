"""
Project Traefik-rule cache.

Project rules live in each project's ``.codx/project.json`` (so they travel
with the project to another codx-junior instance).  Traefik, however, polls
``GET /api/traefik/config`` every 10 seconds with a 5 second timeout, and a
full project discovery can take much longer than that on a cold start.

This module keeps a small snapshot of every project's rules:

* in memory for fast reads;
* on disk (``<config>/traefik/project_rules.json``) so a restart does not
  silently drop the published project routes while discovery warms up.

``project.json`` remains the source of truth.  The snapshot is refreshed from
the discovery cache in a background thread, and updated immediately whenever a
project's settings are saved through the API.
"""

import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from codx.junior.project.project_discover import (
    find_all_projects,
    get_all_projects_snapshot,
    update_project_snapshot,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

CONFIG_FOLDER = os.environ.get(
    "CODX_JUNIOR_CONFIG_FOLDER", os.environ.get("HOME", "/root")
)
CACHE_DIR = os.path.join(CONFIG_FOLDER, "traefik")
CACHE_FILE = os.path.join(CACHE_DIR, "project_rules.json")

# How long a snapshot is considered fresh before a background refresh starts.
CACHE_TTL_SECONDS = 30.0

_lock = threading.Lock()
_cache: Optional[Dict[str, Any]] = None
_cache_at: float = 0.0
_refreshing: bool = False


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def _empty_snapshot() -> Dict[str, Any]:
    return {"version": 1, "updated_at": None, "projects": {}}


def _read_cache_file() -> Dict[str, Any]:
    """Read the persisted snapshot; never raise on a corrupt/missing file."""
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return _empty_snapshot()
        data.setdefault("projects", {})
        return data
    except FileNotFoundError:
        return _empty_snapshot()
    except Exception as ex:  # pragma: no cover - defensive
        logger.warning("Cannot read Traefik project-rules cache %s: %s", CACHE_FILE, ex)
        return _empty_snapshot()


def _write_cache_file(data: Dict[str, Any]) -> None:
    """Atomically replace the persisted snapshot."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix="project_rules.", suffix=".tmp", dir=CACHE_DIR
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.replace(tmp_path, CACHE_FILE)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as ex:  # pragma: no cover - best effort
        logger.warning("Cannot write Traefik project-rules cache %s: %s", CACHE_FILE, ex)


def _rule_dict(rule: Any) -> Dict[str, Any]:
    """Serialize a rule whether it is a model or an already-serialized dict."""
    if hasattr(rule, "model_dump"):
        return rule.model_dump(mode="json")
    if isinstance(rule, dict):
        return dict(rule)
    return {}


def _project_entry(settings: Any) -> Dict[str, Any]:
    project_id = getattr(settings, "project_id", "") or ""
    return {
        "project_id": project_id,
        "project_name": getattr(settings, "project_name", "") or project_id,
        "rules": [_rule_dict(rule) for rule in (getattr(settings, "traefik_rules", None) or [])],
    }


# ---------------------------------------------------------------------------
# Snapshot lifecycle
# ---------------------------------------------------------------------------


def _ensure_loaded() -> Dict[str, Any]:
    """Load the persisted snapshot once, lazily."""
    global _cache, _cache_at
    with _lock:
        if _cache is None:
            _cache = _read_cache_file()
            # Force a refresh on the first read: the file may be from a previous
            # run and projects may have changed since then.
            _cache_at = 0.0
        return _cache


def _refresh_from_discovery() -> Dict[str, Any]:
    """
    Rebuild the snapshot from the project discovery cache.

    If discovery has not run yet, ``find_all_projects()`` starts/joins it.  This
    function is only called from a background thread or an admin endpoint, never
    from the Traefik provider poll.
    """
    global _cache, _cache_at

    projects = get_all_projects_snapshot()
    if projects is None:
        logger.info("Traefik project-rules cache: waiting for project discovery")
        projects = find_all_projects()

    if projects is None:
        return _ensure_loaded()

    snapshot = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "projects": {
            project_id: _project_entry(settings)
            for project_id, settings in projects.items()
            if getattr(settings, "project_id", None)
        },
    }

    with _lock:
        _cache = snapshot
        _cache_at = time.time()

    _write_cache_file(snapshot)
    return snapshot


def _refresh_in_thread() -> None:
    global _refreshing, _cache_at
    try:
        _refresh_from_discovery()
    except Exception as ex:  # pragma: no cover - defensive
        logger.warning("Traefik project-rules cache refresh failed: %s", ex)
    finally:
        with _lock:
            _refreshing = False
            # Avoid a refresh thread on every poll when discovery keeps failing.
            if _cache_at == 0.0:
                _cache_at = time.time()


def _trigger_background_refresh() -> None:
    global _refreshing
    with _lock:
        if _refreshing:
            return
        _refreshing = True
    thread = threading.Thread(
        target=_refresh_in_thread,
        name="traefik-project-rules-refresh",
        daemon=True,
    )
    thread.start()


def get_project_rules_snapshot() -> Dict[str, Any]:
    """
    Return the current project-rules snapshot.

    The snapshot is returned immediately.  When it is older than
    ``CACHE_TTL_SECONDS`` a refresh is started in the background, so the
    Traefik poll never waits for project discovery.
    """
    snapshot = _ensure_loaded()
    if time.time() - _cache_at > CACHE_TTL_SECONDS:
        _trigger_background_refresh()
    return snapshot


def get_project_rule_sets() -> List[Dict[str, Any]]:
    """Return the snapshot's project entries as a list."""
    snapshot = get_project_rules_snapshot()
    return list((snapshot.get("projects") or {}).values())


def get_project_rules(project_id: str) -> Optional[Dict[str, Any]]:
    """Return one project's entry from the snapshot, if present."""
    if not project_id:
        return None
    snapshot = get_project_rules_snapshot()
    return (snapshot.get("projects") or {}).get(project_id)


def refresh_project_rules(wait: bool = False) -> Dict[str, Any]:
    """
    Refresh the project-rules snapshot.

    Args:
        wait: When True, block until discovery finishes (admin endpoints only).
              When False, refresh in a background thread.
    """
    if wait:
        return _refresh_from_discovery()
    _trigger_background_refresh()
    return _ensure_loaded()


def update_project_rules(settings: Any) -> Dict[str, Any]:
    """
    Update one project's entry immediately (after its settings were saved).

    This keeps the Traefik config in sync without re-running discovery.
    """
    global _cache, _cache_at

    snapshot = _ensure_loaded()
    entry = _project_entry(settings)
    project_id = entry.get("project_id")
    if not project_id:
        return snapshot

    projects = dict(snapshot.get("projects") or {})
    projects[project_id] = entry
    snapshot = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "projects": projects,
    }

    with _lock:
        _cache = snapshot
        _cache_at = time.time()

    _write_cache_file(snapshot)
    update_project_snapshot(settings)
    return snapshot


def invalidate_project_rules() -> None:
    """Mark the snapshot stale and schedule a refresh."""
    global _cache_at
    with _lock:
        _cache_at = 0.0
    _trigger_background_refresh()
