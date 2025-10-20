import os
import shutil
import json
import logging
import datetime
import yaml

from pathlib import Path

from slugify import slugify
from enum import Enum
from typing import List, Dict, Tuple, Any, Optional, Any

from pydantic import BaseModel, Field

from concurrent.futures import ThreadPoolExecutor

from slugify import slugify
from pydantic import BaseModel
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

from codx.junior.utils.utils import write_file

from langchain.schema.document import Document

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
        self.wiki_home_path = os.path.join(self.wiki_path, "index.md")
        self.wiki_settings_path = os.path.join(self.settings.codx_path, "wiki_settings.json")

    def save_wiki_settings(self, wiki_settings: Any) -> None:
        """
        Serialize and save the wiki_settings object to a JSON file.

        Args:
            wiki_settings: The list of wiki settings to save.
        """
        self._fix_wiki_categories(wiki_settings)
        file_path = self._get_settings_path()
        wiki_settings["path"] = file_path
        write_file(file_path, json.dumps(wiki_settings, indent=2))
        logger.info(f"Wiki settings successfully saved to {file_path}")
        return self.load_wiki_settings()

    def load_wiki_settings(self, with_files=False) -> Any:
        """
        Read and deserialize the wiki_settings object from a JSON file.

        Returns:
            A dictionary of the deserialized wiki settings.
        """
        try:
            file_path = self._get_settings_path()
            with open(file_path, 'r') as file:
                wiki_settings = json.load(file)
            logger.info(f"Wiki settings successfully loaded from {file_path}")
            self._fix_wiki_categories(wiki_settings)
            return wiki_settings
        except Exception as e:
            logger.exception(f"Error loading wiki settings: {e}")
            return {
                "categories": [],
                "error": str(e) 
            }

    def create_wiki_tree(self):
        repository_files = self.loader.list_repository_files()
        ignore_patters = [
          MKDOCS_YAML_FILE_NAME,
          self.wiki_path
        ]
        def is_valid_file(file_path):
            for ignore in ignore_patters:
                if ignore in file_path:
                    return False
            return True
        repository_files = [f for f in repository_files if is_valid_file(f)]
        repository_files = "\n".join(sorted(repository_files))

        logger.info("Valid wiki files:\n%s", repository_files)
        
        wiki_settings = self.load_wiki_settings()
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")
        try:
            summary_prompt=f"""
            <project_info>
            { self.profile_manager.read_profile("project").content}
            </project_info>
            <project_files>
            { repository_files }
            </project_files>
            <wiki_settings>
            { json.dumps(wiki_settings, indent=2) }
            </wiki_settings>
            <user_instructions>
            { user_instructions }
            </user_instructions>
            <user_language>
            { user_language }
            </user_language>

            We are defining the project's documentation wiki to help new users understand and manage the project.
            Update the wiki structure based on the project's information that can assist users with onboarding, learning and (if apply) executing the project.
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
                * "name": A short user friendly name fo this file in { user_language } that gives seme hint about the file. Can contain 2 or 3 words, no more.
                * "path": File path
            Remove all WikiFiles that are not present in project_files.
            Make sure all project_files has been assigned to a category.
            Return updated wiki_settings JSON object.
            Generated content must be in user_language: { user_language }
            """
            messages = self._ai_chat(prompt=summary_prompt, clean=False)
            wiki_settings = next(extract_json_blocks(messages[-1].content))
            self._fix_wiki_categories(wiki_settings)
                        
            return wiki_settings

        except Exception as ex:
            logger.exception(f"Error creating wiki document: {ex}")
            return {
                **wiki_settings,
                "error": ex
            }    
        
    def update_category_home(self, documents: List[Document]):
        pass

    def create_wiki_document(self, source: str, update_wiki_conf: bool = True) -> Document:
        if not self.is_wiki_active:
            return None

        file_content = self._read_file(source)
        wiki_settings = self.load_wiki_settings()
        category = self._assign_category_to_file(source, wiki_settings)

        title = category['title']
        keywords = category['keywords']
        project_name = self.settings.project_name
        wiki_path = category["path"]
        wiki_file_path = self._determine_wiki_file_path(category, source)

        current_wiki_content = self._read_file(wiki_file_path) if os.path.isfile(wiki_file_path) else ""

        # Prepare the summary or update prompt based on the content
        summary_prompt = self._prepare_summary_prompt(current_wiki_content, category, file_content, project_name, source, title, keywords, wiki_settings)

        messages = self._ai_chat(prompt=summary_prompt)
        page_content = messages[-1].content

        logger.info("Creating wiki document at %s", wiki_file_path)
        os.makedirs(os.path.dirname(wiki_file_path), exist_ok=True)
        write_file(wiki_file_path, page_content)
        metadata = {
            "keywords": keywords,
            "category": title,
            "source": source,
            "language": "md",
            "wiki_path": wiki_path
        }

        # Update home
        if current_wiki_content:
            page_content = self._create_changeset_document(current_wiki_content, page_content, source)

        self.build_wiki_home(page_content)

        # Update wiki configuration
        if update_wiki_conf:
            self._update_wiki_conf()

        return Document(page_content, metadata=metadata)

    def build_wiki_category(self, path: str) -> None:
        """
        Build wiki documents for all files in the category matching the given path.

        Args:
            path: The path of the category for which to build wiki documents.
        """
        # Load current wiki settings
        wiki_settings = self.load_wiki_settings(with_files=True)
        
        # Find the category that matches the given path
        categories = self._get_all_categories(wiki_settings["categories"])
        category = next((c for c in categories if c.get("path") == path), None)
        
        if not category:
            logger.warning(f"No category found for path: {path}")
            return

        # Use ThreadPoolExecutor to parallelize the creation of wiki documents
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.create_wiki_document, file["path"], False) for file in category.get("files", [])]
            for future in futures:
                try:
                    future.result()
                    logger.exception("build_wiki_category %s done", path)
                except Exception as e:
                    logger.exception(f"Failed to create wiki document. Error: {e}")

        self._update_wiki_conf()

    def build_wiki_home(self, markdown_content: str) -> None:
        """
        Build or update the content of the home page of the wiki based on provided markdown content.
        The method will decide if the content is relevant for the front page and update accordingly.

        Args:
            markdown_content: The markdown content from a modified project file.
        """
        # Load current wiki settings
        wiki_settings = self.load_wiki_settings()
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")

        # Strip the "files" field from the categories
        categories_without_files = [
            {key: category[key] for key in category if key != "files"}
            for category in self._get_all_categories(wiki_settings["categories"])
        ]

        # Prepare the prompt for AI to decide on the relevance of the content
        relevance_prompt = f"""
        <markdown_content>
        {markdown_content}
        </markdown_content>
        <home_page_content>
        {self._read_file(self.wiki_home_path)}
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
        that should be included in the front page of the wiki. If relevant, update the home page content 
        with this information. Ensure that content is coherent and well-structured.
        Remember that the home page must show a high level overview don't deep down into details user will navigate the wiki for this.
        Generated content must be in user_language: {user_language}.
        Generate the final "home" document content without any extra comments. 
        """
        
        try:
            messages = self._ai_chat(prompt=relevance_prompt)
            updated_home_content = messages[-1].content
            
            # Write the updated content to the home page file
            write_file(self.wiki_home_path, updated_home_content)
            logger.info(f"Wiki home page successfully updated at {self.wiki_home_path}")
            
        except Exception as e:
            logger.exception(f"Error updating wiki home page: {e}")

    def compile_wiki(self):
        wiki_settings = self.load_wiki_settings()
        # Update mkdocs.yaml if mode is mkdocs
        if wiki_settings.get("mode") == "mkdocs":
            self._update_mkdocs()

    def rebuild_wiki(self):
        wiki_settings = self.load_wiki_settings()
        categories = self._get_all_categories(wiki_settings["categories"])
        
        for category in categories:
            self.build_wiki_category(category["path"])          

    def _update_wiki_conf(self):
        wiki_settings = self.load_wiki_settings()
        if wiki_settings.get("mode") == "mkdocs":
            self._update_mkdocs()

    def _update_mkdocs(self) -> None:
        """
        Use AI to update the mkdocs.yaml file, taking into account the current content
        of the mkdocs.yaml file and all the files and folders from the wiki_path.
        """
        mkdocs_file_path = Path(self.settings.project_path) / MKDOCS_YAML_FILE_NAME

        wiki_settings = self.load_wiki_settings()
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")
        
        # Read the existing mkdocs.yaml content
        current_mkdocs_content = {
          "nav": []
        }
        if mkdocs_file_path.exists():
            with open(mkdocs_file_path, 'r') as mkdocs_file:
                current_mkdocs_content = yaml.safe_load(mkdocs_file)

        # Gather all files and folders from the wiki_path
        wiki_files = []
        for root, dirs, files in os.walk(self.wiki_path):
            for file in files:
                if file != MKDOCS_YAML_FILE_NAME:
                    wiki_files.append(os.path.relpath(os.path.join(root, file), self.wiki_path))
        wiki_files.sort()
        wiki_files = '\n'.join(wiki_files)
        
        # Prepare the prompt for AI
        update_prompt = f"""
        <current_nav_section>
        {yaml.dump(current_mkdocs_content.get('nav', []), default_flow_style=False)}
        </current_nav_section>
        <wiki_files>
        {wiki_files}
        </wiki_files>
        <user_instructions>
        {user_instructions}
        </user_instructions>
        <user_language>
        {user_language}
        </user_language>

        Update the 'nav' section of the mkdocs.yaml content to reflect any changes in the wiki structure, 
        including new or removed files and folders. Ensure that the navigation structure 
        remains clear and logical.
        Generate only the updated 'nav' section as a YAML list.
        Generated content must be in user_language: {user_language}
        """

        try:
            messages = self._ai_chat(prompt=update_prompt)
            updated_nav_content = yaml.safe_load(messages[-1].content)

            # Replace the existing 'nav' section with the updated content
            current_mkdocs_content['nav'] = updated_nav_content['nav']

            # Write the updated content to the mkdocs.yaml file
            with open(mkdocs_file_path, 'w') as mkdocs_file:
                yaml.dump(current_mkdocs_content, mkdocs_file, default_flow_style=False)
            logger.info(f"mkdocs.yaml successfully updated at {mkdocs_file_path}")

        except Exception as e:
            logger.exception(f"Error updating mkdocs.yaml: {e}")

    def _find_category_for_file(self, file_path, all_categories):
        for category in all_categories:
            for file in category.get("files", []):
                if file.get("path", "") == file_path:
                    return category
        return None

    def _assign_category_to_file(self, source: str, wiki_settings: Dict[str, Any]) -> Dict[str, Any]:
        all_categories = self._get_all_categories(wiki_settings["categories"])
        category = self._find_category_for_file(file_path=source, all_categories=all_categories)
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")

        if not category:
            categories_and_keywords = [{
                "path": category["path"],
                "title": category["title"],
                "keywords": category["keywords"]
            } for category in all_categories]

            summary_prompt = f"""
            <document>
            {self._read_file(source)}
            </document>
            <categories>
            {categories_and_keywords}
            </categories>
            <user_instructions>
            {user_instructions}
            </user_instructions>
            <user_language>
            {user_language}
            </user_language>

            Analyze this document and match the best category from the list of categories for this document.
            Only categories from the list are valid response and always return a .
            Return a JSON dictionary with the "path" field category
            Generated content must be in user_language: {user_language}
            """
            messages = self._ai_chat(prompt=summary_prompt, clean=False)
            metadata = next(extract_json_blocks(messages[-1].content))
            wiki_path = metadata["path"]
            category = next(filter(lambda x: x["path"] == wiki_path, all_categories))

            # Update category
            if "files" not in category:
                category["files"] = []
            if source not in category["files"]:
                category["files"].append({"path": source})
                self.save_wiki_settings(wiki_settings)

        return category

    def _determine_wiki_file_path(self, category: Dict[str, Any], source: str) -> str:
        if category.get("single_file", False):
            return path_join(self.wiki_path, f"{category['path']}.md")
        else:
            return path_join(self.wiki_path, category["path"], self._get_file_wiki_name(source))

    def _prepare_summary_prompt(self, current_wiki_content: str, category: Dict[str, Any], file_content: str, project_name: str, source: str, title: str, keywords: List[str], wiki_settings: Dict[str, Any]) -> str:
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
            Important: Use only information from the document don't make it from other sources and add references to the document sections.
            Generated content must be in user_language: {user_language}
            """
        else:
            source = source.replace(self.settings.project_path, '')
            return f"""
            <document project="{project_name}" file="{source}" category="{title}" keywords="{keywords}">
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
            Do not include the name of the file in the document.
            Important: Use only information from the document don't make it from other sources and add references to the document sections.
            Generated content must be in user_language: {user_language}
            """

    def _create_changeset_document(self, current_wiki_content: str, page_content: str, source: str) -> str:
        prompt = f"""
        <old_wiki>
        {current_wiki_content}
        </old_wiki>
        <new_wiki>
        {page_content}
        </new_wiki>

        Explain the changes done to the wiki page for {source}.
        """
        changes = self._ai_chat(prompt=prompt)[-1].content
        return f"""
        <wiki_changes source="{source}">
        {changes}
        </wiki_changes>
        """

    def _get_settings_path(self):
        return self.wiki_settings_path

    def _get_all_categories(
        self, 
        categories: List[Dict[str, Any]], 
        flattened_list: List[Dict[str, Any]] = [], 
        parent: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Flatten the hierarchical list of categories into a single list while preserving hierarchical path info.

        Args:
            categories: A list of category dictionaries to process.
            flattened_list: A list to collect all categories, starting as empty.
            parent: The parent category dictionary for hierarchical reference.

        Returns:
            A list of all categories with updated path and id info.
        """
        parent_path = slugify(parent.get("path", "")) if parent else ""

        for category in categories:
            _id = slugify(category["title"])
            category["id"] = _id
            category["path"] = f'{parent_path}/{_id}' if parent else _id
            flattened_list.append(category)
            
            children = category.get("children", [])
            if children:
                self._get_all_categories(children, flattened_list, category)

        return flattened_list

    def _fix_wiki_categories(self, wiki_settings):
        categories = self._get_all_categories(wiki_settings["categories"])
        for category in categories:
            if not category.get("path"):
                category["path"] = slugify(category["title"])
            for file in category.get("files", []):
                file["slug"] = self._get_file_wiki_name(file["path"])
                file["wiki_file"] = path_join(self.wiki_path, category["path"], file["slug"])

    def _read_file(self, file_path):
        return read_file(file_path, self.settings.project_path)

    def _get_file_wiki_name(self, source):
        return slugify(source.replace(self.settings.project_path, "")) + ".md"

    def _get_ai(self) -> AI:
        """Create and return an AI engine instance for processing."""
        return AI(settings=self.settings, llm_model=self.settings.get_wiki_model(), user=CodxUser(username=__name__))

    def _ai_chat(self, prompt, tags="", clean=True):
        tags = f"{tags},wiki" if tags else "wiki"
        headers = {
            "tags": tags
        }
        messages = self._get_ai().chat(prompt=prompt, headers=headers)
        content = messages[-1].content.strip()
        if clean and content.startswith("```"):
            content = "\n".join(content.split("\n")[1:-1])
            messages[-1].content = content
        return messages
