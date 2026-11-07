"""Reusable browser scripts, stored per project and per site.

Why
---
Exploring a site with the browser tools is slow: every visit re-discovers the
same selectors and click paths.  A *browser script* is a small, named,
versioned recipe that a model writes once ("login on github.com") and replays on
any later visit.

Design decisions
----------------
* Scripts are DATA, never ``eval``/``exec``: ``language="steps"`` stores a JSON
  array of browser actions (the same vocabulary as the ``browse_action`` tool).
  The browser layer executes them; the codx-junior process never runs model
  written Python.
* ``language="javascript"`` is allowed for small in-page helpers and is meant to
  be evaluated **inside the page** (Playwright ``page.evaluate``), never in the
  API process.
* Identity: ``id`` (uuid) is canonical, ``title``/``site`` are labels only, so
  renaming a script never moves a folder.
* Storage (next to the browser sessions, under ``.codx``)::

      <project>/.codx/browser_scripts/index.json      # cheap catalogue
      <project>/.codx/browser_scripts/.trash/         # soft deleted scripts
      <project>/.codx/browser_scripts/<id>/script.json
      <project>/.codx/browser_scripts/<id>/script.<ext>
      <project>/.codx/browser_scripts/<id>/versions/v<N>.<ext>

* Deletes are soft (moved to ``.trash``) so a bad model call is recoverable.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import threading
import uuid
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

SCRIPTS_DIRNAME = os.path.join(".codx", "browser_scripts")
INDEX_FILE = "index.json"
INDEX_VERSION = 1
TRASH_DIRNAME = ".trash"
MAX_VERSIONS = 10

DEFAULT_SITE = "generic"

STEPS = "steps"
JAVASCRIPT = "javascript"
PYTHON = "python"
SCRIPT_LANGUAGES = (STEPS, JAVASCRIPT, PYTHON)
CODE_EXTENSIONS = {STEPS: "json", JAVASCRIPT: "js", PYTHON: "py"}

# Vocabulary of the ``browse_action`` tool: used to warn (never to reject), so a
# script can carry a step the browser layer learned to handle later on.
KNOWN_STEP_ACTIONS = (
    "goto",
    "click",
    "type",
    "fill",
    "press",
    "hover",
    "select",
    "wait",
    "wait_for",
    "scroll",
    "screenshot",
    "evaluate",
    "reload",
    "go_back",
    "extract",
    "assert",
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_site(value: Optional[str]) -> str:
    """Return the site key of a URL or domain (``https://www.GitHub.com/x`` -> ``github.com``)."""
    if not value:
        return DEFAULT_SITE
    value = str(value).strip().lower()
    if not value:
        return DEFAULT_SITE
    try:
        parsed = urlparse(value if "//" in value else f"//{value}")
        host = (parsed.hostname or "").strip()
    except Exception:
        host = ""
    if not host:
        host = re.split(r"[/?#]", value)[0].strip()
    if host.startswith("www."):
        host = host[len("www."):]
    if "@" in host:
        host = host.split("@")[-1]
    return host or DEFAULT_SITE


def _site_matches(entry_site: Optional[str], site: Optional[str]) -> bool:
    left, right = normalize_site(entry_site), normalize_site(site)
    if not left or not right:
        return False
    return left == right or left.endswith(f".{right}") or right.endswith(f".{left}")


def _safe_id(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))


def _normalize_tags(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = re.split(r"[,\s]+", value)
    tags: List[str] = []
    for item in value:
        tag = re.sub(r"\s+", "-", str(item).strip().lower()).strip("-")
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handler:
            return json.load(handler)
    except FileNotFoundError:
        return None
    except Exception:
        logger.warning("Invalid JSON file %s", path, exc_info=True)
        return None


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handler:
        return handler.read()


def _atomic_write(path: str, content: str) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    descriptor, tmp_path = tempfile.mkstemp(dir=folder, prefix=".tmp-", suffix=os.path.basename(path))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handler:
            handler.write(content)
            handler.flush()
            os.fsync(handler.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def coerce_code(code: Any, language: str = STEPS) -> str:
    """Validate/normalize a script body and return it as text.

    ``steps`` bodies accept a list of dicts or a JSON string and are stored as
    pretty printed JSON. Other languages are stored verbatim.
    """
    language = (language or STEPS).strip().lower()
    if language not in SCRIPT_LANGUAGES:
        raise ValueError(f"language must be one of {', '.join(SCRIPT_LANGUAGES)}")

    if isinstance(code, dict) and "steps" in code:
        code = code["steps"]
    if isinstance(code, (list, tuple)):
        data: Any = list(code)
        text = ""
    else:
        text = str(code or "").strip()
        if not text:
            raise ValueError("code is required")
        if language != STEPS:
            return text
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"steps script must be valid JSON: {error}") from error
        if isinstance(data, dict) and "steps" in data:
            data = data["steps"]

    if language != STEPS:
        return text or json.dumps(data, indent=2, ensure_ascii=False)

    if not isinstance(data, list) or not data:
        raise ValueError("steps script must be a non-empty JSON array of actions")

    steps: List[Dict[str, Any]] = []
    for index, step in enumerate(data):
        if not isinstance(step, dict):
            raise ValueError(f"step #{index + 1} must be an object, got {type(step).__name__}")
        step = dict(step)
        action = step.pop("type", None) or step.get("action")
        if not action:
            raise ValueError(f"step #{index + 1} is missing 'action'")
        step["action"] = str(action).strip().lower()
        if step["action"] not in KNOWN_STEP_ACTIONS:
            logger.info("Unknown browser step action '%s' (stored anyway)", step["action"])
        steps.append(step)
    return json.dumps(steps, indent=2, ensure_ascii=False)


def parse_steps(code: str) -> List[Dict[str, Any]]:
    """Return the action list of a ``steps`` script body (empty when invalid)."""
    try:
        data = json.loads(code or "[]")
    except json.JSONDecodeError:
        return []
    return [step for step in data if isinstance(step, dict)] if isinstance(data, list) else []


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
@dataclass
class BrowserScript:
    id: str
    title: str
    site: str = DEFAULT_SITE
    description: str = ""
    language: str = STEPS
    code: str = ""
    tags: List[str] = field(default_factory=list)
    version: int = 1
    uses: int = 0
    created_at: str = ""
    updated_at: str = ""
    last_used_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.site = normalize_site(self.site)
        self.language = (self.language or STEPS).strip().lower()
        self.tags = _normalize_tags(self.tags)
        if not self.created_at:
            self.created_at = _now()
        if not self.updated_at:
            self.updated_at = self.created_at

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return parse_steps(self.code) if self.language == STEPS else []

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "site": self.site,
            "description": self.description,
            "language": self.language,
            "tags": list(self.tags),
            "version": self.version,
            "uses": self.uses,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_used_at": self.last_used_at,
        }

    def to_dict(self, include_code: bool = False) -> Dict[str, Any]:
        data = self.summary()
        data["steps"] = len(self.steps)
        if include_code:
            data["code"] = self.code
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrowserScript":
        known = {item.name for item in fields(cls)}
        payload = {key: value for key, value in (data or {}).items() if key in known}
        payload.setdefault("id", str(uuid.uuid4()))
        payload.setdefault("title", "Untitled script")
        return cls(**payload)


# --------------------------------------------------------------------------- #
# store
# --------------------------------------------------------------------------- #
class BrowserScriptStore:
    """Read/write the per project library of reusable browser scripts."""

    def __init__(self, project_path: str, root: Optional[str] = None) -> None:
        self.project_path = os.path.abspath(project_path or ".")
        self.root = os.path.abspath(root or os.path.join(self.project_path, SCRIPTS_DIRNAME))
        self._lock = threading.RLock()

    # -- paths ------------------------------------------------------------- #
    @property
    def index_path(self) -> str:
        return os.path.join(self.root, INDEX_FILE)

    @property
    def trash_path(self) -> str:
        return os.path.join(self.root, TRASH_DIRNAME)

    def script_dir(self, script_id: str) -> str:
        return os.path.join(self.root, _safe_id(script_id))

    def script_json_path(self, script_id: str) -> str:
        # Metadata must not collide with the code file: a ``steps`` script is
        # also JSON (``script.json``), and writing both to the same path made
        # the loader read metadata as the script body.
        return os.path.join(self.script_dir(script_id), "meta.json")

    def _legacy_json_path(self, script_id: str) -> str:
        return os.path.join(self.script_dir(script_id), "script.json")

    def code_path(self, script_id: str, language: str) -> str:
        extension = CODE_EXTENSIONS.get((language or STEPS).lower(), "txt")
        return os.path.join(self.script_dir(script_id), f"script.{extension}")

    def versions_dir(self, script_id: str) -> str:
        return os.path.join(self.script_dir(script_id), "versions")

    # -- index ------------------------------------------------------------- #
    def _read_index(self) -> Dict[str, Any]:
        data = _read_json(self.index_path) if os.path.isfile(self.index_path) else None
        if isinstance(data, dict) and isinstance(data.get("scripts"), dict):
            return data
        return self._rebuild_index()

    def _write_index(self, data: Dict[str, Any]) -> None:
        data["version"] = INDEX_VERSION
        data["updated_at"] = _now()
        data.setdefault("scripts", {})
        _atomic_write(self.index_path, json.dumps(data, indent=2, ensure_ascii=False))

    def _rebuild_index(self) -> Dict[str, Any]:
        """Rebuild the catalogue from the script folders (self healing)."""
        scripts: Dict[str, Any] = {}
        if os.path.isdir(self.root):
            for name in sorted(os.listdir(self.root)):
                if name.startswith("."):
                    continue
                folder = os.path.join(self.root, name)
                if not os.path.isdir(folder):
                    continue
                script = self._read_script_folder(name)
                if not script:
                    continue
                entry = script.summary()
                entry["folder"] = name
                scripts[script.id] = entry
        return {"version": INDEX_VERSION, "updated_at": _now(), "scripts": scripts}

    def _upsert_index(self, script: BrowserScript) -> None:
        data = self._read_index()
        entry = script.summary()
        entry["folder"] = os.path.basename(self.script_dir(script.id))
        data["scripts"][script.id] = entry
        self._write_index(data)

    def _remove_from_index(self, script_id: str) -> None:
        data = self._read_index()
        if data["scripts"].pop(script_id, None) is not None:
            self._write_index(data)

    # -- persistence ------------------------------------------------------- #
    def _read_script_folder(self, script_id: str) -> Optional[BrowserScript]:
        path = self.script_json_path(script_id)
        if not os.path.isfile(path):
            # Old layout: metadata and code both lived in ``script.json``.
            legacy = self._legacy_json_path(script_id)
            data = _read_json(legacy) if os.path.isfile(legacy) else None
            if isinstance(data, dict) and data.get("title") and data.get("id"):
                path = legacy
            else:
                return None
        data = _read_json(path)
        if not isinstance(data, dict):
            return None
        data.setdefault("id", _safe_id(script_id))
        language = (data.get("language") or STEPS).lower()
        code_path = self.code_path(script_id, language)
        if os.path.isfile(code_path):
            data["code"] = _read_text(code_path)
        return BrowserScript.from_dict(data)

    def _write_script(self, script: BrowserScript) -> None:
        folder = self.script_dir(script.id)
        os.makedirs(folder, exist_ok=True)
        extension = CODE_EXTENSIONS.get(script.language, "txt")
        for other in set(CODE_EXTENSIONS.values()) | {"txt"}:
            if other == extension:
                continue
            stale = os.path.join(folder, f"script.{other}")
            if os.path.isfile(stale):
                try:
                    os.remove(stale)
                except OSError:
                    logger.warning("Could not remove stale code file %s", stale)
        _atomic_write(self.code_path(script.id, script.language), script.code)
        _atomic_write(self.script_json_path(script.id), json.dumps(script.to_dict(), indent=2, ensure_ascii=False))

    def _archive_version(self, script: BrowserScript) -> None:
        """Keep the current body as ``versions/v<version>.<ext>`` (bounded)."""
        if not script.code:
            return
        extension = CODE_EXTENSIONS.get(script.language, "txt")
        folder = self.versions_dir(script.id)
        os.makedirs(folder, exist_ok=True)
        _atomic_write(os.path.join(folder, f"v{script.version}.{extension}"), script.code)
        archived = sorted(
            (name for name in os.listdir(folder) if re.match(r"^v\d+\.", name)),
            key=lambda name: int(name[1:].split(".")[0]),
        )
        for name in archived[:-MAX_VERSIONS]:
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                logger.warning("Could not prune archived version %s", name)

    # -- queries ----------------------------------------------------------- #
    def get_script(self, script_id: str) -> Optional[BrowserScript]:
        script_id = _safe_id(script_id)
        if not script_id:
            return None
        return self._read_script_folder(script_id)

    def find_script(self, title: Optional[str] = None, site: Optional[str] = None) -> Optional[BrowserScript]:
        """Find by title (case insensitive) optionally constrained to a site."""
        wanted = (title or "").strip().lower()
        if not wanted:
            return None
        for entry in self._read_index()["scripts"].values():
            if (entry.get("title") or "").strip().lower() != wanted:
                continue
            if site and not _site_matches(entry.get("site"), site):
                continue
            script = self.get_script(entry["id"])
            if script:
                return script
        return None

    def search_scripts(
        self,
        query: Optional[str] = None,
        site: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = 20,
    ) -> List[Dict[str, Any]]:
        """Catalogue search, best match first (score, uses, last update)."""
        wanted_tags = set(_normalize_tags(tags))
        tokens = [token for token in re.split(r"[^a-z0-9]+", (query or "").lower()) if len(token) > 1]
        scored = []
        for entry in self._read_index()["scripts"].values():
            if site and not _site_matches(entry.get("site"), site):
                continue
            if wanted_tags and not wanted_tags.issubset({tag.lower() for tag in entry.get("tags") or []}):
                continue
            score = _score_entry(tokens, entry)
            if tokens and score <= 0:
                continue
            scored.append((score, entry))
        scored.sort(
            key=lambda item: (item[0], int(item[1].get("uses") or 0), item[1].get("updated_at") or ""),
            reverse=True,
        )
        entries = [entry for _, entry in scored]
        return entries[:limit] if limit else entries

    def list_scripts(
        self,
        site: Optional[str] = None,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return self.search_scripts(query=query, site=site, tags=tags, limit=limit)

    def list_versions(self, script_id: str) -> List[str]:
        folder = self.versions_dir(script_id)
        if not os.path.isdir(folder):
            return []
        return sorted(
            [name for name in os.listdir(folder) if re.match(r"^v\d+\.", name)],
            key=lambda name: int(name[1:].split(".")[0]),
        )

    def stats(self) -> Dict[str, Any]:
        entries = list(self._read_index()["scripts"].values())
        sites: Dict[str, int] = {}
        for entry in entries:
            key = entry.get("site") or DEFAULT_SITE
            sites[key] = sites.get(key, 0) + 1
        return {
            "root": self.root,
            "scripts": len(entries),
            "sites": dict(sorted(sites.items(), key=lambda item: item[1], reverse=True)),
            "uses": sum(int(entry.get("uses") or 0) for entry in entries),
        }

    # -- mutations --------------------------------------------------------- #
    def save_script(
        self,
        title: str,
        code: Any,
        site: Optional[str] = None,
        description: str = "",
        language: str = STEPS,
        tags: Optional[List[str]] = None,
        script_id: Optional[str] = None,
    ) -> BrowserScript:
        """Create or update a script.

        Updating happens when ``script_id`` is given *or* a script with the same
        title and site already exists: the previous body is archived and the
        version bumped, so a model never duplicates its own recipes.
        """
        title = (title or "").strip()
        if not title:
            raise ValueError("title is required")
        language = (language or STEPS).strip().lower()
        body = coerce_code(code, language)
        site_key = normalize_site(site)
        normalized_tags = _normalize_tags(tags)

        with self._lock:
            existing = self.get_script(script_id) if script_id else None
            if not existing:
                existing = self.find_script(title=title, site=site_key)
            now = _now()
            if existing:
                self._archive_version(existing)
                existing.title = title
                existing.site = site_key
                existing.language = language
                existing.description = description or existing.description
                existing.tags = normalized_tags or existing.tags
                existing.code = body
                existing.version = int(existing.version or 1) + 1
                existing.updated_at = now
                script = existing
            else:
                script = BrowserScript(
                    id=str(uuid.uuid4()),
                    title=title,
                    site=site_key,
                    description=description or "",
                    language=language,
                    code=body,
                    tags=normalized_tags,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            self._write_script(script)
            self._upsert_index(script)
            return script

    def mark_used(self, script_id: str) -> Optional[BrowserScript]:
        with self._lock:
            script = self.get_script(script_id)
            if not script:
                return None
            script.uses = int(script.uses or 0) + 1
            script.last_used_at = _now()
            self._write_script(script)
            self._upsert_index(script)
            return script

    def delete_script(self, script_id: str, hard: bool = False) -> bool:
        with self._lock:
            script = self.get_script(script_id)
            script_id = _safe_id(script_id)
            folder = self.script_dir(script_id)
            if not os.path.isdir(folder):
                self._remove_from_index(script_id)
                return False
            if hard:
                shutil.rmtree(folder, ignore_errors=True)
            else:
                os.makedirs(self.trash_path, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                target = os.path.join(self.trash_path, f"{script_id}-{stamp}")
                shutil.move(folder, target)
            self._remove_from_index(script_id)
            logger.info("Deleted browser script %s (%s)", script_id, script.title if script else "unknown")
            return True

    # -- rendering --------------------------------------------------------- #
    def to_markdown(self, entries: List[Dict[str, Any]]) -> str:
        if not entries:
            return "(no saved browser scripts)"
        lines = ["| id | title | site | lang | ver | uses |", "| --- | --- | --- | --- | --- | --- |"]
        for entry in entries:
            description = (entry.get("description") or "").replace("|", "/").strip()
            title = (entry.get("title") or "").replace("|", "/")
            if description:
                title = f"{title} — {description}"
            lines.append(
                f"| `{entry.get('id')}` | {title} | {entry.get('site')} | {entry.get('language')} "
                f"| {entry.get('version')} | {entry.get('uses')} |"
            )
        return "\n".join(lines)

    def render_script(self, script: BrowserScript, include_code: bool = True) -> str:
        lines = [
            f"# {script.title}",
            f"- id: `{script.id}`",
            f"- site: `{script.site}`",
            f"- language: `{script.language}`",
            f"- version: {script.version} · uses: {script.uses}",
        ]
        if script.description:
            lines.append(f"- description: {script.description}")
        if script.tags:
            lines.append(f"- tags: {', '.join(script.tags)}")
        if not include_code:
            return "\n".join(lines)
        lines.append("")
        if script.language == STEPS:
            lines.append("## Steps — replay them in order with the `browse_action` tool")
            lines.append("```json")
            lines.append(script.code.rstrip())
            lines.append("```")
            lines.append("")
            lines.append(
                "If a selector no longer works, fix it and call `save_browser_script` "
                f"with `script_id=\"{script.id}\"` so the next visit is faster."
            )
        elif script.language == JAVASCRIPT:
            lines.append("## In-page JavaScript — evaluate inside the page, never in the codx process")
            lines.append("```javascript")
            lines.append(script.code.rstrip())
            lines.append("```")
        else:
            lines.append(f"## {script.language} script")
            lines.append("```")
            lines.append(script.code.rstrip())
            lines.append("```")
        return "\n".join(lines)


def _score_entry(tokens: List[str], entry: Dict[str, Any]) -> int:
    if not tokens:
        return 0
    title = (entry.get("title") or "").lower()
    site = (entry.get("site") or "").lower()
    description = (entry.get("description") or "").lower()
    tags = " ".join(entry.get("tags") or []).lower()
    score = 0
    for token in tokens:
        if token in title:
            score += 3
        if token in site:
            score += 2
        if token in tags:
            score += 2
        if token in description:
            score += 1
    return score