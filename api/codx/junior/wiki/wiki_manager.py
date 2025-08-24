import os
import shutil
import json
import logging
import datetime
from slugify import slugify
from enum import Enum
from typing import List, Dict, Tuple, Any, Optional

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

from langchain.schema.document import Document

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND_MESSAGE = "No matching category found for file: %s"
WIKI_FILE_PATH_TEMPLATE = "/{slug}.md"
HOME_PAGE_UPDATE_EVENT = "Build home page"
WIKI_TREE_FILE_NAME = 'wiki_tree.json'


class WikiCategory(BaseModel):
    """Defines a wiki category"""
    category: str = Field(default=None)
    summary: str = Field(default=None)
    files: List[str] = Field(default=[])

class WikiCategories(BaseModel):
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

    def build_home_page(self):
        project_name = self.settings.project_name
        categories = self.db.get_all_categoties()
        
        def build_category_section(category):
            files = self._search_documents(f"category == '{category}'")
            return f"""### [{category}]({category})
            {len(files)} files 
            """
        def build_categories():
            categorie_section = [build_category_section(category) for category \
                                  in sorted(categories)]
            return "\n".join(categorie_section)
        page_content = f"""
        # {project_name}
        
        Welcome to the wiki!

        ## Categories:
        {build_categories()}
        """

        wiki_file_path = path_join(self.wiki_path, "home.md")
        with open(wiki_file_path, 'w') as f:
            f.write(page_content)

    def create_wiki_document(self, source, categories):
        metadata = self._get_wiki_file_metadata(source)
        file_content = self._read_file(source)
        wiki_file_path = path_join(self.wiki_path, self._get_file_wiki_name(source))
        try:
          summary_prompt=f"""
          <document>
          { file_content }
          </document>
          <categories>
          { ",".join(categories)}
          </categories>

          Analyze this document and return a JSON object with this information:
          * "summary": A 10 lines summarization of the content, focusing on important and business related concept.
          * "keywords": A array of keywords. Use "-" insteas spaces for keywords.
          * "category": Choose a category for this document or define a new one if content doesn't fit on any of the exiting ones
          """
          messages = self._get_ai().chat(prompt=summary_prompt)
          response = next(extract_json_blocks(messages[-1].content))
          metadata = {
            **metadata,
            **response
          }
        except Exception as ex:
          logger.exception(f"Error creating wiki document {source}: {ex}")
          metadata["error"] = str(ex)

        category = metadata.get('category', "")
        keywords = ",".join(metadata.get('keywords', []))
        
        project_name = self.settings.project_name
        try:
          summary_prompt=f"""
          <document project="{project_name}" file="{source}" category="{category}" keywords="{keywords}">
          { file_content }
          </document>

          Given this document generate a full detailed, 
          fine grained wiki with examples and tips documentation page 
          including all the parts of the document.
          Resulting document must be in mardown syntax without further decoration or enclosing marks.
          Do not include the name of the file in the document.
          """
          messages = self._get_ai().chat(prompt=summary_prompt)
          metadata["keywords"].append("wiki_page")
          page_content = messages[-1].content
          with open(wiki_file_path, 'w') as f:
              f.write(page_content)
        except Exception as ex:
          logger.exception(f"Error creating wiki document {source}: {ex}")
          
    def _search_documents(self, search_filter):
        return self.db.raw_search(search_filter)

    def _read_file(self, file_path):
        return read_file(file_path, self.settings.project_path)

    def _get_file_wiki_name(self, source):
        return slugify(source.replace(self.settings.project_path, "")) + ".md"

    def _get_wiki_file_metadata(self, source):
        return {
          "source": source,
          "last_update": datetime.datetime.now().isoformat(),
          "language": "md",
          "splitter": "wiki",
          "keywords": []
        }

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

