"""
Saved computers: commit a running desktop into a reusable library entry.

A user can customize a running Linux/Kasmweb desktop (install packages, change
settings, save files in the container home) and then **save** it.  The save
operation creates a Docker image from the container and a project-scoped library
record with:

* the resulting image reference;
* the live-view/control profile (Selkies vs KasmVNC, port, scheme, strip prefix);
* a preview screenshot;
* optional archived home/profile data (for bind-mounted LinuxServer ``/config``);
* resource/env defaults so a new session starts with the same shape.

Other users of the same project can then pick the saved entry from the image
library and start a new session from it.  The Docker image lives on the same
host; multi-host deployments would need a registry push (not implemented here).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

LIBRARY_FOLDER = "computer_library"
ITEM_FILE = "item.json"
PROFILE_ARCHIVE = "profile.tar.gz"
PREVIEW_FILE = "preview.png"
#: Keep saved metadata at 0600 (it can describe private environments).
ITEM_MODE = 0o600
#: Profile/home archive cap; can be raised for large IDE caches.
DEFAULT_MAX_PROFILE_BYTES = int(
    os.environ.get("CODX_COMPUTER_SAVE_MAX_PROFILE_BYTES", str(2 * 1024 * 1024 * 1024))
)
#: Directories that are caches, not user customization.
PROFILE_EXCLUDES = {
    ".cache", "Cache", "Code Cache", "GPUCache", "CachedData",
    "CachedProfilesData", "ShaderCache", "logs", "log", ".npm/_cacache",
    ".local/share/Trash", "Trash",
}


class SavedComputer(BaseModel):
    """A reusable computer image stored in the project library."""

    id: str = Field(description="Library item id")
    name: str = Field(description="Human-readable computer name")
    description: Optional[str] = Field(default=None, description="Description")
    kind: str = Field(default="linux", description="Session kind (linux)")
    image: str = Field(description="Committed Docker image reference")
    provider: str = Field(default="linuxserver", description="Image provider")
    base_image: Optional[str] = Field(default=None, description="Image the session started from")
    live_view: str = Field(default="selkies", description="selkies, kasmvnc or screenshot")
    live_port: Optional[int] = Field(default=None, description="Live-view container port")
    live_scheme: str = Field(default="http", description="http or https")
    strip_prefix: bool = Field(default=False, description="Strip the public path prefix")
    control: str = Field(default="docker", description="AI control channel")
    viewer_user: Optional[str] = Field(default=None, description="KasmVNC login user")
    source_session_id: Optional[str] = Field(default=None, description="Session it was saved from")
    source_session_name: Optional[str] = Field(default=None, description="Source session name")
    created_by: Optional[str] = Field(default=None, description="Username that saved it")
    project_id: Optional[str] = Field(default=None, description="Owning project id")
    project_name: Optional[str] = Field(default=None, description="Owning project name")
    created_at: str = Field(description="ISO creation timestamp")
    image_size_bytes: Optional[int] = Field(default=None, description="Committed image size")
    profile_size_bytes: Optional[int] = Field(default=None, description="Archived profile size")
    include_profile: bool = Field(default=False, description="Whether home/profile data was archived")
    has_profile: bool = Field(default=False, description="Whether a profile archive exists")
    has_preview: bool = Field(default=False, description="Whether a preview image exists")
    defaults: Dict[str, Any] = Field(default_factory=dict, description="Resource/env defaults")
    tags: List[str] = Field(default_factory=list, description="Search tags")
    visibility: str = Field(default="project", description="project or global")
    status: str = Field(default="ready", description="ready or error")
    error: Optional[str] = Field(default=None, description="Save error, when status=error")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=False)


class SavedComputerListResponse(BaseModel):
    count: int
    computers: List[SavedComputer]


class SaveComputerRequest(BaseModel):
    name: str = Field(description="Name shown in the library")
    description: Optional[str] = Field(default=None, description="Optional description")
    include_profile: bool = Field(
        default=False,
        description="Archive the desktop home/profile (may contain logins and secrets)",
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str, fallback: str = "computer") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return (slug[:40] or fallback)


class SavedComputerLibrary:
    """Filesystem-backed project library of saved computers."""

    def __init__(self, codx_path: str, project_id: Optional[str] = None, project_name: Optional[str] = None):
        self.codx_path = codx_path
        self.project_id = project_id
        self.project_name = project_name
        self.root = os.path.join(codx_path, LIBRARY_FOLDER)
        os.makedirs(self.root, exist_ok=True)

    def item_folder(self, item_id: str) -> str:
        return os.path.join(self.root, item_id)

    def item_file(self, item_id: str) -> str:
        return os.path.join(self.item_folder(item_id), ITEM_FILE)

    def profile_path(self, item_id: str) -> str:
        return os.path.join(self.item_folder(item_id), PROFILE_ARCHIVE)

    def preview_path(self, item_id: str) -> str:
        return os.path.join(self.item_folder(item_id), PREVIEW_FILE)

    def list(self) -> List[SavedComputer]:
        items = []
        if not os.path.isdir(self.root):
            return items
        for folder in sorted(Path(self.root).iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
            if not folder.is_dir() or folder.name == ".trash":
                continue
            item = self._read_item(str(folder / ITEM_FILE))
            if item:
                items.append(item)
        return items

    def get(self, item_id: str) -> Optional[SavedComputer]:
        if not item_id:
            return None
        return self._read_item(self.item_file(item_id))

    def save(self, item: SavedComputer) -> SavedComputer:
        folder = self.item_folder(item.id)
        os.makedirs(folder, exist_ok=True)
        try:
            os.chmod(folder, 0o700)
        except OSError:
            pass
        tmp = self.item_file(item.id) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(item.to_dict(), handle, indent=2, ensure_ascii=False)
        os.replace(tmp, self.item_file(item.id))
        try:
            os.chmod(self.item_file(item.id), ITEM_MODE)
        except OSError:
            pass
        return item

    def delete(self, item_id: str, remove_image: bool = True) -> bool:
        item = self.get(item_id)
        if not item:
            return False
        if remove_image and item.image:
            try:
                subprocess.run(
                    ["docker", "rmi", item.image],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except Exception as ex:
                logger.warning("Could not remove saved computer image %s: %s", item.image, ex)
        folder = self.item_folder(item_id)
        # Delete the metadata, preview and potentially large profile archive;
        # a "removed" saved computer should not keep multi-GB leftovers.
        shutil.rmtree(folder, ignore_errors=True)
        return True

    @staticmethod
    def _read_item(path: str) -> Optional[SavedComputer]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return SavedComputer(**json.load(handle))
        except FileNotFoundError:
            return None
        except Exception as ex:
            logger.warning("Could not read saved computer '%s': %s", path, ex)
            return None


def saved_library_for(manager) -> SavedComputerLibrary:
    """Return the project library owned by a BrowserManager/ComputerManager."""
    settings = manager.settings
    return SavedComputerLibrary(
        codx_path=settings.codx_path,
        project_id=getattr(settings, "project_id", None),
        project_name=getattr(settings, "project_name", None),
    )


def saved_image_name(project_name: str, name: str) -> str:
    """Build a unique local Docker image reference for a saved computer."""
    repository = f"codx-saved/{_slug(project_name, 'project')}/{_slug(name)}"
    tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    return f"{repository}:{tag}"


def _docker_json(args: List[str]) -> Any:
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "docker command failed").strip()[:500])
    text = (result.stdout or "").strip()
    return json.loads(text) if text else None


def image_size(image: str) -> Optional[int]:
    """Return the committed image size in bytes."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image, "--format", "{{.Size}}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0:
            return int((result.stdout or "").strip())
    except Exception as ex:
        logger.debug("Could not inspect saved image size: %s", ex)
    return None


def _iter_profile_files(root: str):
    """Yield profile files, skipping caches and symlink escapes."""
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PROFILE_EXCLUDES]
        for name in files:
            path = os.path.join(current, name)
            relative = os.path.relpath(path, root)
            if any(part in PROFILE_EXCLUDES for part in Path(relative).parts):
                continue
            if os.path.islink(path):
                continue
            yield path, relative


def archive_profile(profile_path: str, target: str, max_bytes: int = DEFAULT_MAX_PROFILE_BYTES) -> int:
    """Archive a LinuxServer profile/home directory, excluding caches."""
    total = 0
    for path, _relative in _iter_profile_files(profile_path):
        try:
            total += os.path.getsize(path)
        except OSError:
            continue
        if total > max_bytes:
            raise ValueError(
                f"Profile is larger than the {max_bytes // (1024 * 1024)} MB save limit; "
                "remove caches or raise CODX_COMPUTER_SAVE_MAX_PROFILE_BYTES"
            )
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with tarfile.open(target, "w:gz") as archive:
        for path, relative in _iter_profile_files(profile_path):
            try:
                archive.add(path, arcname=relative)
            except OSError as ex:
                logger.debug("Skipping profile file %s: %s", path, ex)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return os.path.getsize(target)


def restore_profile(item: SavedComputer, library: SavedComputerLibrary, profile_path: str) -> None:
    """Extract a saved profile archive into a fresh session profile folder."""
    archive_path = library.profile_path(item.id)
    if not item.has_profile or not os.path.isfile(archive_path):
        return
    os.makedirs(profile_path, exist_ok=True)
    base = os.path.realpath(profile_path)
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target = os.path.realpath(os.path.join(base, member.name))
            if target != base and not target.startswith(base + os.sep):
                logger.warning("Skipping unsafe saved profile member: %s", member.name)
                continue
            if member.issym() or member.islnk():
                continue
            archive.extract(member, path=profile_path)
    logger.info("Restored saved computer profile for %s", item.id[:8])


async def save_session_to_library(
    manager,
    session,
    name: Optional[str] = None,
    description: Optional[str] = None,
    include_profile: bool = False,
    created_by: Optional[str] = None,
) -> SavedComputer:
    """
    Commit *session*'s container and add it to the project library.

    Only Linux desktop containers are supported.  Kasmweb's home is part of the
    container commit; LinuxServer's ``/config`` is a bind mount and is optionally
    archived separately.  Windows/macOS VM state lives on a VM disk volume and
    is intentionally rejected until a disk-snapshot flow exists.
    """
    if not session:
        raise ValueError("Session not found")
    if session.kind != "linux":
        raise ValueError(
            "Only Linux desktop containers can be saved to the library. "
            "Windows/macOS VM disks need a separate snapshot flow."
        )
    if not session.container_id:
        raise ValueError("The session has no container to save")
    if session.status not in ("running", "stopped"):
        raise ValueError(f"Session cannot be saved while status is '{session.status}'")

    name = (name or session.name or f"Saved {session.kind_label}").strip()
    description = (description or "").strip() or None
    library = saved_library_for(manager)
    item_id = str(uuid.uuid4())
    image = saved_image_name(manager.settings.project_name or "project", name)
    folder = library.item_folder(item_id)
    os.makedirs(folder, exist_ok=True)
    preview = False
    profile_size = None

    # Preview first: the committed image does not help the UI, and the runtime
    # is still live here.
    try:
        runtime = await manager.get_runtime(session)
        shot = await runtime.screenshot(include_text=False, max_width=1280, actor="system", log=False)
        data_uri = (shot or {}).get("image")
        if data_uri and "," in data_uri:
            import base64
            preview_path = library.preview_path(item_id)
            with open(preview_path, "wb") as handle:
                handle.write(base64.b64decode(data_uri.split(",", 1)[1]))
            try:
                os.chmod(preview_path, 0o600)
            except OSError:
                pass
            preview = True
    except Exception as ex:
        logger.info("Could not capture preview for saved computer %s: %s", session.id[:8], ex)

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "commit", "--pause=true", session.container_id, image],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "docker commit failed").strip()[:800])
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise

    if include_profile and (session.image_provider or "").lower() != "kasmweb":
        profile_path = getattr(session, "profile_path", None) or manager.docker_manager._desktop_profile_path(session.id)
        if profile_path and os.path.isdir(profile_path):
            try:
                profile_size = await asyncio.to_thread(
                    archive_profile,
                    profile_path,
                    library.profile_path(item_id),
                )
            except Exception:
                shutil.rmtree(folder, ignore_errors=True)
                try:
                    await asyncio.to_thread(
                        subprocess.run, ["docker", "rmi", image], capture_output=True, timeout=60
                    )
                except Exception:
                    pass
                raise

    item = SavedComputer(
        id=item_id,
        name=name,
        description=description,
        kind=session.kind,
        image=image,
        provider=(session.image_provider or "linuxserver"),
        base_image=session.image,
        live_view=(session.live_view or "selkies"),
        live_port=session.live_port,
        live_scheme=(session.live_scheme or "http"),
        strip_prefix=bool(session.strip_prefix),
        control=(session.control or "docker"),
        viewer_user=session.viewer_user,
        source_session_id=session.id,
        source_session_name=session.name,
        created_by=created_by,
        project_id=getattr(manager.settings, "project_id", None),
        project_name=getattr(manager.settings, "project_name", None),
        created_at=_now(),
        image_size_bytes=await asyncio.to_thread(image_size, image),
        profile_size_bytes=profile_size,
        include_profile=bool(include_profile),
        has_profile=bool(profile_size),
        has_preview=preview,
        defaults={
            "cpu_cores": session.cpu_cores,
            "ram_size": session.ram_size,
            "disk_size": session.disk_size,
            "shm_size": session.shm_size,
            "desktop_width": session.desktop_width,
            "desktop_height": session.desktop_height,
            "extra_env": dict(session.extra_env or {}),
        },
        tags=["saved", session.kind, session.image_provider or "linuxserver"],
        visibility="project",
        status="ready",
    )
    library.save(item)
    manager.log_activity(
        session,
        actor="system",
        action="save_library",
        params={"name": name, "image": image, "include_profile": include_profile},
    )
    logger.info("Saved computer '%s' (%s) from session %s", name, image, session.id[:8])
    return item
