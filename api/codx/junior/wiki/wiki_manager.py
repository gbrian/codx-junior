import os
import shutil
import json
import logging
import datetime
import yaml

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

from codx.junior.utils.utils import write_file

from langchain_core.documents import Document

from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND_MESSAGE = "No matching category found for file: %s"
WIKI_FILE_PATH_TEMPLATE = "/{slug}.md"
HOME_PAGE_UPDATE_EVENT = "Build home page"
WIKI_TREE_FILE_NAME = 'wiki_tree.json'
MKDOCS_YAML_FILE_NAME = 'mkdocs.yml'


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
        self._ai_instance: Optional[AI] = None

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
        tags = f"{tags},wiki" if tags else "wiki"
        headers = {"tags": tags}
        messages = self._get_ai().chat(prompt=prompt, headers=headers)
        content = messages[-1].content.strip()
        if clean and content.startswith("```"):
            content = "\n".join(content.split("\n")[1:-1])
            messages[-1].content = content
        return messages

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

    def load_wiki_settings(self, with_files: bool = False) -> Any:
        """Read and deserialize wiki_settings from JSON."""
        try:
            file_path = self._get_settings_path()
            with open(file_path, 'r') as f:
                wiki_settings = json.load(f)
            logger.info("Wiki settings loaded from %s", file_path)
            self._fix_wiki_categories(wiki_settings)
            return wiki_settings
        except Exception as e:
            logger.exception("Error loading wiki settings: %s", e)
            return {"categories": [], "error": str(e)}

    def _get_settings_path(self) -> str:
        return self.wiki_settings_path

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
            project_info = self.profile_manager.read_profile("project").content
        except Exception:
            project_info = ""

        try:
            summary_prompt = f"""
            <project_info>
            {project_info}
            </project_info>
            <project_files>
            {repository_files_str}
            </project_files>
            {domain_hints}
            <wiki_settings>
            {json.dumps(wiki_settings, indent=2)}
            </wiki_settings>
            <user_instructions>
            {user_instructions}
            </user_instructions>
            <user_language>
            {user_language}
            </user_language>

            We are defining the project's documentation wiki to help new users understand and manage the project.
            Update the wiki structure based on the project's information that can assist users with onboarding, learning and (if apply) executing the project.
            Use domain_hints (if provided) to group files into coherent categories that reflect actual code dependencies.
            Detect which kind of project is and choose and structure it wisely into categories and subcategories.
            Update wiki tree definition from given updated information about the project and its folders.
            A wiki tree will split the project into 6 top-level categories for the main project's sections/functionalities.
            Top-level categories can have "children" categories.
            A category entry is defined in a json with fields:
                * "title": Unique category title. Can't be repeated in by any other category or subcategory.
                * "description": An 8 lines category description
                * "keywords": List of keyword to check if a file belongs to the category
                * "children": An array of category entries
                * "files": (Mandatory) The list of WikiFile matching this category.
            WikiFile object has this properties:
                * "name": A short user friendly name fo this file in {user_language} that gives some hint about the file. Can contain 2 or 3 words, no more.
                * "path": File path
            Remove all WikiFiles that are not present in project_files.
            Make sure all project_files has been assigned to a category.
            Return updated wiki_settings JSON object.
            Generated content must be in user_language: {user_language}
            """
            messages = self._ai_chat(prompt=summary_prompt, clean=False)
            new_settings = next(extract_json_blocks(messages[-1].content))
            # Preserve top-level metadata (language, mode, prompt, …) from existing settings
            for key in ("language", "mode", "prompt"):
                if key in wiki_settings and key not in new_settings:
                    new_settings[key] = wiki_settings[key]
            # Persist and return
            return self.save_wiki_settings(new_settings)

        except Exception as ex:
            logger.exception("Error creating wiki tree: %s", ex)
            return {**wiki_settings, "error": str(ex)}

    # ─────────────────────────────────────────────────────────────
    # Document creation
    # ─────────────────────────────────────────────────────────────

    def create_wiki_document(self, source: str, update_wiki_conf: bool = True) -> Optional[Document]:
        """Generate (or refresh) the wiki page for a single source file."""
        if not self.is_wiki_active:
            logger.debug("Wiki is not active, skipping document creation for %s", source)
            return None

        file_content = self._read_file(source)
        if not file_content:
            logger.warning("Empty or unreadable file, skipping: %s", source)
            return None

        wiki_settings = self.load_wiki_settings()
        category = self._assign_category_to_file(source, wiki_settings)
        if not category:
            logger.warning(CATEGORY_NOT_FOUND_MESSAGE, source)
            return None

        title = category['title']
        keywords = category['keywords']
        project_name = self.settings.project_name
        wiki_path = category["path"]
        wiki_file_path = self._determine_wiki_file_path(category, source)

        current_wiki_content = (
            self._read_file(wiki_file_path)
            if os.path.isfile(wiki_file_path)
            else ""
        )

        summary_prompt = self._prepare_summary_prompt(
            current_wiki_content, category, file_content,
            project_name, source, title, keywords, wiki_settings
        )

        messages = self._ai_chat(prompt=summary_prompt)
        page_content = messages[-1].content

        # Append dependency section from graph
        graph = DependencyGraph(settings=self.settings)
        if graph.load():
            deps = graph.get_file_deps(source)
            dep_section = self._build_dependency_section(deps, source)
            if dep_section:
                page_content = f"{page_content}\n\n{dep_section}"

        logger.info("Writing wiki document to %s", wiki_file_path)
        os.makedirs(os.path.dirname(wiki_file_path), exist_ok=True)
        write_file(wiki_file_path, page_content)

        metadata = {
            "keywords": keywords,
            "category": title,
            "source": source,
            "language": "md",
            "wiki_path": wiki_path,
        }

        # Build changeset summary for home-page update
        if current_wiki_content:
            home_update_content = self._create_changeset_document(
                current_wiki_content, page_content, source
            )
        else:
            # New page – feed the full content to home so it can decide relevance
            home_update_content = page_content

        self.build_wiki_home(home_update_content)

        if update_wiki_conf:
            self._update_wiki_conf()

        return Document(page_content, metadata=metadata)

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
        self.event_manager.send_event(
            "wiki_category_start", {"path": path, "total": len(files)}
        )

        with ThreadPoolExecutor() as executor:
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
        wiki_settings = self.load_wiki_settings()
        categories = self._get_all_categories(wiki_settings["categories"])
        logger.info("Rebuilding entire wiki (%d categories)", len(categories))

        for category in categories:
            self.build_wiki_category(category["path"])

        # Final home + config update after all categories are done
        self.build_wiki_home(self._read_file(self.wiki_home_path) or "")
        self._update_wiki_conf()
        logger.info("Wiki rebuild complete.")

    # ─────────────────────────────────────────────────────────────
    # Home page
    # ─────────────────────────────────────────────────────────────

    def build_wiki_home(self, markdown_content: str) -> None:
        """
        Decide whether *markdown_content* contains information worth showing on the
        wiki landing page and, if so, update home.md accordingly.
        """
        if not markdown_content or not markdown_content.strip():
            logger.debug("build_wiki_home called with empty content – skipping.")
            return

        wiki_settings = self.load_wiki_settings()
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")

        categories_without_files = [
            {k: v for k, v in cat.items() if k != "files"}
            for cat in self._get_all_categories(wiki_settings["categories"])
        ]

        existing_home = ""
        if os.path.isfile(self.wiki_home_path):
            existing_home = self._read_file(self.wiki_home_path) or ""

        relevance_prompt = f"""
        <markdown_content>
        {markdown_content}
        </markdown_content>
        <home_page_content>
        {existing_home}
        </home_page_content>
        <categories>
        {json.dumps(categories_without_files, indent=2)}
        </categories>
        <user_instructions>
        {user_instructions}
        </user_instructions>
        <user_language>
        {user_language}
        </user_language>

        Analyze the provided markdown content and decide if it contains important information
        that should be included in the front page of the wiki. If relevant, update the home page
        content with this information. Ensure that content is coherent and well-structured.
        The home page must show a high-level overview – do not go into implementation details;
        users will navigate the wiki for that.
        Generated content must be in user_language: {user_language}.
        Generate ONLY the final home document content without any extra comments or code fences.
        """

        try:
            messages = self._ai_chat(prompt=relevance_prompt)
            updated_home = messages[-1].content
            os.makedirs(os.path.dirname(self.wiki_home_path), exist_ok=True)
            write_file(self.wiki_home_path, updated_home)
            logger.info("Wiki home page updated at %s", self.wiki_home_path)
        except Exception as e:
            logger.exception("Error updating wiki home page: %s", e)

    # ─────────────────────────────────────────────────────────────
    # Wiki compile / mkdocs
    # ─────────────────────────────────────────────────────────────

    def compile_wiki(self) -> None:
        wiki_settings = self.load_wiki_settings()
        if wiki_settings.get("mode") == "mkdocs":
            self._update_mkdocs()

    def _update_wiki_conf(self) -> None:
        wiki_settings = self.load_wiki_settings()
        if wiki_settings.get("mode") == "mkdocs":
            self._update_mkdocs()

    def _update_mkdocs(self) -> None:
        """Use AI to regenerate the nav section of mkdocs.yml."""
        mkdocs_file_path = Path(self.settings.abs_project_path) / MKDOCS_YAML_FILE_NAME

        wiki_settings = self.load_wiki_settings()
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")

        current_mkdocs_content: Dict[str, Any] = {"nav": []}
        if mkdocs_file_path.exists():
            with open(mkdocs_file_path, 'r') as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    current_mkdocs_content = loaded

        wiki_files: List[str] = []
        for root, _dirs, files in os.walk(self.wiki_path):
            for file in files:
                if file != MKDOCS_YAML_FILE_NAME:
                    wiki_files.append(
                        os.path.relpath(os.path.join(root, file), self.wiki_path)
                    )
        wiki_files.sort()

        update_prompt = f"""
        <current_nav_section>
        {yaml.dump(current_mkdocs_content.get('nav', []), default_flow_style=False)}
        </current_nav_section>
        <wiki_files>
        {chr(10).join(wiki_files)}
        </wiki_files>
        <user_instructions>
        {user_instructions}
        </user_instructions>
        <user_language>
        {user_language}
        </user_language>

        Update the 'nav' section of the mkdocs.yaml to reflect all current wiki files.
        Ensure the navigation structure remains clear and logical, grouping pages sensibly.
        Return ONLY the updated 'nav' section as a raw YAML list (no enclosing dict, no code fences).
        Generated content must be in user_language: {user_language}
        """

        try:
            messages = self._ai_chat(prompt=update_prompt)
            raw = messages[-1].content.strip()
            # AI may return bare list OR {"nav": [...]}
            parsed = yaml.safe_load(raw)
            if isinstance(parsed, dict) and "nav" in parsed:
                updated_nav = parsed["nav"]
            elif isinstance(parsed, list):
                updated_nav = parsed
            else:
                logger.warning("Unexpected mkdocs nav format from AI, skipping update.")
                return

            current_mkdocs_content["nav"] = updated_nav
            with open(mkdocs_file_path, 'w') as f:
                yaml.dump(current_mkdocs_content, f, default_flow_style=False, allow_unicode=True)
            logger.info("mkdocs.yml updated at %s", mkdocs_file_path)
        except Exception as e:
            logger.exception("Error updating mkdocs.yml: %s", e)

    # ─────────────────────────────────────────────────────────────
    # Dependency graph & domains
    # ─────────────────────────────────────────────────────────────

    def build_dependency_graph(self) -> DependencyGraph:
        graph = DependencyGraph(settings=self.settings)
        file_paths = self.loader.list_repository_files()
        ignore_patterns = [self.wiki_path, MKDOCS_YAML_FILE_NAME]
        file_paths = [f for f in file_paths if not any(p in f for p in ignore_patterns)]
        graph.build(file_paths)
        graph.save()
        return graph

    def build_domains(self, graph: DependencyGraph = None) -> List[Dict]:
        if graph is None:
            graph = DependencyGraph(settings=self.settings)
            if not graph.load():
                graph = self.build_dependency_graph()

        source_map = self.db.get_all_sources()
        wiki_domains = WikiDomains(settings=self.settings, db=self.db, ai=self._get_ai())
        domains = wiki_domains.detect_domains(graph=graph, source_map=source_map)

        domains_dir = os.path.join(self.wiki_path, "domains")
        os.makedirs(domains_dir, exist_ok=True)

        with ThreadPoolExecutor() as executor:
            def _build_page(domain: Dict) -> None:
                try:
                    content = wiki_domains.build_domain_page(domain=domain, graph=graph)
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
        return domains

    def build_wiki_index(self, graph: DependencyGraph = None, domains: List[Dict] = None) -> Dict:
        if graph is None:
            graph = DependencyGraph(settings=self.settings)
            if not graph.load():
                graph = self.build_dependency_graph()
        if domains is None:
            wiki_domains = WikiDomains(settings=self.settings, db=self.db, ai=self._get_ai())
            domains = wiki_domains.load_domain_map()

        wiki_settings = self.load_wiki_settings()
        wiki_index = WikiIndex(settings=self.settings, db=self.db)
        index = wiki_index.build(wiki_settings=wiki_settings, domain_map=domains, graph=graph)
        wiki_index.save(index)
        wiki_index.index_to_milvus(index)
        return index

    def build_module_page(self, file_path: str, graph: DependencyGraph = None) -> str:
        if graph is None:
            graph = DependencyGraph(settings=self.settings)
            if not graph.load():
                graph = self.build_dependency_graph()

        deps = graph.get_file_deps(file_path)
        file_content = self._read_file(file_path)
        rel_path = file_path.replace(self.settings.abs_project_path, "")

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

Generate a markdown L2 module page for this file.
Include these sections:
# Module: {rel_path}
## Overview
## Exported Symbols
## Dependencies
**Imports from:** (list internal imports)
**Imported by:** (list files that import this)
**External dependencies:** (list external packages)
## Usage Examples

Do not add code fences around the entire document.
"""
        try:
            messages = self._ai_chat(prompt=prompt)
            page_content = messages[-1].content
            slug = slugify(rel_path)
            module_dir = os.path.join(self.wiki_path, "modules")
            os.makedirs(module_dir, exist_ok=True)
            page_path = os.path.join(module_dir, f"{slug}.md")
            write_file(page_path, page_content)
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
    # Category helpers
    # ─────────────────────────────────────────────────────────────

    def _find_category_for_file(
        self, file_path: str, all_categories: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        file_path = file_path.replace(self.settings.abs_project_path, '')
        for category in all_categories:
            for f in category.get("files", []):
                if f.get("path", "") == file_path:
                    return category
        return None

    def _assign_category_to_file(
        self, source: str, wiki_settings: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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
                    category["files"].append({"path": rel_source})
                    self.save_wiki_settings(wiki_settings)

        return category

    def _determine_wiki_file_path(self, category: Dict[str, Any], source: str) -> str:
        if category.get("single_file", False):
            return path_join(self.wiki_path, f"{category['path']}.md")
        return path_join(self.wiki_path, category["path"], self._get_file_wiki_name(source))

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
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")

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
            <user_language>
            {user_language}
            </user_language>

            Update the current wiki content with the new information coming from the document.
            Resulting document must be in markdown syntax without further decoration or enclosing marks.
            Ensure the updated content is coherent and well-structured.
            Important: Use only information from the document; add references to relevant sections.
            Generated content must be in user_language: {user_language}
            """

        rel_source = source.replace(self.settings.abs_project_path, '')
        return f"""
            <document project="{project_name}" file="{rel_source}" category="{title}" keywords="{keywords}">
            {file_content}
            </document>
            <user_instructions>
            {user_instructions}
            </user_instructions>
            <user_language>
            {user_language}
            </user_language>

            Given this document generate the wiki documentation based on user_instructions.
            Resulting document must be in markdown syntax without further decoration or enclosing marks.
            Do not include the raw file name/path as a heading in the document.
            Important: Use only information from the document; add references to relevant sections.
            Generated content must be in user_language: {user_language}
            """

    def _create_changeset_document(
        self, current_wiki_content: str, page_content: str, source: str
    ) -> str:
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

    def _build_dependency_section(self, deps: Dict, source: str) -> str:
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
        """
        # FIX: never use a mutable default argument
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
        """Ensure every category and file entry has correct path/slug metadata."""
        categories = self._get_all_categories(wiki_settings.get("categories", []))
        for category in categories:
            if not category.get("path"):
                category["path"] = slugify(category.get("title", "unknown"))
            for file in category.get("files", []):
                file["slug"] = self._get_file_wiki_name(file["path"])
                file["wiki_file"] = path_join(
                    self.wiki_path, category["path"], file["slug"]
                )

    def _read_file(self, file_path: str) -> str:
        return read_file(file_path, self.settings.abs_project_path)

    def _get_file_wiki_name(self, source: str) -> str:
        return slugify(source.replace(self.settings.abs_project_path, "")) + ".md"