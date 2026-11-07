"""
Durable download-directory mapping for browser sessions.

A session maps a project folder for its downloads (``session.downloads_path`` on
the host, ``session.downloads_mount`` inside the container).  Telling the running
browser about it through CDP is **not** enough:

``Browser.setDownloadBehavior`` is scoped to the DevTools client that sends it,
and Chromium drops the value as soon as that client detaches.  Every browser tool
call opens its own connection and closes it again (``Browser.close`` ->
``playwright.stop()``), and a download the user starts in the live VNC view has
no DevTools client at all — so the file always fell back to Chromium's default
directory (``$HOME/Downloads`` inside ``/config``, the *profile* folder), never
into the mapped project folder.

The mapping must therefore exist in the browser's own persisted state, which is
read at launch.  The profile folder is bind mounted at ``/config``, which is the
container's ``$HOME``, so everything can be written from the API side before the
container starts:

- ``download.default_directory`` / ``savefile.default_directory`` in the profile
  ``Preferences`` (the setting behind *Settings → Downloads → Location*), with
  ``download.directory_upgrade`` and ``prompt_for_download`` so Chromium keeps
  the value and never opens a "save as" dialog;
- ``<HOME>/Downloads`` symlinked to the mapped folder, because that is the
  fallback Chromium uses when no preference is set.

Both are idempotent and survive restarts (cookies, logins and downloads folder
are re-read from the same mounted profile).

Example:
    >>> apply_download_settings("/sessions/1/chromium_profile", "/downloads")  # doctest: +SKIP
    {'download_dir': '/downloads', 'preferences': ['/sessions/1/.../Preferences'], 'symlink': '/sessions/1/chromium_profile/Downloads', 'changed': True}
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Session sub folder holding the Chromium profile (mounted at ``/config``).
PROFILE_FOLDER = "chromium_profile"
#: Folder Chromium falls back to when no download directory is configured.
DOWNLOADS_FOLDER = "Downloads"

#: Chromium user-data dirs seen in the browser images, relative to ``$HOME``.
PROFILE_DIRS = (
    (".config", "chromium"),
    (".config", "google-chrome"),
    (".config", "chrome"),
    ("chromium",),
)
#: Canonical (Debian chromium) profile, used to seed a fresh session.
CANONICAL_PROFILE = (".config", "chromium", "Default")


def preferences_patch(download_dir: str) -> Dict[str, Any]:
    """
    Build the ``Preferences`` fragment that sets the browser download folder.

    Args:
        download_dir: Container path of the mapped downloads folder.

    Returns:
        Dict[str, Any]: Nested preferences to merge into ``Preferences``.

    Example:
        >>> preferences_patch("/downloads")["download"]["default_directory"]
        '/downloads'
    """
    return {
        "download": {
            # Setting behind "Settings -> Downloads -> Location"
            "default_directory": download_dir,
            # Tells Chromium the value is authoritative (no silent migration)
            "directory_upgrade": True,
            # Never open a "save as" dialog: it would defeat the mapping
            "prompt_for_download": False,
        },
        # "Save page as" / PDFs use their own pref
        "savefile": {"default_directory": download_dir},
    }


def _deep_merge(target: Dict[str, Any], patch: Dict[str, Any]) -> bool:
    """
    Merge *patch* into *target* in place.

    Args:
        target: Preferences read from disk.
        patch: Preferences to enforce.

    Returns:
        bool: True when at least one value changed (nothing else is touched).

    Example:
        >>> data = {"download": {"default_directory": "/old"}, "other": 1}
        >>> _deep_merge(data, preferences_patch("/new"))
        True
        >>> data["other"]
        1
    """
    changed = False
    for key, value in patch.items():
        current = target.get(key)
        if isinstance(value, dict):
            if not isinstance(current, dict):
                target[key] = dict(value)
                changed = True
            elif _deep_merge(current, value):
                changed = True
        elif current != value:
            target[key] = value
            changed = True
    return changed


def _read_preferences(path: str) -> Dict[str, Any]:
    """Read a ``Preferences`` file, returning an empty dict when unusable."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as ex:
        # A corrupt profile must not block the session: start from scratch is
        # worse than keeping the file, so hand back an empty mapping and skip.
        logger.warning("Could not read browser preferences '%s': %s", path, ex)
        return {}


def _write_preferences(path: str, payload: Dict[str, Any]) -> bool:
    """Write *payload* to *path* atomically (Chromium may be reading it)."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp_path = f"{path}.codx.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception as ex:
        logger.warning("Could not write browser preferences '%s': %s", path, ex)
        return False


def preferences_paths(profile_path: str) -> List[str]:
    """
    Return the ``Preferences`` files where the download directory must be set.

    Existing files always win (whatever the image chose as user-data-dir).  On a
    fresh session the canonical Chromium location is returned so the very first
    launch already sees the setting.

    Args:
        profile_path: Host folder mounted at the container's ``/config``.

    Returns:
        List[str]: Absolute ``Preferences`` paths to patch.

    Example:
        >>> preferences_paths("/tmp/new-profile")  # doctest: +SKIP
        ['/tmp/new-profile/.config/chromium/Default/Preferences']
    """
    found: List[str] = []
    for parts in PROFILE_DIRS:
        base = os.path.join(profile_path, *parts)
        try:
            entries = sorted(os.listdir(base))
        except OSError:
            continue
        for name in entries:
            candidate = os.path.join(base, name, "Preferences")
            if os.path.isfile(candidate):
                found.append(candidate)
        # ``--user-data-dir`` pointing straight at the user-data directory
        direct = os.path.join(base, "Preferences")
        if os.path.isfile(direct):
            found.append(direct)

    if found:
        return found
    return [os.path.join(profile_path, *CANONICAL_PROFILE, "Preferences")]


def link_default_downloads(profile_path: str, download_dir: str) -> Optional[str]:
    """
    Point ``<HOME>/Downloads`` at *download_dir* (Chromium's default folder).

    The profile folder is the container's ``$HOME`` (``/config``), so this links
    the fallback download folder the browser uses when no preference applies.
    The link target is a container path, so it dangles on the host on purpose.

    An existing folder or link is never replaced: it may hold files downloaded
    before the mapping existed.

    Args:
        profile_path: Host folder mounted at ``/config``.
        download_dir: Container path of the mapped downloads folder.

    Returns:
        Optional[str]: The link path when it was created, otherwise None.

    Example:
        >>> link_default_downloads("/tmp/profile", "/downloads")  # doctest: +SKIP
        '/tmp/profile/Downloads'
    """
    link_path = os.path.join(profile_path, DOWNLOADS_FOLDER)
    if os.path.lexists(link_path):
        return None
    try:
        os.symlink(download_dir, link_path)
    except OSError as ex:
        logger.warning("Could not link '%s' -> '%s': %s", link_path, download_dir, ex)
        return None
    return link_path


def apply_download_settings(profile_path: str, download_dir: str) -> Dict[str, Any]:
    """
    Make *download_dir* the browser's default download directory.

    Must run **before** the container starts (Chromium reads the profile at
    launch).  Everything is idempotent, so it can be re-applied on restarts.

    Args:
        profile_path: Host folder mounted at the container's ``/config``.
        download_dir: Container path of the mapped downloads folder
            (``session.downloads_mount``).

    Returns:
        Dict[str, Any]: ``download_dir``, ``preferences`` (patched files),
        ``symlink`` (``<HOME>/Downloads`` when created) and ``changed``.

    Example:
        >>> report = apply_download_settings("/tmp/profile", "/downloads")  # doctest: +SKIP
        >>> report["download_dir"]
        '/downloads'
    """
    report: Dict[str, Any] = {
        "download_dir": download_dir,
        "preferences": [],
        "symlink": None,
        "changed": False,
    }

    download_dir = (download_dir or "").strip()
    if not profile_path or not download_dir:
        return report

    os.makedirs(profile_path, exist_ok=True)
    patch = preferences_patch(download_dir)

    for path in preferences_paths(profile_path):
        exists = os.path.isfile(path)
        # Nothing to merge: never turn a corrupt file into a Preferences stub
        if exists and not _read_preferences(path) and os.path.getsize(path) > 0:
            continue
        data = _read_preferences(path)
        changed = _deep_merge(data, patch)
        if (not exists) or changed:
            if not _write_preferences(path, data):
                continue
            report["changed"] = True
        report["preferences"].append(path)

    report["symlink"] = link_default_downloads(profile_path, download_dir)

    logger.info(
        "Browser downloads mapped to '%s' (preferences: %s, symlink: %s)",
        download_dir,
        ", ".join(report["preferences"]) or "-",
        report["symlink"] or "-",
    )
    return report


# Made with ❤️ by codx-junior