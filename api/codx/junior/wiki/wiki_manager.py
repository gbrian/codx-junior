import os
import shutil
import json
import logging
import datetime
import threading
from collections import Counter
import yaml
import re

from pathlib import Path

from slugify import slugify
from enum import Enum
from typing import List, Dict, Tuple, Any, Optional

from pydantic import BaseModel, Field

from concurrent.futures import ThreadPoolExecutor, as_completed

from aiofiles import open as aio_open

from codx.junior.settings import CODXJuniorSettings
from codx.junior.utils.utils import (
    exec_command,
    remove_starting_block,
    read_file,
    path_join
)

from codx.junior.utils.utils import (
    extract_json_blocks
)

from .model import *
from ..ai import AI
from ..events.event_manager import EventManager
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.knowledge.knowledge_db import KnowledgeDB
from codx.junior.knowledge.knowledge_loader import KnowledgeLoader
from codx.junior.knowledge.knowledge_graph import DependencyGraph
from codx.junior.wiki.wiki_domains import WikiDomains
from codx.junior.wiki.wiki_index import WikiIndex
from codx.junior.wiki.site import (
    WikiSiteBuilder,
    first_heading,
    first_paragraph,
    humanize,
    icon_for,
    parse_frontmatter,
    profile_text,
    reading_time,
)

from codx.junior.utils.utils import write_file

from langchain_core.documents import Document

from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND_MESSAGE = "No matching category found for file: %s"
WIKI_FILE_PATH_TEMPLATE = "/{slug}.md"
HOME_PAGE_UPDATE_EVENT = "Build home page"
WIKI_TREE_FILE_NAME = 'wiki_tree.json'
MKDOCS_YAML_FILE_NAME = 'mkdocs.yml'
INVALID_FILENAME_CHARS = re.compile(r'[\[\]<>:"|?*\x00-\x1f]')
MAX_FILENAME_LENGTH = 200
WIKI_BUILD_WORKERS = 3


class WikiCategory(BaseModel):
    """Defines a wiki category"""
    id: str = Field(default=None)
    title: str = Field(default=None)
    path: str = Field(default=None)
    description: str = Field(default=None)
    keywords: List[str] = Field(default=[])
    children: List[Any] = Field(default=[])
    files: List[str] = Field(default=[])


class WikiSettings(BaseModel):
    categories: List[WikiCategory] = Field(default=[])


class WikiManager:
    """
    Manager class responsible for the creation and maintenance of a project wiki
    using VitePress or MkDocs. It initializes, builds, and updates a wiki based on the project's
    structure and changes in files.
    """

    def __init__(self, settings: CODXJuniorSettings) -> None:
        self.settings: CODXJuniorSettings = settings
        self.event_manager = EventManager(codx_path=settings.codx_path)
        self.profile_manager = ProfileManager(settings=settings)
        self.wiki_path: str = settings.get_project_wiki_path()
        self.db = KnowledgeDB(settings=settings)
        self.loader = KnowledgeLoader(settings=settings)
        self.is_wiki_active = self.settings.project_wiki or False
        self.wiki_home_path = os.path.join(self.wiki_path, "home.md")
        self.wiki_settings_path = os.path.join(self.settings.codx_path, "wiki_settings.json")
        self.site_builder = WikiSiteBuilder(settings=settings)
        self._ai_instance: Optional[AI] = None
        self._ai_lock = threading.RLock()
        self._wiki_profile_text: Optional[str] = None

    # ─────────────────────────────────────────────────────────────
    # AI accessor  (cached – one instance per WikiManager lifetime)
    # ─────────────────────────────────────────────────────────────

    def _get_ai(self) -> AI:
        """Return a cached AI engine instance."""
        if self._ai_instance is None:
            self._ai_instance = AI(
                settings=self.settings,
                llm_model=self.settings.get_wiki_model(),
                user=CodxUser(username=__name__)
            )
        return self._ai_instance

    def _ai_chat(self, prompt: str, tags: str = "", clean: bool = True):
        """
        Execute an AI chat request with the given prompt.

        Args:
            prompt: The prompt to send to the AI.
            tags: Additional tags for the request.
            clean: Whether to clean markdown code fence wrapping.

        Returns:
            List of chat messages from the AI.
        """
        tags = f"{tags},wiki" if tags else "wiki"
        headers = {"tags": tags}
        # The AI client is shared by the category worker threads; serialise
        # requests through it instead of relying on provider thread-safety.
        with self._ai_lock:
            messages = self._get_ai().chat(prompt=prompt, headers=headers)
        content = messages[-1].content.strip()
        if clean and content.startswith("```"):
            content = "\n".join(content.split("\n")[1:-1])
            messages[-1].content = content
        return messages

    def _get_wiki_profile_text(self) -> str:
        """Return the rendered `wiki` profile that guides documentation style."""
        if self._wiki_profile_text is None:
            try:
                profile = self.profile_manager.read_profile("wiki")
                self._wiki_profile_text = profile_text(profile, self.settings).strip()
            except Exception as ex:
                logger.debug("Cannot read wiki profile: %s", ex)
                self._wiki_profile_text = ""
        return self._wiki_profile_text

    # ─────────────────────────────────────────────────────────────
    # Settings persistence
    # ─────────────────────────────────────────────────────────────

    def save_wiki_settings(self, wiki_settings: Any) -> Any:
        """Serialize and save wiki_settings to JSON, return reloaded settings."""
        self._fix_wiki_categories(wiki_settings)
        file_path = self._get_settings_path()
        wiki_settings["path"] = file_path
        write_file(file_path, json.dumps(wiki_settings, indent=2))
        logger.info("Wiki settings saved to %s", file_path)
        return self.load_wiki_settings()

    def _default_wiki_settings(self) -> Dict[str, Any]:
        """Default settings shared by new wikis."""
        return {
            "language": "English",
            "mode": "codx-junior",
            "prompt": "",
            "categories": [],
            "assistant": {"enabled": True},
        }

    def load_wiki_settings(self, with_files: bool = False) -> Any:
        """Read and deserialize wiki_settings from JSON."""
        file_path = self._get_settings_path()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                wiki_settings = json.load(f)
            if not isinstance(wiki_settings, dict):
                wiki_settings = self._default_wiki_settings()
            for key, value in self._default_wiki_settings().items():
                wiki_settings.setdefault(key, value)
            logger.info("Wiki settings loaded from %s", file_path)
            self._fix_wiki_categories(wiki_settings)
            return wiki_settings
        except FileNotFoundError:
            logger.info("Wiki settings file not found, using defaults: %s", file_path)
            return self._default_wiki_settings()
        except Exception as e:
            logger.exception("Error loading wiki settings: %s", e)
            return {**self._default_wiki_settings(), "error": str(e)}

    def _get_settings_path(self) -> str:
        return self.wiki_settings_path

    # ─────────────────────────────────────────────────────────────
    # Modern docs site
    # ─────────────────────────────────────────────────────────────

    def ensure_wiki_structure(self) -> str:
        """
        Create the wiki folder and seed the optional VitePress shell.

        The integrated docs UI only needs the markdown pages, but keeping the
        VitePress template means a project can still build a standalone static
        site. Existing files are never overwritten.

        Returns:
            Absolute path of the wiki folder.
        """
        os.makedirs(self.wiki_path, exist_ok=True)
        template = os.path.join(os.path.dirname(__file__), "wiki_template")
        if os.path.isdir(template):
            for root, _dirs, files in os.walk(template):
                relative = os.path.relpath(root, template)
                target_dir = self.wiki_path if relative == "." else os.path.join(self.wiki_path, relative)
                os.makedirs(target_dir, exist_ok=True)
                for filename in files:
                    # index.md is generated from docs.json so it stays in sync.
                    if relative == "." and filename in ("index.md",):
                        continue
                    source = os.path.join(root, filename)
                    target = os.path.join(target_dir, filename)
                    if not os.path.exists(target):
                        shutil.copy2(source, target)
        if not os.path.isfile(self.wiki_home_path):
            write_file(self.wiki_home_path, self._default_home_page())
        return self.wiki_path

    def _default_home_page(self) -> str:
        """Create a useful landing page without calling the AI."""
        project = self.settings.project_name or "Project"
        try:
            description = self.site_builder._project_description(project)
        except Exception:
            description = f"Documentation for {project}."
        _kind, languages = self.site_builder.project_kind()
        language_hint = f" Built with {', '.join(languages)}." if languages else ""
        header = yaml.safe_dump(
            {"title": project, "description": description, "tags": ["overview"]},
            sort_keys=False,
            allow_unicode=True,
        ).strip()
        return (
            f"---\n{header}\n---\n\n"
            f"# {project}\n\n"
            f"{description}\n\n"
            "> [!TIP]\n"
            "> This documentation is generated and kept up to date while the project "
            "changes. Use the navigation or ask the built-in assistant a question.\n\n"
            "## Start here\n\n"
            "- Browse the sections in the sidebar.\n"
            "- Use **Ask AI** for a guided answer with sources.\n"
            "- Every page is generated from the source code, so diagrams and examples "
            "reflect the current project.\n"
            f"{language_hint}\n"
        )

    # ── initial wiki creation (deterministic, no AI) ──────────────────────

    def build_default_tree(self) -> Dict[str, Any]:
        """
        Create a sensible category tree from the repository layout.

        ``create_wiki_tree`` is AI-powered and can be slow. This deterministic
        tree gives a new wiki an immediately navigable structure; the tree can
        be regenerated later from Wiki settings.
        """
        root = os.path.abspath(self.settings.abs_project_path or "")
        wiki_root = os.path.abspath(self.wiki_path)
        groups: Dict[str, List[str]] = {}
        for file_path in self.loader.list_repository_files() or []:
            absolute = os.path.abspath(file_path)
            if absolute.startswith(wiki_root):
                continue
            try:
                relative = os.path.relpath(absolute, root).replace(os.sep, "/")
            except ValueError:
                continue
            if relative.startswith("../") or relative.startswith("."):
                continue
            top = relative.split("/")[0] if "/" in relative else "project-overview"
            if top.startswith(".") or top in ("node_modules", "dist", "build", "coverage"):
                continue
            groups.setdefault(top, []).append(relative)

        if not groups:
            return self.load_wiki_settings()

        ordered = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
        selected = ordered[:8]
        overflow = [path for _group, files in ordered[8:] for path in files]

        categories = []
        for index, (group, files) in enumerate(selected):
            title = humanize(group)
            categories.append({
                "title": title,
                "description": f"Documentation for the {title} area of the project.",
                "icon": icon_for(title),
                "order": (index + 1) * 10,
                "keywords": [group],
                "children": [],
                "files": [
                    {"path": f"/{path}", "name": humanize(os.path.basename(path))}
                    for path in sorted(files)
                ],
            })
        if overflow:
            categories.append({
                "title": "Other",
                "description": "Remaining project files.",
                "icon": icon_for("other"),
                "order": 900,
                "keywords": [],
                "children": [],
                "files": [
                    {"path": f"/{path}", "name": humanize(os.path.basename(path))}
                    for path in sorted(overflow)
                ],
            })

        settings = self.load_wiki_settings()
        settings["categories"] = categories
        return self.save_wiki_settings(settings)

    def _write_category_overview(self, category: Dict[str, Any]) -> str:
        """Write a deterministic category landing page (no AI call)."""
        title = str(category.get("title") or "Overview")
        description = str(category.get("description") or f"Documentation for {title}.")
        files = category.get("files", []) or []
        rows = []
        for file in files[:40]:
            path = str(file.get("path", "")).lstrip("/")
            rows.append(f"| `{path}` | {file.get('name') or humanize(path)} |")
        more = "" if len(files) <= 40 else f"\n_…and {len(files) - 40} more files._\n"
        body = (
            f"# {title}\n\n"
            f"> **TL;DR** — {description}\n\n"
            "> [!NOTE]\n"
            "> This overview was generated from the repository layout when the wiki was created. "
            "Detailed pages are generated in the background as files change.\n\n"
            "## What's inside\n\n"
            "| File | Area |\n| --- | --- |\n"
            + "\n".join(rows)
            + f"\n{more}\n"
            "## Suggested reading\n\n"
            "- Start with the files closest to the project entry point.\n"
            "- Ask the assistant for a guided tour of this area.\n"
        )
        header = yaml.safe_dump(
            {
                "title": f"{title} overview",
                "description": description[:300],
                "tags": ["overview", "generated"],
                "category": title,
            },
            sort_keys=False,
            allow_unicode=True,
        ).strip()
        page_path = path_join(self.wiki_path, category["path"], "overview.md")
        os.makedirs(os.path.dirname(page_path), exist_ok=True)
        write_file(page_path, f"---\n{header}\n---\n\n{body}")
        return page_path

    def _initial_page_files(self, categories: List[Dict[str, Any]], limit: int = 12) -> List[str]:
        """Pick a small, useful set of files for the first AI page batch."""
        candidates: List[str] = []
        preferred = ("readme", "main", "app", "index", "entrypoint", "dockerfile")
        for category in categories:
            for file in category.get("files", []) or []:
                path = str(file.get("path", "")).lstrip("/")
                if path:
                    candidates.append(path)
        def priority(path: str) -> tuple:
            name = os.path.basename(path).lower()
            return (
                0 if name.startswith("readme") else 1,
                0 if any(token in name for token in preferred) else 1,
                len(path),
            )
        seen = set()
        selected = []
        for path in sorted(candidates, key=priority):
            if path in seen:
                continue
            seen.add(path)
            selected.append(os.path.join(self.settings.abs_project_path, path))
            if len(selected) >= limit:
                break
        return selected

    def ensure_initial_wiki(self, queue_pages: bool = False) -> bool:
        """
        Make sure the project has a wiki, creating a lightweight one if needed.

        Returns True when a wiki was created. This is the automatic path used
        for every discovered project; it deliberately does not queue a large AI
        batch unless the caller asks for it.
        """
        try:
            existing = self.site_builder.load()
            if existing and existing.get("pages"):
                return False
        except Exception:
            pass
        if not self.settings.project_wiki:
            self.settings.project_wiki = True
            saved = self.settings.save_project()
            self.settings = saved
            self.wiki_path = saved.get_project_wiki_path()
            self.wiki_home_path = os.path.join(self.wiki_path, "home.md")
            self.site_builder = WikiSiteBuilder(settings=saved)
        self.is_wiki_active = True
        self.create_initial_wiki(queue_pages=queue_pages)
        return True

    def create_initial_wiki(self, queue_pages: bool = True) -> Dict[str, Any]:
        """
        Create a usable wiki without waiting for a large AI pipeline.

        * seeds the folder/home,
        * builds a deterministic category tree when none exists,
        * writes one overview page per category,
        * rebuilds the docs manifest,
        * queues a small first batch of detailed pages in the background.
        """
        self.is_wiki_active = True
        self.ensure_wiki_structure()
        settings = self.load_wiki_settings()
        if not settings.get("categories"):
            settings = self.build_default_tree()
        settings = self.load_wiki_settings()
        categories = self._get_all_categories(settings.get("categories", []))
        for category in categories:
            if category.get("files"):
                try:
                    self._write_category_overview(category)
                except Exception as ex:
                    logger.warning("Cannot write category overview for %s: %s", category.get("title"), ex)
        site = self.build_site()
        initial_files = self._initial_page_files(categories) if queue_pages else []
        if initial_files:
            from codx.junior.wiki.scheduler import schedule_wiki_update

            schedule_wiki_update(
                self.settings,
                files=initial_files,
                reason="create-wiki",
                debounce_seconds=1,
            )
        return site

    def create_config(self) -> Dict[str, Any]:
        """Initialise the wiki folder and return its settings."""
        self.ensure_wiki_structure()
        if not os.path.isfile(self.wiki_settings_path):
            write_file(
                self.wiki_settings_path,
                json.dumps(self._default_wiki_settings(), indent=2),
            )
        return self.load_wiki_settings()

    def build_site(self, write: bool = True) -> Dict[str, Any]:
        """
        Rebuild ``docs.json`` (navigation, landing page, child projects).

        This is cheap and AI-free; it is called after every page update and by
        the parent-project refresh path.
        """
        site = self.site_builder.build(
            wiki_settings=self.load_wiki_settings(),
            write=write,
        )
        return site

    def build_home(self) -> None:
        """Regenerate the landing/overview page and the site manifest."""
        self.ensure_wiki_structure()
        existing = self._read_file(self.wiki_home_path) or ""
        self.build_wiki_home(existing)
        self.build_site()

    def build_wiki(self) -> None:
        """Backward-compatible alias used by older API clients."""
        self.rebuild_wiki()

    def update_files(self, files: List[str], reason: str = "change") -> int:
        """
        Update the wiki pages for a batch of changed files.

        Called by the debounced background scheduler. Only the changed files
        are regenerated; the site manifest is rebuilt once for the whole batch.

        Args:
            files: Absolute paths of changed project files.
            reason: Why the update runs (``change``, ``refresh``, …).

        Returns:
            Number of pages successfully regenerated.
        """
        if not self.is_wiki_active:
            logger.debug("Wiki is not active, skipping batch update")
            return 0
        self.ensure_wiki_structure()
        unique_files = []
        seen = set()
        for file_path in files or []:
            if not file_path:
                continue
            absolute = os.path.abspath(file_path)
            if absolute in seen:
                continue
            if absolute.startswith(os.path.abspath(self.wiki_path)):
                continue
            if not os.path.isfile(absolute):
                continue
            seen.add(absolute)
            unique_files.append(absolute)

        built = 0
        for file_path in unique_files:
            try:
                document = self.create_wiki_document(
                    source=file_path,
                    update_wiki_conf=False,
                )
                if document:
                    built += 1
            except Exception as ex:
                logger.exception("Cannot update wiki page for %s: %s", file_path, ex)

        self._update_wiki_conf()
        self.event_manager.send_event("wiki_updated", {
            "project": self.settings.project_name,
            "reason": reason,
            "files": len(unique_files),
            "pages": built,
        })
        if unique_files:
            logger.info(
                "Wiki batch updated for %s: %d/%d page(s)",
                self.settings.project_name,
                built,
                len(unique_files),
            )
        return built

    # ─────────────────────────────────────────────────────────────
    # Wiki tree creation
    # ─────────────────────────────────────────────────────────────

    def create_wiki_tree(self) -> Dict[str, Any]:
        """
        Analyse the repository and ask the AI to build / refresh the category tree.
        The result is persisted via save_wiki_settings and also returned.
        """
        repository_files = self.loader.list_repository_files()
        ignore_patterns = [MKDOCS_YAML_FILE_NAME, self.wiki_path]

        def is_valid_file(file_path: str) -> bool:
            return not any(p in file_path for p in ignore_patterns)

        repository_files = [
            f.replace(self.settings.abs_project_path, '')
            for f in repository_files
            if is_valid_file(f)
        ]

        # Domain hints from dependency graph
        wiki_domains = WikiDomains(settings=self.settings, db=self.db, ai=self._get_ai())
        domain_map = wiki_domains.load_domain_map()
        domain_hints = ""
        if domain_map:
            domain_hints = "<domain_hints>\n"
            for d in domain_map:
                files_sample = ", ".join(d.get("files", [])[:10])
                domain_hints += f"  Domain '{d['name']}' contains: {files_sample}\n"
            domain_hints += "</domain_hints>\n"

        repository_files_str = "\n".join(sorted(repository_files))
        logger.info("Valid wiki files:\n%s", repository_files_str)

        wiki_settings = self.load_wiki_settings()
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")

        try:
            project_info = profile_text(
                self.profile_manager.read_profile("project"), self.settings
            )
        except Exception:
            project_info = ""

        project_kind, languages = self.site_builder.project_kind()
        try:
            summary_prompt = f"""
            <project_info>
            {project_info}
            </project_info>
            <project_kind>{project_kind}</project_kind>
            <languages>{', '.join(languages)}</languages>
            <project_files>
            {repository_files_str}
            </project_files>
            {domain_hints}
            <wiki_settings>
            {json.dumps(wiki_settings, indent=2)}
            </wiki_settings>
            <wiki_profile>
            {self._get_wiki_profile_text()}
            </wiki_profile>
            <user_instructions>
            {user_instructions}
            </user_instructions>
            <user_language>
            {user_language}
            </user_language>

            Design the navigation of a modern documentation site for this project.
            Think like a senior engineer writing the docs a new teammate needs on day one:
            onboarding, architecture, guides, API/reference and operations.

            Return a wiki_settings JSON object with the updated "categories" tree and
            keep the existing top-level keys (language, mode, prompt, assistant).

            Category rules:
            - 5 to 8 top-level categories, each with a clear purpose.
            - Use children only when it genuinely helps (do not create one-child groups).
            - Every category has:
                * "title": unique, 2-4 words, sentence case, in {user_language}
                * "description": one or two sentences explaining what the reader learns
                * "icon": one Font Awesome class, e.g. "fa-solid fa-rocket"
                * "order": integer used to sort the sidebar (10, 20, 30…)
                * "keywords": list of keywords used to match files
                * "children": array of optional child categories
                * "files": list of WikiFile entries (mandatory)
            - WikiFile: {{"name": 2-4 word friendly title in {user_language}, "path": project-relative path}}.
            - Prefer a "Get started" category first, then "Guides", "Architecture",
              "API reference" (or equivalents for the project kind), then operations.
            - For non-code projects, use sections that make sense (e.g. Policies,
              Research, Processes) instead of forcing code structure.
            - Remove files that are no longer present; assign every project file to a category.

            Return ONLY the JSON object. Generated content must be in {user_language}.
            """
            messages = self._ai_chat(prompt=summary_prompt, clean=False)
            new_settings = next(extract_json_blocks(messages[-1].content))
            # Preserve top-level metadata (language, mode, prompt, assistant…)
            for key in ("language", "mode", "prompt", "assistant"):
                if key in wiki_settings and key not in new_settings:
                    new_settings[key] = wiki_settings[key]
            saved = self.save_wiki_settings(new_settings)
            self.build_site()
            return saved

        except Exception as ex:
            logger.exception("Error creating wiki tree: %s", ex)
            return {**wiki_settings, "error": str(ex)}

    # ─────────────────────────────────────────────────────────────
    # Document creation
    # ─────────────────────────────────────────────────────────────

    def create_wiki_document(self, source: str, update_wiki_conf: bool = True) -> Optional[Document]:
        """
        Generate (or refresh) the wiki page for a single source file.

        The generated page uses the modern documentation format: YAML
        frontmatter, a skimmable summary, Mermaid diagrams, runnable examples
        and callout hints. The AI is free to omit a section when it does not
        apply; the page is normalised afterwards so every page always has valid
        metadata and an H1.
        """
        if not self.is_wiki_active:
            logger.debug("Wiki is not active, skipping document creation for %s", source)
            return None

        if source and not os.path.isabs(source):
            source = os.path.join(self.settings.abs_project_path, source)
        source = os.path.abspath(source)

        # Validate source path to prevent malformed filenames
        if not self._is_valid_source_path(source):
            logger.warning("Invalid source path detected: %s", source)
            return None

        file_content = self._read_file(source)
        if not file_content:
            logger.warning("Empty or unreadable file, skipping: %s", source)
            return None

        self.ensure_wiki_structure()
        wiki_settings = self.load_wiki_settings()
        category = self._assign_category_to_file(source, wiki_settings)
        if not category:
            logger.warning(CATEGORY_NOT_FOUND_MESSAGE, source)
            return None

        title = category['title']
        keywords = category.get('keywords') or []
        project_name = self.settings.project_name
        wiki_path = category["path"]
        wiki_file_path = self._determine_wiki_file_path(category, source)

        # Validate wiki file path before attempting to read
        if not self._is_valid_wiki_file_path(wiki_file_path):
            logger.error("Invalid wiki file path generated: %s", wiki_file_path)
            return None

        current_wiki_content = ""
        if os.path.isfile(wiki_file_path):
            try:
                with open(wiki_file_path, "r", encoding="utf-8", errors="replace") as handle:
                    current_wiki_content = handle.read()
            except OSError as ex:
                logger.debug("Cannot read current wiki page %s: %s", wiki_file_path, ex)

        summary_prompt = self._prepare_summary_prompt(
            current_wiki_content, category, file_content,
            project_name, source, title, keywords, wiki_settings
        )

        messages = self._ai_chat(prompt=summary_prompt)
        page_content = self._normalize_generated_page(
            messages[-1].content,
            category=category,
            source=source,
            wiki_settings=wiki_settings,
        )

        # Append a related-pages / dependency section from the graph. This is
        # deterministic (no AI) and helps the reader jump to connected code.
        try:
            graph = DependencyGraph(settings=self.settings)
            if graph.load():
                deps = graph.get_file_deps(source)
                dep_section = self._build_dependency_section(deps, source)
                if dep_section:
                    page_content = f"{page_content.rstrip()}\n\n{dep_section}\n"
        except Exception as ex:
            logger.debug("Cannot append dependency section for %s: %s", source, ex)

        logger.info("Writing wiki document to %s", wiki_file_path)
        os.makedirs(os.path.dirname(wiki_file_path), exist_ok=True)
        write_file(wiki_file_path, page_content)

        metadata = {
            "keywords": keywords,
            "category": title,
            "source": source,
            "language": "md",
            "wiki_path": wiki_path,
            "page_path": os.path.splitext(os.path.relpath(wiki_file_path, self.wiki_path))[0].replace(os.sep, "/"),
            "updated_at": int(datetime.datetime.now().timestamp()),
        }

        if update_wiki_conf:
            self._update_wiki_conf()

        return Document(page_content, metadata=metadata)

    def _normalize_generated_page(
        self,
        content: str,
        category: Dict[str, Any],
        source: str,
        wiki_settings: Dict[str, Any],
    ) -> str:
        """
        Make an AI answer a valid, self-describing wiki page.

        * strips accidental outer code fences,
        * guarantees YAML frontmatter (title, description, tags, category, source),
        * guarantees an H1 heading,
        * keeps the body intact.
        """
        text = (content or "").strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2 and lines[-1].strip().startswith("```"):
                text = "\n".join(lines[1:-1]).strip()
        if not text:
            text = f"# {humanize(category.get('title') or source)}"

        frontmatter, body = parse_frontmatter(text)
        body = body.strip()
        title = str(
            frontmatter.get("title")
            or first_heading(body)
            or humanize(os.path.basename(source))
        )
        description = str(
            frontmatter.get("description")
            or first_paragraph(body)
            or f"Documentation for {os.path.relpath(source, self.settings.abs_project_path)}."
        )
        tags = frontmatter.get("tags") or frontmatter.get("keywords") or category.get("keywords") or []
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        updated = datetime.date.today().isoformat()
        rel_source = os.path.relpath(source, self.settings.abs_project_path).replace(os.sep, "/")
        meta = {
            "title": title,
            "description": description[:300],
            "tags": list(tags),
            "category": category.get("title", ""),
            "source": rel_source,
            "updated": updated,
        }
        if not first_heading(body):
            body = f"# {title}\n\n{body}".strip()
        try:
            header = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
        except Exception:
            header = (
                f"title: {json.dumps(title)}\n"
                f"description: {json.dumps(description[:300])}\n"
                f"category: {json.dumps(category.get('title', ''))}\n"
                f"source: {json.dumps(rel_source)}\n"
                f"updated: {updated}"
            )
        return f"---\n{header}\n---\n\n{body.strip()}\n"

    # ─────────────────────────────────────────────────────────────
    # Category / bulk build
    # ─────────────────────────────────────────────────────────────

    def build_wiki_category(self, path: str) -> None:
        """Build wiki documents for all files in the category at *path*."""
        wiki_settings = self.load_wiki_settings(with_files=True)
        categories = self._get_all_categories(wiki_settings["categories"])
        category = next((c for c in categories if c.get("path") == path), None)

        if not category:
            logger.warning("No category found for path: %s", path)
            return

        files = category.get("files", [])
        if not files:
            logger.info("Category '%s' has no files, skipping.", path)
            return

        logger.info("Building wiki category '%s' (%d files)", path, len(files))
        # Warm the repository scan before the worker threads start so parallel
        # page generation does not repeat it.
        self.site_builder.project_kind()
        self.event_manager.send_event(
            "wiki_category_start", {"path": path, "total": len(files)}
        )

        with ThreadPoolExecutor(max_workers=WIKI_BUILD_WORKERS) as executor:
            future_to_file = {
                executor.submit(self.create_wiki_document, f["path"], False): f["path"]
                for f in files
            }
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    future.result()
                    logger.info("Wiki document built: %s", file_path)
                except Exception as e:
                    logger.exception("Failed to build wiki document for %s: %s", file_path, e)

        self._update_wiki_conf()
        self.event_manager.send_event("wiki_category_done", {"path": path})

    def rebuild_wiki(self) -> None:
        """Rebuild all wiki documents for every category."""
        self.ensure_wiki_structure()
        wiki_settings = self.load_wiki_settings()
        categories = self._get_all_categories(wiki_settings["categories"])
        logger.info("Rebuilding entire wiki (%d categories)", len(categories))

        for category in categories:
            self.build_wiki_category(category["path"])

        # Final home + manifest update after all categories are done.
        self.build_wiki_home(self._read_file(self.wiki_home_path) or "")
        self.build_site()
        logger.info("Wiki rebuild complete.")

    # ─────────────────────────────────────────────────────────────
    # Home page
    # ─────────────────────────────────────────────────────────────

    def build_wiki_home(self, markdown_content: str) -> None:
        """
        Regenerate the landing page from the project overview and categories.

        The home page is the front door of the docs site: a short pitch, a
        visual map of the project, quick-start steps and links into the main
        sections. It is regenerated explicitly (settings / refresh), not on
        every single file change.
        """
        self.ensure_wiki_structure()
        wiki_settings = self.load_wiki_settings()
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")
        project_kind, languages = self.site_builder.project_kind()

        categories_without_files = [
            {k: v for k, v in cat.items() if k != "files"}
            for cat in self._get_all_categories(wiki_settings["categories"])
        ]

        existing_home = ""
        if os.path.isfile(self.wiki_home_path):
            try:
                with open(self.wiki_home_path, "r", encoding="utf-8", errors="replace") as handle:
                    existing_home = handle.read()
            except OSError:
                existing_home = ""

        if not markdown_content or not markdown_content.strip():
            markdown_content = existing_home or self._default_home_page()
        if not categories_without_files and not existing_home:
            write_file(self.wiki_home_path, self._default_home_page())
            return

        project_name = self.settings.project_name or "Project"
        project_info = ""
        try:
            project_info = profile_text(
                self.profile_manager.read_profile("project"), self.settings
            )
        except Exception:
            project_info = ""

        diagram_rule = (
            "Include a high-level `flowchart TD` Mermaid diagram that shows the "
            "main subsystems and how a request/flow moves through them."
            if project_kind == "code"
            else "Include a Mermaid diagram only if it clarifies the project structure."
        )
        relevance_prompt = f"""
<project_info>
{project_info}
</project_info>
<project_kind>{project_kind}</project_kind>
<languages>{', '.join(languages)}</languages>
<markdown_content>
{markdown_content}
</markdown_content>
<home_page_content>
{existing_home}
</home_page_content>
<categories>
{json.dumps(categories_without_files, indent=2)}
</categories>
<wiki_profile>
{self._get_wiki_profile_text()}
</wiki_profile>
<user_instructions>
{user_instructions}
</user_instructions>

Write the landing page for the {project_name} documentation site in {user_language}.
Make it feel like a modern developer portal: welcoming, skimmable and useful on
first contact. Do not repeat page contents; link to them.

Use this shape:

---
title: "{project_name}"
description: <one sentence>
tags: [overview]
---

# {project_name}

> **<One-line pitch that explains the value.>**

<2 short paragraphs: what it is, who it is for and the problem it solves.>

## What you can do here
- 3-5 outcomes the reader can achieve, each linking to a page as [Title](wiki:path).

## Architecture at a glance
{diagram_rule}
A short explanation of the main parts. Keep it high level.

## Quick start
1. 3-5 concrete first steps with commands in fenced ```bash blocks.

## Explore the docs
A compact table or list of the main sections with one-line descriptions.

## Hints
> [!TIP]
> The best reading order for a new contributor.

> [!NOTE]
> Anything to install or configure before starting.

Rules:
- Only use information present in the sources; do not invent features.
- Use links in the form [Page title](wiki:relative/path) when referencing a page.
- Keep it under ~450 words. No raw file paths as headings.
- Return only the final markdown document, without enclosing code fences.
"""
        try:
            messages = self._ai_chat(prompt=relevance_prompt)
            updated_home = messages[-1].content
            frontmatter, body = parse_frontmatter(updated_home)
            if not first_heading(body):
                body = f"# {project_name}\n\n{body}"
            if not frontmatter:
                meta = {
                    "title": project_name,
                    "description": self.site_builder._project_description(project_name),
                    "tags": ["overview"],
                }
                header = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
                updated_home = f"---\n{header}\n---\n\n{body.strip()}\n"
            os.makedirs(os.path.dirname(self.wiki_home_path), exist_ok=True)
            write_file(self.wiki_home_path, updated_home)
            logger.info("Wiki home page updated at %s", self.wiki_home_path)
        except Exception as e:
            logger.exception("Error updating wiki home page: %s", e)

    # ─────────────────────────────────────────────────────────────
    # Wiki compile / mkdocs
    # ─────────────────────────────────────────────────────────────

    def compile_wiki(self) -> None:
        """Compile the wiki: refresh the docs manifest and optional static site."""
        site = self.build_site()
        wiki_settings = self.load_wiki_settings()
        if wiki_settings.get("mode") == "mkdocs":
            self._update_mkdocs(site)

    def _update_wiki_conf(self) -> None:
        """Update the docs manifest and any optional static-site configuration."""
        site = self.build_site()
        wiki_settings = self.load_wiki_settings()
        if wiki_settings.get("mode") == "mkdocs":
            self._update_mkdocs(site)

    def _update_mkdocs(self, site: Optional[Dict[str, Any]] = None) -> None:
        """
        Keep the MkDocs navigation in sync with the docs-site manifest.

        The old implementation asked the AI to rewrite the nav on every update.
        Navigation is deterministic data, so this is now cheap and correct.
        """
        mkdocs_file_path = Path(self.settings.abs_project_path) / MKDOCS_YAML_FILE_NAME
        site = site or self.site_builder.load() or self.build_site(write=False)
        nav: List[Any] = []
        for section in site.get("navigation", []):
            items = section.get("items", [])
            if not items:
                continue
            entries = []
            for item in items:
                title = item.get("title", "")
                path = item.get("path", "")
                if path:
                    entries.append({title: f"{path}.md"})
            if entries:
                nav.append({section.get("title", "Docs"): entries})

        current: Dict[str, Any] = {}
        if mkdocs_file_path.exists():
            try:
                with open(mkdocs_file_path, "r", encoding="utf-8") as handle:
                    loaded = yaml.safe_load(handle)
                if isinstance(loaded, dict):
                    current = loaded
            except Exception as ex:
                logger.warning("Cannot read existing mkdocs.yml: %s", ex)
        current.setdefault("site_name", self.settings.project_name)
        current["nav"] = nav
        try:
            with open(mkdocs_file_path, "w", encoding="utf-8") as handle:
                yaml.dump(current, handle, default_flow_style=False, allow_unicode=True)
            logger.info("mkdocs.yml updated at %s", mkdocs_file_path)
        except Exception as e:
            logger.exception("Error updating mkdocs.yml: %s", e)

    # ─────────────────────────────────────────────────────────────
    # Dependency graph & domains
    # ─────────────────────────────────────────────────────────────

    def build_dependency_graph(self) -> DependencyGraph:
        """Build and save the project dependency graph."""
        graph = DependencyGraph(settings=self.settings)
        file_paths = self.loader.list_repository_files()
        ignore_patterns = [self.wiki_path, MKDOCS_YAML_FILE_NAME]
        file_paths = [f for f in file_paths if not any(p in f for p in ignore_patterns)]
        graph.build(file_paths)
        graph.save()
        return graph

    def build_domains(self, graph: DependencyGraph = None) -> List[Dict]:
        """Build domain-based wiki pages."""
        if graph is None:
            graph = DependencyGraph(settings=self.settings)
            if not graph.load():
                graph = self.build_dependency_graph()

        source_map = self.db.get_all_sources()
        wiki_domains = WikiDomains(settings=self.settings, db=self.db, ai=self._get_ai())
        domains = wiki_domains.detect_domains(graph=graph, source_map=source_map)

        domains_dir = os.path.join(self.wiki_path, "domains")
        os.makedirs(domains_dir, exist_ok=True)

        with ThreadPoolExecutor(max_workers=WIKI_BUILD_WORKERS) as executor:
            def _build_page(domain: Dict) -> None:
                try:
                    content = wiki_domains.build_domain_page(domain=domain, graph=graph)
                    content = self._ensure_domain_frontmatter(content, domain)
                    page_path = os.path.join(domains_dir, f"{domain['slug']}.md")
                    write_file(page_path, content)
                except Exception as ex:
                    logger.exception("Error building domain page for %s: %s", domain.get("name"), ex)

            futures = [executor.submit(_build_page, d) for d in domains]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as ex:
                    logger.exception("build_domains future error: %s", ex)

        wiki_domains.save_domain_map(domains)
        self.build_site()
        return domains

    def build_wiki_index(self, graph: DependencyGraph = None, domains: List[Dict] = None) -> Dict:
        """Build and index wiki content."""
        if graph is None:
            graph = DependencyGraph(settings=self.settings)
            if not graph.load():
                graph = self.build_dependency_graph()
        if domains is None:
            wiki_domains = WikiDomains(settings=self.settings, db=self.db, ai=self._get_ai())
            domains = wiki_domains.load_domain_map()

        wiki_settings = self.load_wiki_settings()
        self.build_site()
        wiki_index = WikiIndex(settings=self.settings, db=self.db)
        index = wiki_index.build(wiki_settings=wiki_settings, domain_map=domains, graph=graph)
        wiki_index.save(index)
        wiki_index.index_to_milvus(index)
        return index

    def _ensure_domain_frontmatter(self, content: str, domain: Dict[str, Any]) -> str:
        """Guarantee frontmatter/description on an AI-generated domain page."""
        text = (content or "").strip()
        frontmatter, body = parse_frontmatter(text)
        title = str(frontmatter.get("title") or first_heading(body) or domain.get("name") or "Domain")
        description = str(
            frontmatter.get("description")
            or domain.get("description")
            or first_paragraph(body)
        )
        if not first_heading(body):
            body = f"# {title}\n\n{body}".strip()
        if not frontmatter:
            meta = {
                "title": title,
                "description": description[:300],
                "tags": ["architecture", "domain"],
                "category": "Architecture",
            }
            header = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
            return f"---\n{header}\n---\n\n{body.strip()}\n"
        return f"---\n{yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()}\n---\n\n{body.strip()}\n"

    def build_module_page(self, file_path: str, graph: DependencyGraph = None) -> str:
        """
        Generate a reference page for one source file.

        The page is written to ``wiki/modules/<slug>.md`` and uses the same
        modern format as the rest of the site: summary, diagram, dependencies,
        example and hints.
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.settings.abs_project_path, file_path)
        file_path = os.path.abspath(file_path)
        if graph is None:
            graph = DependencyGraph(settings=self.settings)
            if not graph.load():
                graph = self.build_dependency_graph()

        deps = graph.get_file_deps(file_path)
        file_content = self._read_file(file_path)
        if not file_content:
            logger.warning("Cannot build module page for empty file: %s", file_path)
            return ""
        rel_path = os.path.relpath(file_path, self.settings.abs_project_path).replace(os.sep, "/")

        imports_str = "\n".join(deps.get("imports", [])) or "none"
        imported_by_str = "\n".join(deps.get("imported_by", [])) or "none"
        external_str = ", ".join(deps.get("external_deps", [])) or "none"

        prompt = f"""
<file_path>{rel_path}</file_path>
<file_content>
{file_content}
</file_content>
<imports>
{imports_str}
</imports>
<imported_by>
{imported_by_str}
</imported_by>
<external_deps>{external_str}</external_deps>

<wiki_profile>
{self._get_wiki_profile_text()}
</wiki_profile>

Generate a modern reference page for this module in the same format used by the
rest of the wiki. Use YAML frontmatter then:

---
title: <module title>
description: <one sentence>
tags: [reference, module]
category: "API Reference"
source: "{rel_path}"
---

# <title>

> **TL;DR** — what this module is responsible for.

## Overview
## API / Exported symbols
Use a table for public functions, classes or commands with parameters and
return values when the code exposes them.

## How it works
Include a Mermaid `flowchart TD` or `sequenceDiagram` for the main flow.

## Example
A realistic runnable example with a language-tagged code fence.

## Dependencies
**Imports from:** {imports_str}
**Imported by:** {imported_by_str}
**External dependencies:** {external_str}

## Hints
> [!TIP]
> A useful usage detail.

> [!WARNING]
> An edge case or common mistake.

Return only the markdown document, no enclosing fences.
"""
        try:
            messages = self._ai_chat(prompt=prompt)
            page_content = self._normalize_generated_page(
                messages[-1].content,
                category={"title": "API Reference", "keywords": ["reference", "module"]},
                source=file_path,
                wiki_settings=self.load_wiki_settings(),
            )
            slug = slugify(rel_path)
            module_dir = os.path.join(self.wiki_path, "modules")
            os.makedirs(module_dir, exist_ok=True)
            page_path = os.path.join(module_dir, f"{slug}.md")
            write_file(page_path, page_content)
            self.build_site()
            return page_content
        except Exception as ex:
            logger.exception("Error building module page for %s: %s", file_path, ex)
            return ""

    # ─────────────────────────────────────────────────────────────
    # Single-file entry point (called by ChangeManager)
    # ─────────────────────────────────────────────────────────────

    def build_file(self, file_path: str) -> None:
        """Called by ChangeManager when a single file changes."""
        self.create_wiki_document(source=file_path)

    def update_category_home(self, documents: List[Document]) -> None:
        """Placeholder – aggregate category-level home page (not yet implemented)."""
        pass

    # ─────────────────────────────────────────────────────────────
    # File path validation helpers
    # ─────────────────────────────────────────────────────────────

    def _is_valid_source_path(self, file_path: str) -> bool:
        """
        Validate that the source path is a legitimate file path.
        Reject paths that contain invalid characters or patterns from code/markdown.

        Checks for:
        - Non-string types
        - Markdown/code syntax patterns (```, [, etc.)
        - Invalid filesystem characters (brackets, pipes, etc.)
        - Path traversal attempts
        - Paths that don't end with file extensions

        Args:
            file_path: The path to validate.

        Returns:
            True if the path is valid, False otherwise.
        """
        if not isinstance(file_path, str):
            logger.error("Source path must be a string, got %s", type(file_path))
            return False

        # Check for empty or whitespace-only paths
        if not file_path or not file_path.strip():
            logger.warning("Source path is empty or whitespace-only: %s", file_path)
            return False

        # Check for markdown/code patterns that shouldn't be file paths
        if file_path.startswith("```"):
            logger.warning("Source path looks like code block start: %s", file_path)
            return False

        if file_path.startswith("["):
            logger.warning("Source path looks like markdown link: %s", file_path)
            return False

        # Check for any markdown inline code or other special markup
        if file_path.startswith("`") or file_path.startswith("*"):
            logger.warning("Source path looks like markdown formatting: %s", file_path)
            return False

        # Normalize path to catch various forms
        try:
            normalized = os.path.normpath(file_path)
        except (ValueError, TypeError) as e:
            logger.warning("Failed to normalize path %s: %s", file_path, e)
            return False

        # Check for path traversal attempts
        if ".." in normalized or normalized.startswith(".."):
            logger.warning("Path traversal attempt detected: %s", file_path)
            return False

        # Check for invalid filesystem characters that might slip through
        if INVALID_FILENAME_CHARS.search(file_path):
            logger.warning("Invalid filesystem characters in path: %s", file_path)
            return False

        # Reject paths without extensions (likely malformed)
        # Exception: allow paths that are clearly directories (should have slashes)
        if os.path.sep in file_path or "/" in file_path:
            # It's a path with directories, which is ok
            pass
        elif "." not in os.path.basename(file_path):
            # Single filename without extension - reject it
            logger.warning("Path has no file extension (likely malformed): %s", file_path)
            return False

        return True

    def _is_valid_wiki_file_path(self, file_path: str) -> bool:
        """
        Validate that the wiki file path is safe to write to.
        Check for invalid filename characters and excessive length.

        Args:
            file_path: The wiki file path to validate.

        Returns:
            True if the path is safe to use, False otherwise.
        """
        try:
            # Ensure path is normalized
            normalized = os.path.normpath(file_path)

            # Check each component for invalid characters
            for part in normalized.split(os.sep):
                if not part:
                    # Empty component (e.g., from double slashes) - skip
                    continue

                # Check for invalid characters
                if INVALID_FILENAME_CHARS.search(part):
                    logger.warning("Invalid characters in wiki file path component '%s'", part)
                    return False

                # Check for excessive length
                if len(part) > MAX_FILENAME_LENGTH:
                    logger.warning(
                        "Wiki file path component too long: '%s' (%d chars, max %d)",
                        part,
                        len(part),
                        MAX_FILENAME_LENGTH
                    )
                    return False

            return True
        except Exception as e:
            logger.exception("Error validating wiki file path %s: %s", file_path, e)
            return False

    # ─────────────────────────────────────────────────────────────
    # Category helpers
    # ─────────────────────────────────────────────────────────────

    def _find_category_for_file(
        self, file_path: str, all_categories: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find the category that contains the given file."""
        file_path = file_path.replace(self.settings.abs_project_path, '')
        for category in all_categories:
            for f in category.get("files", []):
                if f.get("path", "") == file_path:
                    return category
        return None

    def _assign_category_to_file(
        self, source: str, wiki_settings: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Assign a file to a category, using AI if necessary."""
        all_categories = self._get_all_categories(wiki_settings["categories"])
        category = self._find_category_for_file(file_path=source, all_categories=all_categories)
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")

        if not category:
            if not all_categories:
                logger.warning("No categories defined in wiki_settings, cannot assign file: %s", source)
                return None

            categories_and_keywords = [
                {"path": c["path"], "title": c["title"], "keywords": c["keywords"]}
                for c in all_categories
            ]

            summary_prompt = f"""
            <document>
            {self._read_file(source)}
            </document>
            <categories>
            {json.dumps(categories_and_keywords, indent=2)}
            </categories>
            <user_instructions>
            {user_instructions}
            </user_instructions>
            <user_language>
            {user_language}
            </user_language>

            Analyze this document and match the best category from the list of categories for this document.
            Only categories from the list are valid responses.
            Return a JSON dictionary with a single field "path" containing the chosen category path.
            Generated content must be in user_language: {user_language}
            """
            try:
                messages = self._ai_chat(prompt=summary_prompt, clean=False)
                metadata = next(extract_json_blocks(messages[-1].content))
                wiki_path = metadata["path"]
                category = next(
                    (c for c in all_categories if c["path"] == wiki_path), None
                )
                if category is None:
                    logger.warning("AI returned unknown category path '%s' for %s", wiki_path, source)
                    # Fall back to first category
                    category = all_categories[0]
            except Exception as ex:
                logger.exception("Error assigning category to %s: %s", source, ex)
                category = all_categories[0] if all_categories else None

            if category is not None:
                # Register file in category and persist
                if "files" not in category:
                    category["files"] = []
                rel_source = source.replace(self.settings.abs_project_path, '')
                if not any(f.get("path") == rel_source for f in category["files"]):
                    category["files"].append({
                        "path": rel_source,
                        "name": humanize(os.path.basename(rel_source)),
                    })
                    self.save_wiki_settings(wiki_settings)

        return category

    def _determine_wiki_file_path(self, category: Dict[str, Any], source: str) -> str:
        """
        Determine the wiki file path for a source file.

        Args:
            category: The category containing the file.
            source: The source file path.

        Returns:
            The full wiki file path.
        """
        if category.get("single_file", False):
            return path_join(self.wiki_path, f"{category['path']}.md")
        rel_source = os.path.relpath(source, self.settings.abs_project_path).replace(os.sep, "/")
        self._assign_category_file_slugs(category)
        entry = next(
            (file for file in category.get("files", [])
             if str(file.get("path", "")).lstrip("/") == rel_source),
            None,
        )
        filename = entry.get("slug") if entry else self._get_file_wiki_name(source)
        return path_join(self.wiki_path, category["path"], filename)

    def _prepare_summary_prompt(
        self,
        current_wiki_content: str,
        category: Dict[str, Any],
        file_content: str,
        project_name: str,
        source: str,
        title: str,
        keywords: List[str],
        wiki_settings: Dict[str, Any],
    ) -> str:
        """
        Build the prompt that turns one source file into a modern wiki page.

        The format is deliberately opinionated: a skimmable summary, a
        diagram when the content is structural, a runnable example and short
        callout hints. This is what makes the generated docs feel like a
        hand-written developer portal instead of a wall of text.
        """
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")
        project_kind, languages = self.site_builder.project_kind()
        rel_source = os.path.relpath(source, self.settings.abs_project_path).replace(os.sep, "/")
        language_text = ", ".join(languages) or "n/a"
        diagram_rule = (
            "Include at least one Mermaid diagram that explains the control flow, "
            "module relationships or data flow. Use `flowchart TD` for flows, "
            "`sequenceDiagram` for interactions and `classDiagram` only when it adds clarity."
            if project_kind == "code"
            else "Use a Mermaid diagram only when it genuinely clarifies a process or relationship."
        )
        example_rule = (
            "Include at least one realistic, runnable example (imports + call + expected result) "
            "taken from the code. Label the language in the fence."
            if project_kind == "code"
            else "Include a concrete example or a short template when it helps the reader act."
        )
        wiki_profile = self._get_wiki_profile_text()
        style = f"""
<wiki_profile>
{wiki_profile}
</wiki_profile>

You are documenting the project "{project_name}" for developers who are new to
this file. Write like a senior engineer: concrete, skimmable and honest about
trade-offs. Never invent APIs, options or behaviour.

Return ONE markdown document in {user_language} using exactly this shape (omit
a section only when it truly does not apply):

---
title: <2-5 word page title, sentence case>
description: <one sentence a reader could use to decide whether to open the page>
tags: [<3-6 short lowercase tags>]
category: "{title}"
source: "{rel_source}"
---

# <title>

> **TL;DR** — one or two sentences explaining what this is and why it matters.

## What you'll learn
- 2-4 concrete takeaways.

## Overview
Short contextual explanation. Link related concepts as [Page title](wiki:page/path).

## How it works
{diagram_rule}
Explain the flow in short paragraphs or numbered steps. Reference real symbols
and files with inline code, never a raw file path as a heading.

## Example
{example_rule}

## Hints
> [!TIP]
> A practical tip that saves time.

> [!WARNING]
> A common mistake, edge case or requirement to watch out for.

## Related
- [Related page](wiki:relative/path) — why it matters.

Rules:
- Project kind: {project_kind}; languages: {language_text}.
- Use sentence case headings, short paragraphs, lists and tables where useful.
- Code fences must include a language (```python, ```bash, ```json…).
- Keep the page under ~700 words. Prefer linking to another page over repeating it.
- Do not wrap the whole document in ``` fences and do not repeat the file path as a title.
- Use callouts (`> [!TIP]`, `> [!WARNING]`, `> [!NOTE]`) for hints, pitfalls and requirements.
- Stay grounded in the provided document; if something is unknown, say so.
"""
        if current_wiki_content and category.get("single_file", False):
            return f"""
<current_wiki_content>
{current_wiki_content}
</current_wiki_content>

<new_document_content>
{file_content}
</new_document_content>

<user_instructions>
{user_instructions}
</user_instructions>

{style}

Update the existing page with the new information. Preserve accurate details,
remove duplicates and restructure to the format above. The result must be a
complete document without enclosing marks.
"""
        return f"""
<document project="{project_name}" file="{rel_source}" category="{title}" keywords="{keywords}">
{file_content}
</document>

<user_instructions>
{user_instructions}
</user_instructions>

{style}

Generate the page for this document.
"""

    def _create_changeset_document(
        self, current_wiki_content: str, page_content: str, source: str
    ) -> str:
        """
        Create a summary of changes between wiki versions.

        Args:
            current_wiki_content: The previous wiki content.
            page_content: The new wiki content.
            source: The source file path.

        Returns:
            A formatted changeset document.
        """
        prompt = f"""
        <old_wiki>
        {current_wiki_content}
        </old_wiki>
        <new_wiki>
        {page_content}
        </new_wiki>

        Concisely explain the changes made to the wiki page for {source}.
        Focus on what is new, removed, or significantly altered.
        """
        changes = self._ai_chat(prompt=prompt)[-1].content
        return f'<wiki_changes source="{source}">\n{changes}\n</wiki_changes>'

    def _build_dependency_section(self, deps: Dict[str, Any], source: str) -> str:
        """
        Build a dependency section for the wiki page.

        Args:
            deps: Dictionary of dependencies from the dependency graph.
            source: The source file path.

        Returns:
            Formatted markdown dependency section, or empty string if no deps.
        """
        imports = deps.get("imports", [])
        imported_by = deps.get("imported_by", [])
        if not imports and not imported_by:
            return ""
        lines = ["## Dependencies"]
        if imports:
            lines.append(f"**Imports from:** {', '.join(imports)}")
        if imported_by:
            lines.append(f"**Imported by:** {', '.join(imported_by)}")
        return "\n".join(lines)

    def _get_all_categories(
        self,
        categories: List[Dict[str, Any]],
        flattened_list: Optional[List[Dict[str, Any]]] = None,
        parent: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Flatten the hierarchical category tree into a single list,
        assigning each category a unique slugified *path*.

        Args:
            categories: List of category definitions.
            flattened_list: Accumulator for flattened categories (auto-initialized).
            parent: Parent category context.

        Returns:
            Flattened list of all categories and subcategories.
        """
        if flattened_list is None:
            flattened_list = []

        parent_path = slugify(parent.get("path", "")) if parent else ""

        for category in categories:
            _id = slugify(category.get("title", "unknown"))
            category["id"] = _id
            category["path"] = f"{parent_path}/{_id}" if parent_path else _id
            flattened_list.append(category)

            children = category.get("children", [])
            if children:
                self._get_all_categories(children, flattened_list, category)

        return flattened_list

    def _fix_wiki_categories(self, wiki_settings: Dict[str, Any]) -> None:
        """
        Ensure every category and file entry has correct path/slug metadata.

        Args:
            wiki_settings: The wiki settings dictionary to fix in-place.
        """
        categories = self._get_all_categories(wiki_settings.get("categories", []))
        for category in categories:
            if not category.get("path"):
                category["path"] = slugify(category.get("title", "unknown"))
            category.setdefault("keywords", [])
            if not isinstance(category.get("keywords"), list):
                category["keywords"] = [
                    keyword.strip()
                    for keyword in str(category.get("keywords", "")).split(",")
                    if keyword.strip()
                ]
            category["files"] = [
                {"path": file} if isinstance(file, str) else file
                for file in (category.get("files") or [])
                if (file.get("path") if isinstance(file, dict) else file)
            ]
            for file in category["files"]:
                file["name"] = file.get("name") or humanize(os.path.basename(file["path"]))
            self._assign_category_file_slugs(category)

    def _read_file(self, file_path: str) -> str:
        """
        Read a file from the project.

        Args:
            file_path: Path to the file to read.

        Returns:
            The file content as a string.
        """
        return read_file(file_path, self.settings.abs_project_path)

    def _assign_category_file_slugs(self, category: Dict[str, Any]) -> None:
        """
        Give every file in a category a stable, unique wiki filename.

        Basenames are used when unique. When two files in the same category
        share a basename (``src/api/index.ts`` and ``src/web/index.ts``), the
        project-relative path is slugified instead, and a numeric suffix is
        appended as a last resort. This prevents one page silently overwriting
        another.
        """
        files = [file for file in (category.get("files") or []) if file.get("path")]
        base_counts = Counter(
            slugify(os.path.splitext(os.path.basename(str(file["path"])))[0]) or "document"
            for file in files
        )
        used = set()
        for file in files:
            path = str(file["path"]).replace(os.sep, "/")
            base = slugify(os.path.splitext(os.path.basename(path))[0]) or "document"
            if base_counts[base] > 1:
                base = slugify(os.path.splitext(path)[0]) or base
            candidate = base
            suffix = 2
            while candidate in used:
                candidate = f"{base}-{suffix}"
                suffix += 1
            used.add(candidate)
            file["slug"] = f"{candidate}.md"
            file["wiki_file"] = path_join(
                self.wiki_path, category["path"], file["slug"]
            )

    def _get_file_wiki_name(self, source: str) -> str:
        """Generate a safe wiki filename from a source file path."""
        filename = os.path.basename(source)
        name_without_ext = os.path.splitext(filename)[0]
        safe_slug = slugify(name_without_ext)
        if not safe_slug:
            safe_slug = "document"
        return f"{safe_slug}.md"

# Made with ❤️ by codx-junior