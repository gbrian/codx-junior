import os
import shutil
import json
import logging
import datetime
from slugify import slugify
from enum import Enum
from typing import List, Dict, Tuple, Any, Optional, Any

from pydantic import BaseModel, Field

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

from langchain.schema.document import Document

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND_MESSAGE = "No matching category found for file: %s"
WIKI_FILE_PATH_TEMPLATE = "/{slug}.md"
HOME_PAGE_UPDATE_EVENT = "Build home page"
WIKI_TREE_FILE_NAME = 'wiki_tree.json'

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
    using VitePress. It initializes, builds, and updates a wiki based on the project's
    structure and changes in files.
    """
    
    def __init__(self, settings: CODXJuniorSettings) -> None:
        self.settings: CODXJuniorSettings = settings
        self.event_manager = EventManager(codx_path=settings.codx_path)
        self.profile_manager = ProfileManager(settings=settings)
        self.wiki_path: str = settings.get_project_wiki_path()
        self.db = KnowledgeDB(settings=settings)
        self.loader = KnowledgeLoader(settings=settings)

    def save_wiki_settings(self, wiki_settings: Any) -> None:
        """
        Serialize and save the wiki_settings object to a JSON file.

        Args:
            wiki_settings: The list of wiki settings to save.
        """
        self._fix_wiki_categories(wiki_settings)
        file_path = self._get_settings_path()
        wiki_settings["path"] = file_path
        with open(file_path, 'w') as file:
            json.dump(wiki_settings, file, indent=2)
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
            if with_files:
                self._load_category_files(wiki_settings)
            return wiki_settings
        except Exception as e:
            logger.exception(f"Error loading wiki settings: {e}")
            return {
              "categories": [] 
            }

    def create_wiki_tree(self):
        repository_files = self.loader.list_repository_files()
        repository_files = "\n".join(sorted(repository_files))
        
        wiki_settings = self.load_wiki_settings()
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

          We are defining the project's documentation wiki to help new users unnderstand and manage the project.
          Update the wiki structure based on the project's information that can assist users with onboarding, learning and (if apply) executing the project.
          Detect which kind of project is and choose and structure it wisely into categories and sub categories.
          Update wiki tree definition from given updated information aboute the project and its folders.
          A wiki tree will split the project into 6 top level categories for the main project's sections/functionalities.
          Top level categories can have "children" categories.
          A catgeory entry is defined in a json with fields:  
            * "title": Unique category title. Can't be repeated in by any other category or subcategory.
            * "description": A 8 lines category descrption
            * "keywords": List of keyword to check if a file belongs to the category
            * "children": An array of cetgory entries
            * "files": (Mandatory) The list of files matching this category. Remove the category if you can't find any matching file.
          Return updated wiki_settings JSON object
          """
          messages = self._get_ai().chat(prompt=summary_prompt)
          wiki_settings = next(extract_json_blocks(messages[-1].content))
          self._fix_wiki_categories(wiki_settings)
        
          return wiki_settings

        except Exception as ex:
          logger.exception(f"Error creating wiki document: {ex}")
          return {
            **wiki_settings,
            "error": ex
          }    
        
    def create_wiki_document(self, source):
        file_content = self._read_file(source)
        wiki_settings = self.load_wiki_settings()
        categories = self._get_all_categories(wiki_settings["categories"])
        # Check if we have already assigned a caregory 
        category = next((c for c in categories if source in c["files"]), None)

        if not category:
            categories_and_keywords = [{
              "path": category["path"], 
              "title": category["title"],
              "keywords": category["keywords"]
            } for category in categories]

            summary_prompt=f"""
            <document>
            { file_content }
            </document>
            <categories>
            { categories_and_keywords }
            </categories>

            Analyze this document and match the best category from the list of categories for this document.
            Only categories from the list are valid response and always return a .
            Return a JSON dictionary with the "path" field category
            """
            messages = self._get_ai().chat(prompt=summary_prompt)
            metadata = next(extract_json_blocks(messages[-1].content))
            category = next(filter(lambda x: x["path"] == wiki_path, categories))
            # Update category
            if "files" not in category:
                category["files"] = []
            if source not in category["files"]:
                category["files"].append(source)
                self.save_wiki_settings(wiki_settings)

        title = category['title']
        keywords = category['keywords']
        project_name = self.settings.project_name
        wiki_path = category["path"]
            
        summary_prompt=f"""
        <document project="{project_name}" file="{source}" category="{title}" keywords="{keywords}">
        { file_content }
        </document>

        Given this document generate a full detailed, 
        fine grained wiki with examples and tips documentation page 
        including all the parts of the document.
        Resulting document must be in mardown syntax without further decoration or enclosing marks.
        Do not include the name of the file in the document.
        """
        messages = self._get_ai().chat(prompt=summary_prompt)
        page_content = messages[-1].content
        
        wiki_file_path = path_join(self.wiki_path, wiki_path, self._get_file_wiki_name(source))
        os.makedirs(os.path.dirname(wiki_file_path), exist_ok=True)
        with open(wiki_file_path, 'w') as f:
            f.write(page_content)

    def _get_settings_path(self):
        return os.path.join(self.wiki_path, "wiki_settings.json")

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

    def _load_category_files(self, wiki_settings):
        """
        List all files for each category based on their path and update the 'files' property.

        Args:
            wiki_settings: The dictionary containing the wiki settings with categories.
        """
        base_path = self.wiki_path  # The base path where the files are located

        categories = self._get_all_categories(wiki_settings["categories"])
        for category in categories:
            category_path = os.path.join(base_path, category["path"])

            if os.path.exists(category_path):
                # List all files under the category path
                root, _, files = next(os.walk(category_path))
                set_path = lambda f: os.path.join(self.wiki_path, category_path, f)
                category["files"] = [set_path(f) for f in files]
            else:
                category["files"] = []      
    
    def _search_documents(self, search_filter):
        return self.db.raw_search(search_filter)

    def _read_file(self, file_path):
        return read_file(file_path, self.settings.project_path)

    def _get_file_wiki_name(self, source):
        return slugify(source.replace(self.settings.project_path, "")) + ".md"

    def _get_ai(self) -> AI:
        """Create and return an AI engine instance for processing."""
        return AI(settings=self.settings, llm_model=self.settings.get_wiki_model())

    def _generate_home_page_prompt(self, wiki_profile: str, 
                                   config: WikiConfig, 
                                   sources: str, 
                                   home_content: str) -> str:
        """Generate a prompt for updating the wiki's home page."""
        return (
            f"{wiki_profile}\n"
            "Update wiki home page based on the configuration.\n"
            "Update features with the 3 most important categories.\n"
            "\nProject configuration:\n"
            f"```json\n{config.model_dump_json()}\n```\n"
            "\nProject's files:\n"
            "```bash\n"
            f"{sources}\n```\n"
            "\nHome page:\n"
            "```md\n"
            f"{home_content}\n```\n"
            "Respect home page format:\n"
            " * Starts with a line \"---\"\n"
            " * Ends with a line \"---\"\n"
            " * Don't add content before the starting \"---\" or ending \"---\"\n"
            " * Update project info\n"
            " * Update the features\n"
            " * Keep actions as it is\n"
        )

