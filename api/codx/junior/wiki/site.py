"""
Build the machine-readable manifest that powers the modern documentation site.

The wiki used to be a folder of markdown files consumed by a bare-bones viewer.
This module turns that folder into a *site*:

* a navigation tree grouped in meaningful sections,
* rich page metadata (description, tags, reading time, headings, source links),
* a landing page (hero, feature cards, quick links, stats),
* child-project navigation so a parent wiki can link to every project below it,
* the AI assistant suggestions and context catalog.

The manifest is written to ``<wiki>/docs.json`` and is consumed by the Vue
docs UI. It is deliberately cheap to build (no AI calls) so it can be
regenerated on every wiki update and on every page request.

Everything here is defensive: a malformed markdown file must never break the
site. Missing metadata is inferred from the first heading/paragraph and the
file system.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import tomllib
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

from slugify import slugify

logger = logging.getLogger(__name__)

DOCS_FILE_NAME = "docs.json"
SITE_VERSION = 2

# Folder names that never contain wiki pages.
_WIKI_IGNORED_DIRS = {
    ".git",
    ".vitepress",
    ".codx",
    "node_modules",
    "dist",
    "site-packages",
    "__pycache__",
}

# Non-markdown files that live next to the pages.
_WIKI_IGNORED_FILES = {
    "index.md",  # VitePress landing page (generated from the manifest)
    "README.md",
    "package.json",
    "package-lock.json",
    "docs.json",
    "llms.txt",
    "wiki_index.json",
    "wiki_tree.json",
    "mkdocs.yml",
    "wiki-manager.sh",
}

_CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".go", ".rs",
    ".java", ".kt", ".kts", ".scala", ".c", ".h", ".cc", ".cpp", ".hpp",
    ".cs", ".fs", ".rb", ".php", ".swift", ".dart", ".ex", ".exs", ".clj",
    ".sh", ".bash", ".ps1", ".sql", ".lua", ".r", ".m", ".mm", ".zig",
    ".nim", ".proto", ".graphql",
}

_DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".adoc", ".txt"}

_LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "React",
    ".ts": "TypeScript",
    ".tsx": "React",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".dart": "Dart",
    ".sh": "Shell",
    ".sql": "SQL",
    ".md": "Markdown",
}

_ROOT_MARKERS = {
    "package.json": "Node",
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "setup.py": "Python",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java",
    "build.gradle": "Java",
    "composer.json": "PHP",
    "Gemfile": "Ruby",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker",
    "docker-compose.yaml": "Docker",
}

_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_MERMAID_RE = re.compile(r"```mermaid\b", re.IGNORECASE)

_ICON_RULES: List[Tuple[Tuple[str, ...], str]] = [
    (("start", "setup", "install", "quickstart", "getting"), "fa-solid fa-rocket"),
    (("architect", "domain", "design", "overview"), "fa-solid fa-diagram-project"),
    (("api", "reference", "module", "class", "function"), "fa-solid fa-code"),
    (("guide", "tutorial", "how", "usage", "example"), "fa-solid fa-compass"),
    (("test", "quality", "ci", "build"), "fa-solid fa-vial-circle-check"),
    (("deploy", "operation", "infra", "docker", "kubernetes"), "fa-solid fa-cloud-arrow-up"),
    (("security", "auth", "permission", "secret"), "fa-solid fa-shield-halved"),
    (("data", "database", "storage", "model"), "fa-solid fa-database"),
    (("config", "setting", "environment"), "fa-solid fa-sliders"),
    (("support", "faq", "troubleshoot"), "fa-solid fa-life-ring"),
]

_SECTION_ORDER = {
    "get started": 10,
    "overview": 11,
    "guides": 20,
    "architecture": 30,
    "api reference": 40,
    "reference": 41,
    "operations": 50,
    "community": 60,
}


def _as_list(value: Any) -> List[str]:
    """Normalise a frontmatter value into a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value).strip()]


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """
    Split a markdown document into (frontmatter, body).

    Supports the YAML subset used by generated pages. Invalid YAML is ignored
    instead of raising: the page content is always more important than its
    metadata.
    """
    match = _FRONTMATTER_RE.match(text or "")
    if not match:
        return {}, text or ""
    raw = match.group(1)
    body = text[match.end():]
    data: Dict[str, Any] = {}
    try:
        import yaml  # PyYAML is already a runtime dependency

        loaded = yaml.safe_load(raw)
        if isinstance(loaded, dict):
            data = {str(key): value for key, value in loaded.items()}
    except Exception as ex:  # pragma: no cover - malformed metadata only
        logger.debug("Ignoring invalid wiki frontmatter: %s", ex)
    return data, body


def strip_frontmatter(text: str) -> str:
    """Return the markdown body without its YAML frontmatter."""
    return parse_frontmatter(text)[1]


def first_heading(text: str) -> str:
    """Return the first markdown heading, or an empty string."""
    for line in (text or "").splitlines():
        match = _HEADING_RE.match(line.strip())
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
    return ""


def first_paragraph(text: str) -> str:
    """
    Return a short description extracted from the first real paragraph.

    Headings, frontmatter fences, code blocks, tables and lists are skipped.
    """
    in_code = False
    for raw_line in strip_frontmatter(text or "").splitlines():
        line = raw_line.strip()
        if line.startswith("```") or line.startswith("~~~"):
            in_code = not in_code
            continue
        if in_code or not line:
            continue
        if line.startswith(">"):
            quoted = re.sub(r"^>\s*", "", line)
            if "tl;dr" in quoted.lower():
                clean = re.sub(r"[*_`~]+", "", quoted).strip()
                if clean:
                    return clean[:240]
            continue
        if line.startswith("<"):
            # Raw HTML (badges, screenshots) is never a description.
            line = re.sub(r"<[^>]+>", "", line).strip()
            if not line:
                continue
        if line.startswith(("#", "|", "-", "*", ":::", "<!--", "//", "/*", "*/", "--")):
            continue
        if re.match(r"^\d+[.)]\s+", line):
            continue
        clean = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
        clean = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", clean)
        clean = re.sub(r"[*_`~]+", "", clean).strip()
        if len(clean) >= 24:
            return clean[:240]
    return ""


def humanize(value: str) -> str:
    """Turn ``some-page_name`` into ``Some Page Name``."""
    text = re.sub(r"[-_/]+", " ", os.path.splitext(str(value or ""))[0])
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Page"
    return text[:1].upper() + text[1:]


_PROFILE_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render_profile_placeholders(text: str, settings: Any) -> str:
    """
    Render the small template used by project profiles.

    Profiles are composed/rendered by ``ProfileManager`` for chats, but the
    wiki reads them from the management API. This helper makes the wiki safe
    even when a profile is read without rendering (or when an older generated
    document still contains ``{{ project_path }}`` / ``{{ projectpath }}``).
    """
    values = {
        "project_name": getattr(settings, "project_name", "") or "",
        "project_path": getattr(settings, "abs_project_path", "") or "",
        "projectpath": getattr(settings, "abs_project_path", "") or "",
    }
    return _PROFILE_PLACEHOLDER_RE.sub(
        lambda match: str(values.get(match.group(1), "")),
        text or "",
    )


def profile_text(profile: Any, settings: Any) -> str:
    """Return rendered profile content (parsed content preferred)."""
    content = getattr(profile, "parsed_content", None) or getattr(profile, "content", "") or ""
    return render_profile_placeholders(str(content), settings)


def icon_for(text: str) -> str:
    """Pick a Font Awesome icon from a page/section title."""
    lowered = (text or "").lower()
    for needles, icon in _ICON_RULES:
        if any(needle in lowered for needle in needles):
            return icon
    return "fa-regular fa-file-lines"


def reading_time(text: str) -> int:
    """Approximate reading time in minutes (200 words per minute)."""
    words = len(re.findall(r"\b[\w'-]+\b", strip_frontmatter(text or "")))
    return max(1, round(words / 200))


def _heading_slug(text: str) -> str:
    """Slug used to anchor a markdown heading in the docs renderer."""
    clean = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text or "")
    clean = re.sub(r"[`*_~]", "", clean)
    slug = slugify(clean)
    return slug or "section"


def extract_headings(text: str) -> List[Dict[str, Any]]:
    """Return the h2/h3 outline used by the on-this-page rail."""
    headings: List[Dict[str, Any]] = []
    in_code = False
    for raw_line in strip_frontmatter(text or "").splitlines():
        line = raw_line.strip()
        if line.startswith("```") or line.startswith("~~~"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = _HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        if level not in (2, 3):
            continue
        title = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", match.group(2).strip())
        title = re.sub(r"`", "", title).strip()
        headings.append({
            "level": level,
            "text": title,
            "id": _heading_slug(title),
        })
    return headings


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError as ex:
        logger.debug("Cannot read wiki file %s: %s", path, ex)
        return ""


def _atomic_write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.replace(tmp, path)


class WikiSiteBuilder:
    """Create and read the docs-site manifest for a project wiki."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.wiki_path = settings.get_project_wiki_path()
        self.docs_path = os.path.join(self.wiki_path, DOCS_FILE_NAME)
        self._kind_cache: Optional[Tuple[str, List[str]]] = None

    # ── public API ──────────────────────────────────────────────────────────

    def load(self) -> Dict[str, Any]:
        """Read the persisted manifest, returning an empty-ish site if absent."""
        if not os.path.isfile(self.docs_path):
            return {}
        try:
            with open(self.docs_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError) as ex:
            logger.warning("Cannot read wiki site manifest %s: %s", self.docs_path, ex)
            return {}

    def latest_page_mtime(self) -> float:
        """Return the newest markdown page mtime in the wiki folder."""
        latest = 0.0
        if not os.path.isdir(self.wiki_path):
            return latest
        for root, dirs, files in os.walk(self.wiki_path):
            dirs[:] = [d for d in dirs if d not in _WIKI_IGNORED_DIRS and not d.startswith(".")]
            for filename in files:
                if not filename.lower().endswith(".md") or filename in _WIKI_IGNORED_FILES:
                    continue
                try:
                    latest = max(latest, os.path.getmtime(os.path.join(root, filename)))
                except OSError:
                    continue
        return latest

    def is_stale(self, site: Optional[Dict[str, Any]] = None) -> bool:
        """
        Return True when pages changed after the manifest was generated.

        The scheduler rebuilds the manifest after each batch, but the UI and the
        assistant must also handle a manifest that is behind (for example when a
        background process was restarted). Rebuilding it is cheap and AI-free.
        """
        site = site if site is not None else self.load()
        if not site:
            return True
        latest = self.latest_page_mtime()
        try:
            docs_mtime = os.path.getmtime(self.docs_path)
        except OSError:
            return True
        # A page written after the manifest means the manifest is behind. The
        # small margin tolerates filesystem timestamp granularity.
        return latest > docs_mtime + 0.5

    def build_if_stale(self, write: bool = True) -> Dict[str, Any]:
        """Load the manifest and rebuild it only when a page is newer."""
        site = self.load()
        if self.is_stale(site):
            return self.build(write=write)
        return site

    def manifest_status(self) -> Dict[str, Any]:
        """Return a compact freshness report used by the update-status API."""
        site = self.load()
        latest = self.latest_page_mtime()
        generated = int((site or {}).get("generated_at") or 0)
        docs_mtime = 0.0
        try:
            docs_mtime = os.path.getmtime(self.docs_path)
        except OSError:
            pass
        return {
            "path": self.docs_path,
            "exists": bool(site),
            "generated_at": generated,
            "docs_mtime": int(docs_mtime),
            "latest_page_at": int(latest),
            "stale": (not site) or latest > docs_mtime + 0.5,
            "pages": len((site or {}).get("pages", {})),
        }

    def build(self, wiki_settings: Optional[Dict[str, Any]] = None, write: bool = True) -> Dict[str, Any]:
        """
        Build the complete docs-site manifest.

        Args:
            wiki_settings: Optional already-loaded wiki settings (categories,
                language, mode…). Loaded from disk when omitted.
            write: Persist ``docs.json`` and the derived static-site files.

        Returns:
            The JSON-serialisable site manifest.
        """
        wiki_settings = wiki_settings or self._load_wiki_settings()
        pages = self._collect_pages(wiki_settings)
        home = self._pick_home_page(pages)
        project = self._project_info(pages)
        child_projects, parent_project = self._related_projects()
        navigation = self._build_navigation(pages, home)
        features = self._build_features(navigation, pages)
        site = {
            "version": SITE_VERSION,
            "generated_at": int(time.time()),
            "project": project,
            "home": self._build_home(home, pages, project, features),
            "navigation": navigation,
            "pages": {page["path"]: page for page in pages},
            "child_projects": child_projects,
            "parent_project": parent_project,
            "assistant": self._assistant_config(project, pages),
            "stats": {
                "pages": len(pages),
                "sections": len(navigation),
                "domains": len([p for p in pages if p["kind"] == "domain"]),
                "modules": len([p for p in pages if p["kind"] == "module"]),
                "child_projects": len(child_projects),
                "reading_minutes": sum(page.get("reading_time", 1) for page in pages),
            },
            "search": {
                "provider": "local",
                "items": [
                    {
                        "path": page["path"],
                        "title": page["title"],
                        "description": page.get("description", ""),
                        "section": page.get("section", ""),
                        "tags": page.get("tags", []),
                    }
                    for page in pages
                ],
            },
        }
        if write:
            try:
                _atomic_write(self.docs_path, json.dumps(site, indent=2))
                self._write_llms_txt(site)
                self._write_vitepress_config(site)
            except OSError as ex:
                logger.exception("Cannot persist wiki site manifest: %s", ex)
        return site

    def page(self, page_path: str) -> Optional[Dict[str, Any]]:
        """
        Return one page (metadata + markdown body) from the wiki folder.

        The path is interpreted relative to the wiki root and is protected
        against traversal. Frontmatter is removed from the returned content.
        """
        if not page_path:
            return None
        relative = str(page_path).replace("\\", "/").lstrip("/")
        if not relative.endswith(".md"):
            relative = f"{relative}.md"
        root = os.path.realpath(self.wiki_path)
        target = os.path.realpath(os.path.join(root, relative))
        if not target.startswith(root + os.sep) or not os.path.isfile(target):
            return None
        raw = _read_text(target)
        frontmatter, body = parse_frontmatter(raw)
        title = str(frontmatter.get("title") or first_heading(body) or humanize(relative))
        return {
            "path": relative[:-3].replace(os.sep, "/"),
            "file": relative,
            "title": title,
            "description": str(frontmatter.get("description") or first_paragraph(body)),
            "tags": _as_list(frontmatter.get("tags") or frontmatter.get("keywords")),
            "content": body,
            "updated_at": int(os.path.getmtime(target)),
            "reading_time": reading_time(body),
            "headings": extract_headings(body),
        }

    # ── page discovery ──────────────────────────────────────────────────────

    def _collect_pages(self, wiki_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not os.path.isdir(self.wiki_path):
            return []
        categories = self._category_index(wiki_settings)
        pages: List[Dict[str, Any]] = []
        for root, dirs, files in os.walk(self.wiki_path):
            dirs[:] = sorted(d for d in dirs if d not in _WIKI_IGNORED_DIRS and not d.startswith("."))
            for filename in sorted(files):
                if not filename.lower().endswith(".md"):
                    continue
                if filename in _WIKI_IGNORED_FILES:
                    continue
                absolute = os.path.join(root, filename)
                relative = os.path.relpath(absolute, self.wiki_path).replace(os.sep, "/")
                if relative.startswith("."):
                    continue
                page = self._page_metadata(absolute, relative, categories, wiki_settings)
                if page:
                    pages.append(page)
        pages.sort(key=lambda p: (
            p.get("section_order", 999),
            p.get("order", 9999),
            p.get("title", "").lower(),
        ))
        return pages

    def _page_metadata(
        self,
        absolute: str,
        relative: str,
        categories: Dict[str, Dict[str, Any]],
        wiki_settings: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        raw = _read_text(absolute)
        if not raw.strip():
            return None
        frontmatter, body = parse_frontmatter(raw)
        title = str(frontmatter.get("title") or first_heading(body) or humanize(relative))
        description = str(frontmatter.get("description") or first_paragraph(body))
        directory = os.path.dirname(relative).replace(os.sep, "/")
        section, section_order, order = self._section_for(
            relative=relative,
            directory=directory,
            categories=categories,
            frontmatter=frontmatter,
        )
        kind = str(frontmatter.get("kind") or self._page_kind(relative))
        tags = _as_list(frontmatter.get("tags") or frontmatter.get("keywords"))
        source = frontmatter.get("source") or frontmatter.get("file")
        stat = os.stat(absolute)
        page_path = relative[:-3]
        return {
            "path": page_path,
            "file": relative,
            "title": title,
            "description": description,
            "section": section,
            "section_order": section_order,
            "order": order,
            "kind": kind,
            "icon": str(frontmatter.get("icon") or icon_for(f"{section} {title}")),
            "tags": tags,
            "source": str(source) if source else "",
            "updated_at": int(stat.st_mtime),
            "reading_time": reading_time(body),
            "headings": extract_headings(body),
            "has_diagram": bool(_MERMAID_RE.search(body)),
            "words": len(re.findall(r"\b[\w'-]+\b", body)),
            "language": wiki_settings.get("language", "English"),
        }

    def _category_index(self, wiki_settings: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Map each category directory to its metadata.

        The longest matching directory wins, so a page inside
        ``guides/start/advanced`` is grouped under ``guides/start`` even when
        both are categories.
        """
        index: Dict[str, Dict[str, Any]] = {}
        for category in self._flatten_categories(wiki_settings.get("categories", [])):
            path = str(category.get("path") or "").strip("/")
            if path:
                index[path] = category
        return index

    def _section_for(
        self,
        relative: str,
        directory: str,
        categories: Dict[str, Dict[str, Any]],
        frontmatter: Dict[str, Any],
    ) -> Tuple[str, int, int]:
        explicit = str(frontmatter.get("section") or "").strip()
        if explicit:
            return explicit, _SECTION_ORDER.get(explicit.lower(), 25), self._order(frontmatter)

        if directory.startswith("domains"):
            return "Architecture", _SECTION_ORDER["architecture"], self._order(frontmatter)
        if directory.startswith("modules"):
            return "API Reference", _SECTION_ORDER["api reference"], self._order(frontmatter)

        # Longest category directory that is a prefix of the page directory.
        matches = [
            (path, category)
            for path, category in categories.items()
            if directory == path or directory.startswith(f"{path}/")
        ]
        if matches:
            path, category = max(matches, key=lambda item: len(item[0]))
            title = str(category.get("title") or humanize(path))
            return title, _SECTION_ORDER.get(title.lower(), 20), self._order(frontmatter, category)

        if directory:
            top = directory.split("/")[0]
            return humanize(top), _SECTION_ORDER.get(top.lower(), 25), self._order(frontmatter)
        if relative.lower() in ("home.md", "overview.md", "readme.md"):
            return "Get started", _SECTION_ORDER["get started"], 0
        return "Overview", _SECTION_ORDER["overview"], self._order(frontmatter)

    @staticmethod
    def _order(frontmatter: Dict[str, Any], category: Optional[Dict[str, Any]] = None) -> int:
        value = frontmatter.get("order")
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
        if category:
            try:
                return int(category.get("order", 9999))
            except (TypeError, ValueError):
                pass
        return 9999

    @staticmethod
    def _page_kind(relative: str) -> str:
        if relative in ("home.md", "overview.md", "index.md"):
            return "overview"
        if relative.startswith("domains/"):
            return "domain"
        if relative.startswith("modules/"):
            return "module"
        if relative.startswith("guides/"):
            return "guide"
        return "page"

    @staticmethod
    def _flatten_categories(categories: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        for category in categories or []:
            yield category
            yield from WikiSiteBuilder._flatten_categories(category.get("children", []))

    def _pick_home_page(self, pages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        preferred = ("home", "overview", "index", "welcome")
        by_path = {page["path"]: page for page in pages}
        for candidate in preferred:
            if candidate in by_path:
                return by_path[candidate]
        return pages[0] if pages else None

    # ── landing page ────────────────────────────────────────────────────────

    def _project_info(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        name = self.settings.project_name or "Project"
        description = self._project_description(name)
        kind, languages = self._detect_project_kind()
        return {
            "name": name,
            "title": name,
            "description": description,
            "tagline": self._tagline(description),
            "icon": self.settings.project_icon or "",
            "repository": self.settings.repo_url or "",
            "version": self._detect_version(),
            "kind": kind,
            "languages": languages,
            "project_id": self.settings.project_id,
            "codx_path": self.settings.codx_path,
            "wiki_enabled": bool(getattr(self.settings, "project_wiki", False)),
            "generated_at": int(time.time()),
        }

    def _project_description(self, fallback: str) -> str:
        """Return a useful project description without leaking template markers."""
        try:
            from codx.junior.profiles.profile_manager import ProfileManager

            profile = ProfileManager(settings=self.settings).read_profile("project")
            content = profile_text(profile, self.settings).strip()
            if content:
                description = first_paragraph(content)
                lowered = (description or "").lower()
                if description and not lowered.startswith(("project's path is", "project path is", "about ")):
                    return description
        except Exception as ex:  # pragma: no cover - profile is optional
            logger.debug("Cannot read project profile for wiki: %s", ex)

        # The profile may only contain boilerplate (or placeholders). Prefer a
        # real project summary from the README before falling back to a generic
        # sentence.
        root = getattr(self.settings, "abs_project_path", "") or ""
        for filename in ("README.md", "PROJECT_OVERVIEW.md", "readme.md"):
            path = os.path.join(root, filename)
            if not os.path.isfile(path):
                continue
            description = first_paragraph(_read_text(path))
            if description:
                return description[:240]
        return f"Documentation for {fallback}."

    @staticmethod
    def _tagline(description: str) -> str:
        sentence = re.split(r"(?<=[.!?])\s+", description or "")[0].strip()
        return sentence[:140] if sentence else "Project documentation"

    def project_kind(self) -> Tuple[str, List[str]]:
        """Public helper: ``(kind, languages)`` for the repository."""
        if self._kind_cache is None:
            self._kind_cache = self._detect_project_kind()
        return self._kind_cache

    def _detect_project_kind(self) -> Tuple[str, List[str]]:
        """Classify the repository as code/docs/generic and list its languages."""
        root = self.settings.abs_project_path or ""
        markers = []
        for filename, language in _ROOT_MARKERS.items():
            if os.path.isfile(os.path.join(root, filename)):
                markers.append(language)
        counts: Dict[str, int] = {}
        doc_count = 0
        scanned = 0
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in _WIKI_IGNORED_DIRS and not d.startswith(".")]
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in _CODE_EXTENSIONS:
                    counts[ext] = counts.get(ext, 0) + 1
                    scanned += 1
                elif ext in _DOC_EXTENSIONS:
                    doc_count += 1
                    scanned += 1
                if scanned >= 4000:
                    break
            if scanned >= 4000:
                break
        code_count = sum(counts.values())
        languages = sorted(
            {_LANGUAGE_BY_EXTENSION.get(ext, ext.lstrip(".").upper()) for ext in counts},
            key=lambda language: -sum(
                count for ext, count in counts.items()
                if _LANGUAGE_BY_EXTENSION.get(ext, ext.lstrip(".").upper()) == language
            ),
        )[:6]
        if code_count >= 5 or markers:
            return "code", languages
        if doc_count > code_count:
            return "docs", languages
        return "generic", languages

    def _detect_version(self) -> str:
        root = self.settings.abs_project_path or ""
        package = os.path.join(root, "package.json")
        if os.path.isfile(package):
            try:
                with open(package, "r", encoding="utf-8") as handle:
                    version = json.load(handle).get("version")
                if version:
                    return str(version)
            except (OSError, ValueError):
                pass
        pyproject = os.path.join(root, "pyproject.toml")
        if os.path.isfile(pyproject):
            try:
                with open(pyproject, "rb") as handle:
                    version = tomllib.load(handle).get("project", {}).get("version")
                if version:
                    return str(version)
            except (OSError, ValueError):
                pass
        for filename in ("VERSION", "version.txt"):
            path = os.path.join(root, filename)
            if os.path.isfile(path):
                version = _read_text(path).strip()
                if version:
                    return version
        return ""

    def _build_home(
        self,
        home: Optional[Dict[str, Any]],
        pages: List[Dict[str, Any]],
        project: Dict[str, Any],
        features: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        quick_links = []
        seen = set()
        for page in pages:
            if page["kind"] in ("domain", "module"):
                continue
            if page["path"] in seen:
                continue
            seen.add(page["path"])
            quick_links.append({
                "title": page["title"],
                "path": page["path"],
                "description": page.get("description", ""),
                "icon": page.get("icon", "fa-regular fa-file-lines"),
            })
            if len(quick_links) >= 6:
                break
        return {
            "page": home["path"] if home else "",
            "title": project["title"],
            "tagline": project["tagline"],
            "description": project["description"],
            "badge": self._hero_badge(project, pages),
            "features": features,
            "quick_links": quick_links,
            "diagram": next(
                (page["path"] for page in pages if page.get("has_diagram")),
                "",
            ),
        }

    @staticmethod
    def _hero_badge(project: Dict[str, Any], pages: List[Dict[str, Any]]) -> str:
        parts = []
        if project.get("version"):
            parts.append(f"v{project['version']}")
        if project.get("kind") == "code":
            parts.append("Code project")
        if len(pages) > 1:
            parts.append(f"{len(pages)} pages")
        return " · ".join(parts) or "Living documentation"

    def _build_features(
        self,
        navigation: List[Dict[str, Any]],
        pages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        features: List[Dict[str, Any]] = []
        for section in navigation:
            items = section.get("items", [])
            if not items:
                continue
            first = items[0]
            features.append({
                "title": section["title"],
                "details": first.get("description") or (
                    f"{len(items)} page{'s' if len(items) != 1 else ''} "
                    f"covering {section['title'].lower()}."
                ),
                "icon": section.get("icon") or icon_for(section["title"]),
                "path": first["path"],
            })
            if len(features) >= 6:
                break
        if len(features) < 3:
            for page in pages:
                if len(features) >= 3:
                    break
                if any(feature["path"] == page["path"] for feature in features):
                    continue
                features.append({
                    "title": page["title"],
                    "details": page.get("description") or "Read this page.",
                    "icon": page.get("icon", "fa-regular fa-file-lines"),
                    "path": page["path"],
                })
        return features

    def _build_navigation(
        self,
        pages: List[Dict[str, Any]],
        home: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        groups: Dict[str, Dict[str, Any]] = {}
        for page in pages:
            section = page.get("section") or "Overview"
            group = groups.setdefault(section, {
                "title": section,
                "icon": icon_for(section),
                "order": page.get("section_order", 999),
                "items": [],
            })
            group["items"].append({
                "title": page["title"],
                "path": page["path"],
                "description": page.get("description", ""),
                "icon": page.get("icon", "fa-regular fa-file-lines"),
                "tags": page.get("tags", []),
                "reading_time": page.get("reading_time", 1),
                "kind": page.get("kind", "page"),
            })
        if home:
            # The landing/overview page gets its own section. Remove it from the
            # category it was auto-assigned to so the sidebar never shows it twice.
            for group in groups.values():
                group["items"] = [
                    item for item in group["items"] if item.get("path") != home.get("path")
                ]
            overview = groups.setdefault("Overview", {
                "title": "Overview",
                "icon": icon_for("overview"),
                "order": _SECTION_ORDER["overview"],
                "items": [],
            })
            overview["items"].insert(0, {
                "title": "Introduction",
                "path": home["path"],
                "description": home.get("description", ""),
                "icon": "fa-solid fa-house",
                "tags": home.get("tags", []),
                "reading_time": home.get("reading_time", 1),
                "kind": "overview",
            })
        for group in groups.values():
            group["items"].sort(key=lambda item: item["title"].lower())
            group["count"] = len(group["items"])
        return sorted(
            (group for group in groups.values() if group["items"]),
            key=lambda group: (group["order"], group["title"].lower()),
        )

    # ── related projects ────────────────────────────────────────────────────

    def _related_projects(self) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        children: List[Dict[str, Any]] = []
        parent: Optional[Dict[str, Any]] = None
        try:
            from codx.junior.project.project_discover import (
                find_all_projects,
                get_project_dependencies,
                is_path_child_of,
            )

            for dependency in get_project_dependencies(self.settings):
                if not dependency or dependency.project_id == self.settings.project_id:
                    continue
                relation = (
                    "child"
                    if is_path_child_of(dependency.abs_project_path, self.settings.abs_project_path)
                    else "dependency"
                )
                entry = self._project_card(dependency)
                entry["relation"] = relation
                children.append(entry)

            if self.settings.abs_project_path:
                parents = [
                    project
                    for project in find_all_projects().values()
                    if project.project_id != self.settings.project_id
                    and is_path_child_of(self.settings.abs_project_path, project.abs_project_path)
                ]
                if parents:
                    closest = max(parents, key=lambda project: len(project.abs_project_path))
                    parent = self._project_card(closest)
                    parent["relation"] = "parent"
        except Exception as ex:  # pragma: no cover - discovery must never break docs
            logger.warning("Cannot resolve related wiki projects: %s", ex)
        children.sort(key=lambda entry: (entry.get("relation") != "child", entry.get("title", "").lower()))
        return children, parent

    def _project_card(self, project: Any) -> Dict[str, Any]:
        site = {}
        try:
            docs_path = os.path.join(project.get_project_wiki_path(), DOCS_FILE_NAME)
            if os.path.isfile(docs_path):
                with open(docs_path, "r", encoding="utf-8") as handle:
                    site = json.load(handle)
        except (OSError, ValueError):
            site = {}
        site_project = site.get("project", {}) if isinstance(site, dict) else {}
        pages = site.get("pages", {}) if isinstance(site, dict) else {}
        return {
            "name": project.project_name,
            "title": site_project.get("title") or project.project_name,
            "description": site_project.get("description") or (
                f"Documentation for {project.project_name}."
            ),
            "icon": site_project.get("icon") or project.project_icon or "",
            "project_id": project.project_id,
            "codx_path": project.codx_path,
            "path": project.abs_project_path,
            "wiki_path": project.get_project_wiki_path(),
            "page_count": len(pages) if isinstance(pages, dict) else 0,
            "status": "ready" if pages else ("pending" if project.project_wiki else "disabled"),
            "updated_at": site.get("generated_at") if isinstance(site, dict) else None,
            "wiki_url": f"?project={quote(project.project_name or '')}",
        }

    # ── assistant ───────────────────────────────────────────────────────────

    def _assistant_config(
        self,
        project: Dict[str, Any],
        pages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        name = project["name"]
        suggestions = [
            f"What is {name} and what problem does it solve?",
            "Give me a guided tour of the architecture.",
            "How do I get started in 5 minutes?",
            "Which modules should I read first?",
        ]
        for page in pages[:8]:
            if page["kind"] in ("overview", "domain", "guide"):
                suggestions.append(f"Explain \"{page['title']}\" with an example.")
        seen = set()
        unique = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique.append(suggestion)
        return {
            "enabled": bool(getattr(self.settings, "wiki_assistant_enabled", True)),
            "name": f"{name} guide",
            "greeting": (
                f"Hi! I'm the {name} documentation assistant. "
                "Ask me about the architecture, a module or how to get started."
            ),
            "suggestions": unique[:6],
            "scope": [page["path"] for page in pages[:80]],
        }

    # ── derived files ───────────────────────────────────────────────────────

    def _write_llms_txt(self, site: Dict[str, Any]) -> None:
        project = site.get("project", {})
        lines = [
            f"# {project.get('title') or project.get('name')}",
            "",
            f"> {project.get('description', '')}",
            "",
            "## Documentation",
            "",
        ]
        for page in site.get("pages", {}).values():
            lines.append(
                f"- [{page['title']}]({page['path']}): {page.get('description', '')}"
            )
        lines.append("")
        _atomic_write(os.path.join(self.wiki_path, "llms.txt"), "\n".join(lines))

    def _write_vitepress_config(self, site: Dict[str, Any]) -> None:
        """Keep the optional standalone VitePress build in sync with the site."""
        project = site.get("project", {})
        sidebar = [
            {
                "text": section["title"],
                "items": [
                    {"text": item["title"], "link": f"/{item['path']}"}
                    for item in section.get("items", [])
                ],
            }
            for section in site.get("navigation", [])
            if section.get("items")
        ]
        config = {
            "project": {
                "name": project.get("title") or project.get("name"),
                "description": project.get("description"),
                "icon": project.get("icon"),
                "repository": project.get("repository"),
            },
            "sidebar": sidebar,
            "last_update": site.get("generated_at"),
        }
        _atomic_write(
            os.path.join(self.wiki_path, ".vitepress", "config.json"),
            json.dumps(config, indent=2),
        )
        self._write_vitepress_landing(site)

    def _write_vitepress_landing(self, site: Dict[str, Any]) -> None:
        landing = os.path.join(self.wiki_path, "index.md")
        if os.path.isfile(landing):
            existing = _read_text(landing)
            if "layout: home" not in existing:
                # Respect a hand-written landing page.
                return
        project = site.get("project", {})
        home = site.get("home", {})
        features = home.get("features", [])
        hero_name = project.get("title") or project.get("name") or "Project"
        lines = [
            "---",
            "layout: home",
            "",
            "hero:",
            f"  name: {json.dumps(hero_name, ensure_ascii=False)}",
            f"  text: {json.dumps(project.get('tagline', ''), ensure_ascii=False)}",
            f"  tagline: {json.dumps(project.get('description', ''), ensure_ascii=False)}",
            "  actions:",
            "    - theme: brand",
            '      text: "Get started"',
            f"      link: {json.dumps('/' + (home.get('page') or ''), ensure_ascii=False)}",
            "    - theme: alt",
            '      text: "Ask the assistant"',
            '      link: "/assistant"',
            "",
            "features:",
        ]
        for feature in features:
            lines.extend([
                f"  - title: {json.dumps(feature['title'], ensure_ascii=False)}",
                f"    details: {json.dumps(feature['details'], ensure_ascii=False)}",
                "",
            ])
        lines.append("---")
        lines.append("")
        _atomic_write(landing, "\n".join(lines))

    def _load_wiki_settings(self) -> Dict[str, Any]:
        path = os.path.join(self.settings.codx_path, "wiki_settings.json")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    # ── misc helpers ────────────────────────────────────────────────────────

    def source_link(self, source: str) -> str:
        """Return a stable relative link to a source file, when known."""
        if not source:
            return ""
        project_root = os.path.realpath(self.settings.abs_project_path or "")
        candidate = os.path.realpath(source if os.path.isabs(source) else os.path.join(project_root, source))
        if project_root and candidate.startswith(project_root + os.sep):
            return os.path.relpath(candidate, project_root).replace(os.sep, "/")
        return source

    def assistant_context(self, max_pages: int = 40) -> List[Dict[str, str]]:
        """Return a compact page catalog suitable for an AI prompt."""
        site = self.load()
        context = []
        for page in list(site.get("pages", {}).values())[:max_pages]:
            context.append({
                "path": page["path"],
                "title": page["title"],
                "section": page.get("section", ""),
                "description": page.get("description", ""),
                "tags": ", ".join(page.get("tags", [])),
            })
        return context
