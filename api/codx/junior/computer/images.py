"""
Image library for computer sessions.

Computer desktops are not one image: LinuxServer.io publishes many ``webtop``
flavours (Ubuntu/Debian/Fedora/Arch/Alpine with XFCE/KDE/MATE/i3/LXQt) and
Kasmweb publishes desktops plus hundreds of application images (Firefox,
Chrome, VS Code, LibreOffice, Kali...).  This module is the single catalog the
UI and the session manager use:

* a curated, offline catalog with the metadata the UI needs (name, category,
  description, screenshot/logo, provider, desktop transport);
* optional live enrichment and tag discovery from the Docker Hub and
  LinuxServer APIs (cached; network failures fall back to the catalog);
* :func:`resolve_image` which turns an image reference into the Docker run
  profile (KasmVNC on 6901 HTTPS, LinuxServer Selkies on 3000 HTTP, or a
  generic image with screenshot-only viewing).

The catalog is intentionally curated: listing all 200+ Kasmweb repositories
would bury the useful desktops, and every entry here has a verified transport.
A user can still type any image reference in the selector's custom field.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

#: Kasm Stable tag used when the caller does not specify one.
DEFAULT_KASM_TAG = (os.environ.get("CODX_COMPUTER_KASM_TAG") or "1.19.0").strip()
#: Default LinuxServer webtop flavour.
DEFAULT_LINUXSERVER_TAG = (os.environ.get("CODX_COMPUTER_WEBTOP_TAG") or "debian-kde").strip()
LINUXSERVER_IMAGE = "lscr.io/linuxserver/webtop"
KASMWEB_REGISTRY = "kasmweb"
KASM_SCREENSHOT_BASE = (
    "https://f.hubspotusercontent30.net/hubfs/5856039/dockerhub/image-screenshots"
)
LS_WEBTOP_LOGO = (
    "https://raw.githubusercontent.com/linuxserver/docker-templates/master/"
    "linuxserver.io/img/webtop-logo.png"
)
KASM_DOCS = "https://docs.kasm.com/docs/how-to/workspaces-sessions/container-workspace/custom-images"
LS_WEBTOP_DOCS = "https://docs.linuxserver.io/images/docker-webtop/"

CACHE_TTL_SECONDS = 3600
TAGS_TTL_SECONDS = 900


class ComputerImage(BaseModel):
    """One selectable image in the library."""

    id: str = Field(description="Stable catalog id (provider:repository:tag)")
    provider: str = Field(description="linuxserver, kasmweb or custom")
    repository: str = Field(description="Image repository (without registry)")
    image: str = Field(description="Full Docker image reference including the default tag")
    tag: str = Field(description="Default tag")
    default_tag: str = Field(description="Default tag")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="", description="Short description")
    category: str = Field(default="Desktop", description="UI category")
    icon_url: Optional[str] = Field(default=None, description="Small logo")
    screenshot_url: Optional[str] = Field(default=None, description="Preview image")
    docs_url: Optional[str] = Field(default=None, description="Upstream documentation")
    pull_count: Optional[int] = Field(default=None, description="Docker Hub pulls (when known)")
    updated_at: Optional[str] = Field(default=None, description="Last update (when known)")
    live_view: str = Field(description="selkies, kasmvnc or screenshot")
    live_port: Optional[int] = Field(default=None, description="Container port of the live view")
    live_scheme: str = Field(default="http", description="http or https")
    strip_prefix: bool = Field(default=False, description="Strip the public path prefix when proxying")
    control: str = Field(default="docker", description="AI control channel: docker or vnc")
    viewer_user: Optional[str] = Field(default=None, description="Viewer login user (KasmVNC)")
    tags: List[str] = Field(default_factory=list, description="Known/related tags")
    source: str = Field(default="curated", description="curated or live metadata")


class ComputerImageListResponse(BaseModel):
    """Image library response."""

    count: int
    images: List[ComputerImage]


class ComputerImageTag(BaseModel):
    """One selectable tag."""

    name: str
    updated_at: Optional[str] = None


class ComputerImageTagsResponse(BaseModel):
    """Tags available for one repository."""

    provider: str
    repository: str
    default_tag: str
    count: int
    tags: List[ComputerImageTag]


@dataclass(frozen=True)
class ImageSpec:
    """Resolved Docker/live-view profile for an image reference."""

    provider: str
    image: str
    repository: str
    tag: str
    live_view: str
    live_port: Optional[int]
    live_scheme: str
    strip_prefix: bool
    control: str
    viewer_user: Optional[str] = None
    name: Optional[str] = None
    docs_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Curated catalog
# ---------------------------------------------------------------------------
_LINUXSERVER_FLAVORS: List[Tuple[str, str, str]] = [
    ("debian-kde", "Debian KDE", "Debian with KDE Plasma. The codx-junior default."),
    ("ubuntu-xfce", "Ubuntu XFCE", "Ubuntu with XFCE: light, fast and familiar."),
    ("ubuntu-kde", "Ubuntu KDE", "Ubuntu with KDE Plasma."),
    ("ubuntu-mate", "Ubuntu MATE", "Ubuntu with the MATE desktop."),
    ("ubuntu-lxqt", "Ubuntu LXQt", "Very light Ubuntu desktop for small machines."),
    ("ubuntu-i3", "Ubuntu i3", "Tiling window manager for keyboard-driven work."),
    ("debian-xfce", "Debian XFCE", "Debian with XFCE."),
    ("debian-mate", "Debian MATE", "Debian with MATE."),
    ("debian-i3", "Debian i3", "Debian with i3."),
    ("fedora-xfce", "Fedora XFCE", "Fedora with XFCE."),
    ("fedora-kde", "Fedora KDE", "Fedora with KDE Plasma."),
    ("fedora-mate", "Fedora MATE", "Fedora with MATE."),
    ("fedora-i3", "Fedora i3", "Fedora with i3."),
    ("arch-xfce", "Arch XFCE", "Arch Linux with XFCE."),
    ("arch-mate", "Arch MATE", "Arch Linux with MATE."),
    ("arch-i3", "Arch i3", "Arch Linux with i3."),
    ("latest", "Alpine XFCE", "Tiny Alpine desktop with XFCE (LinuxServer publishes it as :latest)."),
    ("alpine-mate", "Alpine MATE", "Tiny Alpine desktop with MATE."),
    ("alpine-i3", "Alpine i3", "Tiny Alpine desktop with i3."),
]

_KASM_DESKTOPS: List[Tuple[str, str, str, str]] = [
    ("desktop", "Kasm Desktop", "Ubuntu Jammy desktop with Chrome and Firefox preinstalled.", "Desktop"),
    ("desktop-deluxe", "Kasm Desktop Deluxe", "Full Ubuntu desktop with the productivity application set.", "Desktop"),
    ("ubuntu-jammy-desktop", "Ubuntu 22.04 Desktop", "Ubuntu Jammy productivity desktop.", "Desktop"),
    ("ubuntu-focal-desktop", "Ubuntu 20.04 Desktop", "Ubuntu Focal productivity desktop.", "Desktop"),
    ("ubuntu-bionic-desktop", "Ubuntu 18.04 Desktop", "Ubuntu Bionic desktop for legacy tools.", "Desktop"),
    ("debian-bookworm-desktop", "Debian 12 Desktop", "Debian Bookworm desktop.", "Desktop"),
    ("debian-bullseye-desktop", "Debian 11 Desktop", "Debian Bullseye desktop.", "Desktop"),
    ("core-ubuntu-jammy", "Ubuntu Jammy (core)", "Minimal Ubuntu Jammy desktop.", "Desktop"),
    ("kali-rolling-desktop", "Kali Rolling Desktop", "Kali Linux desktop with the default tool set.", "Security"),
    ("core-kali-rolling", "Kali Rolling XFCE", "Kali Rolling with XFCE and the metapackage tools.", "Security"),
    ("almalinux-9-desktop", "AlmaLinux 9 Desktop", "RHEL-compatible AlmaLinux 9 desktop.", "Desktop"),
    ("rockylinux-9-desktop", "Rocky Linux 9 Desktop", "RHEL-compatible Rocky Linux 9 desktop.", "Desktop"),
    ("oracle-9-desktop", "Oracle Linux 9 Desktop", "Oracle Linux 9 desktop.", "Desktop"),
    ("opensuse-15-desktop", "openSUSE Leap 15 Desktop", "openSUSE Leap desktop.", "Desktop"),
    ("fedora-37-desktop", "Fedora 37 Desktop", "Fedora desktop image.", "Desktop"),
]

_KASM_APPS: List[Tuple[str, str, str, str]] = [
    ("vs-code", "Visual Studio Code", "VS Code in a disposable desktop.", "Development"),
    ("terminal", "Terminal", "A browser-accessible terminal workspace.", "Development"),
    ("java-dev", "Java Development", "Java toolchain desktop.", "Development"),
    ("sublime-text", "Sublime Text", "Sublime Text editor.", "Development"),
    ("postman", "Postman", "Postman API client.", "Development"),
    ("insomnia", "Insomnia", "Insomnia API client.", "Development"),
    ("firefox", "Firefox", "Firefox in an isolated desktop.", "Browser"),
    ("chrome", "Google Chrome", "Google Chrome in an isolated desktop.", "Browser"),
    ("brave", "Brave", "Brave browser.", "Browser"),
    ("edge", "Microsoft Edge", "Microsoft Edge browser.", "Browser"),
    ("tor-browser", "Tor Browser", "Tor Browser in an isolated desktop.", "Browser"),
    ("libre-office", "LibreOffice", "LibreOffice suite.", "Office"),
    ("only-office", "ONLYOFFICE", "ONLYOFFICE document suite.", "Office"),
    ("thunderbird", "Thunderbird", "Thunderbird mail client.", "Office"),
    ("gimp", "GIMP", "GIMP image editor.", "Media"),
    ("inkscape", "Inkscape", "Inkscape vector editor.", "Media"),
    ("blender", "Blender", "Blender 3D suite.", "Media"),
    ("audacity", "Audacity", "Audacity audio editor.", "Media"),
    ("vlc", "VLC", "VLC media player.", "Media"),
    ("slack", "Slack", "Slack desktop client.", "Communication"),
    ("discord", "Discord", "Discord desktop client.", "Communication"),
    ("teams", "Microsoft Teams", "Microsoft Teams client.", "Communication"),
    ("zoom", "Zoom", "Zoom client.", "Communication"),
    ("signal", "Signal", "Signal desktop client.", "Communication"),
    ("telegram", "Telegram", "Telegram desktop client.", "Communication"),
    ("remmina", "Remmina", "Remote desktop client.", "Utilities"),
    ("filezilla", "FileZilla", "FTP/SFTP client.", "Utilities"),
    ("steam", "Steam", "Steam client (GPU recommended).", "Games"),
]

#: Kasmweb stopped publishing the current stable tag for a handful of legacy
#: images.  They still work, but only under the last release Kasm shipped;
#: pinning them here keeps every catalog card pullable.
_KASM_TAG_OVERRIDES: Dict[str, str] = {
    "ubuntu-focal-desktop": "1.16.1",
    "ubuntu-bionic-desktop": "1.10.0",
    "opensuse-15-desktop": "1.18.0",
    "fedora-37-desktop": "1.15.0",
    "teams": "1.12.0",
}


def _kasm_image(repo: str, tag: Optional[str] = None) -> str:
    return f"{KASMWEB_REGISTRY}/{repo}:{tag or _KASM_TAG_OVERRIDES.get(repo) or DEFAULT_KASM_TAG}"


def _linuxserver_image(tag: str) -> str:
    return f"{LINUXSERVER_IMAGE}:{tag}"


def _linuxserver_entries(with_dynamic: bool = True, refresh: bool = False) -> List[ComputerImage]:
    """Curated webtop flavours, enriched with live tag descriptions."""
    descriptions: Dict[str, str] = {}
    latest: Dict[str, str] = {}
    if with_dynamic:
        try:
            data = _cached_json(
                "linuxserver:webtop",
                lambda: _http_json(
                    "https://api.linuxserver.io/api/v1/images"
                    "?include_config=false&include_deprecated=false"
                ),
                0 if refresh else CACHE_TTL_SECONDS,
            )
            for item in (data or {}).get("data", {}).get("repositories", {}).get("linuxserver", []):
                if item.get("name") != "webtop":
                    continue
                for tag in item.get("tags") or []:
                    name = (tag.get("tag") or "").strip()
                    if name:
                        descriptions[name] = tag.get("desc") or ""
                latest["webtop"] = item.get("version_timestamp") or ""
        except Exception as ex:
            logger.debug("Could not enrich LinuxServer webtop catalog: %s", ex)

    entries = []
    for tag, name, description in _LINUXSERVER_FLAVORS:
        entries.append(ComputerImage(
            id=f"linuxserver:webtop:{tag}",
            provider="linuxserver",
            repository="linuxserver/webtop",
            image=_linuxserver_image(tag),
            tag=tag,
            default_tag=tag,
            name=name,
            description=descriptions.get(tag) or description,
            category="Desktop",
            icon_url=LS_WEBTOP_LOGO,
            screenshot_url=None,
            docs_url=LS_WEBTOP_DOCS,
            updated_at=latest.get("webtop") or None,
            live_view="selkies",
            live_port=3000,
            live_scheme="http",
            strip_prefix=False,
            control="docker",
            tags=[tag, "webtop", "linuxserver", "selkies"],
        ))
    return entries


def _kasm_entries() -> List[ComputerImage]:
    """Curated Kasmweb desktops and applications."""
    entries = []
    for repo, name, description, category in _KASM_DESKTOPS + _KASM_APPS:
        is_desktop = (repo, name, description, category) in _KASM_DESKTOPS
        tag = _KASM_TAG_OVERRIDES.get(repo) or DEFAULT_KASM_TAG
        entries.append(ComputerImage(
            id=f"kasmweb:{repo}:{tag}",
            provider="kasmweb",
            repository=f"kasmweb/{repo}",
            image=_kasm_image(repo, tag),
            tag=tag,
            default_tag=tag,
            name=name,
            description=description,
            category=category,
            icon_url=f"{KASM_SCREENSHOT_BASE}/{repo}.png",
            screenshot_url=f"{KASM_SCREENSHOT_BASE}/{repo}.png",
            docs_url=KASM_DOCS,
            live_view="kasmvnc",
            live_port=6901,
            live_scheme="https",
            strip_prefix=True,
            control="docker",
            viewer_user="kasm_user",
            tags=[repo, tag, "kasmweb", "kasmvnc", "desktop" if is_desktop else "application"],
        ))
    return entries


def all_catalog_images(provider: Optional[str] = None, refresh: bool = False) -> List[ComputerImage]:
    """Return the curated catalog, optionally enriched from upstream APIs."""
    provider = (provider or "").strip().lower() or None
    images: List[ComputerImage] = []
    if provider in (None, "all", "linuxserver", "lscr"):
        images.extend(_linuxserver_entries(with_dynamic=True, refresh=refresh))
    if provider in (None, "all", "kasmweb", "kasm"):
        images.extend(_kasm_entries())
    return images


def list_images(
    provider: Optional[str] = None,
    query: Optional[str] = None,
    category: Optional[str] = None,
    kind: str = "linux",
    refresh: bool = False,
) -> List[ComputerImage]:
    """Filter the catalog by provider, free text and category."""
    if kind and kind not in ("linux", "desktop", ""):
        # Windows/macOS images are provided by dockurr, not this library.
        return []
    images = all_catalog_images(provider=provider, refresh=refresh)
    term = (query or "").strip().lower()
    category = (category or "").strip().lower()
    if category:
        images = [image for image in images if image.category.lower() == category]
    if term:
        images = [
            image for image in images
            if term in image.name.lower()
            or term in image.repository.lower()
            or term in image.description.lower()
            or term in image.category.lower()
            or any(term in tag.lower() for tag in image.tags)
        ]
    return images


def categories(provider: Optional[str] = None) -> List[str]:
    """List distinct categories for the UI chips."""
    seen: List[str] = []
    for image in all_catalog_images(provider=provider):
        if image.category not in seen:
            seen.append(image.category)
    return seen


def find_catalog_image(repository: str, tag: Optional[str] = None) -> Optional[ComputerImage]:
    """Find a catalog entry by repository (and optionally tag).

    The provider is inferred first so a Kasmweb lookup never waits for the
    LinuxServer API (and vice versa).
    """
    repo = (repository or "").strip().lower()
    if "kasmweb/" in repo:
        provider = "kasmweb"
    elif "webtop" in repo:
        provider = "linuxserver"
    else:
        provider = None
    for image in all_catalog_images(provider=provider):
        if image.repository.lower() == repo or image.repository.lower().endswith("/" + repo):
            if tag is None or image.tag == tag:
                return image
    return None


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------
def _split_image(image: str) -> Tuple[str, str]:
    """Split ``repo[:tag]`` (registry-safe; ignores digests)."""
    value = (image or "").strip()
    if "@" in value:
        value = value.split("@", 1)[0]
    last_colon = value.rfind(":")
    slash = value.rfind("/")
    if last_colon > slash:
        return value[:last_colon], value[last_colon + 1:]
    return value, ""


def resolve_image(
    image: Optional[str],
    provider: Optional[str] = None,
    kind: str = "linux",
) -> ImageSpec:
    """
    Resolve an image reference into the Docker/live-view profile.

    Known providers:
      * ``linuxserver/webtop``: Selkies web desktop on 3000 (HTTP, subfolder).
      * ``kasmweb/*``: KasmVNC web desktop on 6901 (HTTPS, strip prefix).
      * anything else: generic container; screenshot/screenshot fallback.

    The Kasm profile is still driven through ``docker exec`` by the X11 agent;
    the HTTPS KasmVNC page is only the human live view.
    """
    raw = (image or "").strip()
    hint = (provider or "").strip().lower()
    if not raw:
        if kind in ("windows", "macos"):
            raw = ""
        elif hint in ("kasmweb", "kasm"):
            raw = _kasm_image("desktop")
        else:
            raw = _linuxserver_image(DEFAULT_LINUXSERVER_TAG)

    lowered = raw.lower()
    if hint in ("kasmweb", "kasm") or lowered.startswith("kasmweb/") or "/kasmweb/" in lowered:
        repository, tag = _split_image(raw)
        repo_name = repository.split("kasmweb/", 1)[-1] if "kasmweb/" in repository else repository
        repository = f"kasmweb/{repo_name}"
        catalog = find_catalog_image(repository)
        # No explicit tag: honour the catalog default, which for legacy images
        # is the last tag Kasm actually published (see _KASM_TAG_OVERRIDES).
        tag = tag or (catalog.default_tag if catalog else DEFAULT_KASM_TAG)
        name = catalog.name if catalog else repo_name.replace("-", " ").title()
        return ImageSpec(
            provider="kasmweb",
            image=f"{repository}:{tag}",
            repository=repository,
            tag=tag,
            live_view="kasmvnc",
            live_port=6901,
            live_scheme="https",
            strip_prefix=True,
            control="docker",
            viewer_user="kasm_user",
            name=name,
            docs_url=KASM_DOCS,
        )

    if hint in ("linuxserver", "lscr") or "linuxserver/webtop" in lowered:
        repository, tag = _split_image(raw)
        tag = tag or DEFAULT_LINUXSERVER_TAG
        catalog = find_catalog_image("linuxserver/webtop", tag)
        return ImageSpec(
            provider="linuxserver",
            image=f"{LINUXSERVER_IMAGE}:{tag}",
            repository="linuxserver/webtop",
            tag=tag,
            live_view="selkies",
            live_port=3000,
            live_scheme="http",
            strip_prefix=False,
            control="docker",
            name=catalog.name if catalog else f"LinuxServer webtop ({tag})",
            docs_url=LS_WEBTOP_DOCS,
        )

    # Unknown image: still run it as a desktop container, but expose only the
    # screenshot fallback until the user picks a known library image.
    repository, tag = _split_image(raw)
    return ImageSpec(
        provider="custom",
        image=raw,
        repository=repository or raw,
        tag=tag or "latest",
        live_view="screenshot",
        live_port=None,
        live_scheme="http",
        strip_prefix=False,
        control="docker",
        name=repository or raw,
        docs_url=None,
    )


# ---------------------------------------------------------------------------
# Tags (live)
# ---------------------------------------------------------------------------
def list_image_tags(
    provider: str,
    repository: str,
    refresh: bool = False,
) -> List[ComputerImageTag]:
    """Return selectable tags for a repository (cached, with fallback)."""
    provider = (provider or "").strip().lower()
    repository = (repository or "").strip()
    fallback_tag = DEFAULT_KASM_TAG if provider == "kasmweb" else DEFAULT_LINUXSERVER_TAG
    static = find_catalog_image(repository)
    if static:
        fallback_tag = static.default_tag

    try:
        if provider in ("kasmweb", "kasm"):
            repo = repository if repository.startswith("kasmweb/") else f"kasmweb/{repository}"
            data = _cached_json(
                f"kasmweb:tags:{repo}",
                lambda: _http_json(
                    f"https://hub.docker.com/v2/repositories/{repo}/tags"
                    "?page_size=100&ordering=last_updated"
                ),
                0 if refresh else TAGS_TTL_SECONDS,
            )
            tags = []
            for item in (data or {}).get("results", []):
                name = (item.get("name") or "").strip()
                if not name or name.startswith(("aarch64-", "x86_64-", "arm64v8-")):
                    continue
                tags.append(ComputerImageTag(name=name, updated_at=item.get("last_updated")))
            return _sort_tags(tags) or [ComputerImageTag(name=fallback_tag)]

        if provider in ("linuxserver", "lscr"):
            data = _cached_json(
                "linuxserver:webtop:tags",
                lambda: _http_json(
                    "https://api.linuxserver.io/api/v1/images"
                    "?include_config=false&include_deprecated=false"
                ),
                0 if refresh else TAGS_TTL_SECONDS,
            )
            tags = []
            for item in (data or {}).get("data", {}).get("repositories", {}).get("linuxserver", []):
                if item.get("name") != "webtop":
                    continue
                for tag in item.get("tags") or []:
                    name = (tag.get("tag") or "").strip()
                    # alpine-kde/arch-kde are Wayland-only and do not expose
                    # the X11 display the agent needs.
                    if name and name not in ("dev", "alpine-kde", "arch-kde"):
                        tags.append(ComputerImageTag(name=name, updated_at=item.get("version_timestamp")))
            return _sort_tags(tags) or [ComputerImageTag(name=fallback_tag)]
    except Exception as ex:
        logger.debug("Could not fetch tags for %s/%s: %s", provider, repository, ex)
    return [ComputerImageTag(name=fallback_tag)]


def _sort_tags(tags: Iterable[ComputerImageTag]) -> List[ComputerImageTag]:
    """Stable semantic-ish ordering: stable versions first, then flavors."""
    items = list(tags)
    seen = set()
    unique = []
    for item in items:
        if item.name in seen:
            continue
        seen.add(item.name)
        unique.append(item)
    def rank(item: ComputerImageTag):
        version = re.match(r"^(\d+)\.(\d+)\.(\d+)$", item.name)
        if version:
            return (0, tuple(-int(part) for part in version.groups()))
        if re.match(r"^\d+\.\d+\.\d+-rolling-(daily|weekly)$", item.name):
            return (1, item.name)
        return (2, item.name)
    return sorted(unique, key=rank)[:80]


# ---------------------------------------------------------------------------
# HTTP cache
# ---------------------------------------------------------------------------
_CACHE: Dict[str, Tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()


def _cached_json(key: str, loader, ttl: int) -> Any:
    """Return a cached JSON response, refreshing after *ttl*."""
    now = time.time()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] < ttl:
            return cached[1]
    data = loader()
    with _CACHE_LOCK:
        _CACHE[key] = (now, data)
    return data


def _http_json(url: str) -> Any:
    """Fetch a URL as JSON with a short timeout."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "codx-junior-computer-image-library",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        import json
        return json.loads(response.read().decode("utf-8"))
