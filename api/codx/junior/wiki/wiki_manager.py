import os
import shutil
import json
import logging
import datetime
from enum import Enum
from typing import List, Dict, Tuple, Any, Optional

from pydantic import BaseModel, Field

from slugify import slugify
from pydantic import BaseModel
from aiofiles import open as aio_open

from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession
from codx.junior.utils.utils import exec_command, remove_starting_block
from .model import *
from ..ai import AI
from ..events.event_manager import EventManager
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.profiles.profile_manager import ProfileManager

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
        self.knowledge = Knowledge(settings=settings)
        self.profile_manager = ProfileManager(settings=settings)
        self.wiki_path: str = settings.get_project_wiki_path()
        
    def build_categories(self):
        """We'll create a summary of all the categories defined in the knowledge"""
        # Get all categories
        self.knowledge.get_categories()

        # Read current categories file having a list of WikiCategory

        # Find categries with new files
            # Create new category summary

        # Remove old categories

        # Save categories file 
       

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

