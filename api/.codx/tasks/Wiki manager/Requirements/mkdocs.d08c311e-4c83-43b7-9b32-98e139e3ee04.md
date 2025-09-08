# [[{"id": "d08c311e-4c83-43b7-9b32-98e139e3ee04", "doc_id": null, "project_id": null, "parent_id": null, "message_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/wiki/wiki_manager.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "mkdocs", "description": "The conversation focused on updating the `WikiManager` class to enhance the `_update_mkdocs` method. The goal was to generate a tree representation of the wiki directory structure and incorporate it into the `mkdocs.yaml` file. The method involves creating a nested YAML structure for the `nav` section, which is then passed to an AI to generate user-friendly names. The AI-generated `nav` content updates the existing `nav` section in the `mkdocs.yaml` file. This update aims to improve the navigation layout of the wiki for easier user access.", "created_at": "2025-09-06 14:29:38.790111", "updated_at": "2025-09-08T08:11:42.600867", "mode": "task", "kanban_id": "", "column_id": "", "board": "Wiki manager", "column": "Requirements", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Wiki manager/Requirements/mkdocs.d08c311e-4c83-43b7-9b32-98e139e3ee04.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": [], "chat_links": [], "pr_view": {}}]]
## [[{"doc_id": "3b51b38f-036a-4933-adc9-0da2964f7630", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-06 14:29:38.787671", "updated_at": "2025-09-06 14:29:38.787699", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
wiki could be of type "mkdocs" check the settings wiki_settings.mode === 'mkdocs'.


For the mkdocs mode we must keep the "mkdocs.yaml" file updated after new file is created.


For this add a new method _update_mkdocs that will list all files in the wiki_path and update the yaml definition.


Use the categories and the files names to give friendly names.
Method will update existing file or create new one


Example of mkdocs:
```yaml
site_name: der-viewer-api
nav:
  - Home: index.md


plugins:
  - techdocs-core
```
```
## [[{"doc_id": "f4f33054-c892-41f8-a158-66c6c3b94e5e", "role": "assistant", "task_item": "analysis", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-06 14:29:38.787671", "updated_at": "2025-09-06 14:29:38.787699", "images": [], "files": [], "meta_data": {"time_taken": 128.06156468391418, "first_chunk_time_taken": 0.00021457672119140625, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To accommodate the user's comments, we need to implement an additional method in the `WikiManager` class to update or create the `mkdocs.yaml` file whenever a new file is created in the `mkdocs` mode. Below is the updated version of the `wiki_manager.py` file with the new `_update_mkdocs` method implemented:

```python /shared/codx-junior/api/codx/junior/wiki/wiki_manager.py
import os
import shutil
import json
import logging
import datetime
import yaml  # Import yaml for handling mkdocs.yaml
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

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND_MESSAGE = "No matching category found for file: %s"
WIKI_FILE_PATH_TEMPLATE = "/{slug}.md"
HOME_PAGE_UPDATE_EVENT = "Build home page"
WIKI_TREE_FILE_NAME = 'wiki_tree.json'
MKDOCS_YAML_FILE_NAME = 'mkdocs.yaml'  # Define mkdocs.yaml file name

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
        self.is_wiki_active = True if self.wiki_path else False
        self.wiki_home_path = os.path.join(self.wiki_path, "index.md")

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
        repository_files = [f for f in repository_files if not f.startswith(self.wiki_path)]
        repository_files = "\n".join(sorted(repository_files))
        
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
                * "files": (Mandatory) The list of files matching this category. Remove the category if you can't find any matching file.
            Return updated wiki_settings JSON object
            Generated content must be in user_language: { user_language }
            """
            messages = self._ai_chat(prompt=summary_prompt)
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

    def create_wiki_document(self, source: str) -> Document:
        if not self.is_wiki_active:
            return None
            
        file_content = self._read_file(source)
        wiki_settings = self.load_wiki_settings()
        categories = self._get_all_categories(wiki_settings["categories"])
        # Check if we have already assigned a category 
        category = next((c for c in categories if source in c.get("files", [])), None)
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")
        
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
            <user_instructions>
            { user_instructions }
            </user_instructions>
            <user_language>
            { user_language }
            </user_language>

            Analyze this document and match the best category from the list of categories for this document.
            Only categories from the list are valid response and always return a .
            Return a JSON dictionary with the "path" field category
            Generated content must be in user_language: { user_language }
            """
            messages = self._ai_chat(prompt=summary_prompt)
            metadata = next(extract_json_blocks(messages[-1].content))
            wiki_path = metadata["path"]
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
        <user_instructions>
        { user_instructions }
        </user_instructions>
        <user_language>
        { user_language }
        </user_language>

        Given this document generate a full detailed, fine-grained wiki documentation with examples and tips.
        Resulting document must be in markdown syntax without further decoration or enclosing marks.
        Do not include the name of the file in the document.
        Important: Use only information from the document don't make it from other sources and add references to the document sections.
        Generated content must be in user_language: { user_language }
        """
        messages = self._ai_chat(prompt=summary_prompt)
        page_content = messages[-1].content
        
        wiki_file_path = path_join(self.wiki_path, wiki_path, self._get_file_wiki_name(source))
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
        self.build_wiki_home(page_content)

        # Update mkdocs.yaml if mode is mkdocs
        if wiki_settings.get("mode") == "mkdocs":
            self._update_mkdocs()

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
            futures = [executor.submit(self.create_wiki_document, file) for file in category.get("files", [])]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(f"Failed to create wiki document. Error: {e}")

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
        Generated content must be in user_language: {user_language}
        """
        
        try:
            messages = self._ai_chat(prompt=relevance_prompt)
            updated_home_content = messages[-1].content
            
            # Write the updated content to the home page file
            write_file(self.wiki_home_path, updated_home_content)
            logger.info(f"Wiki home page successfully updated at {self.wiki_home_path}")
            
        except Exception as e:
            logger.exception(f"Error updating wiki home page: {e}")

    def _update_mkdocs(self) -> None:
        """
        Update or create the mkdocs.yaml file to reflect the current wiki structure.
        """
        site_name = self.settings.project_name
        nav = []
        
        # Load current wiki settings
        wiki_settings = self.load_wiki_settings(with_files=True)
        categories = self._get_all_categories(wiki_settings["categories"])

        # Build navigation structure
        for category in categories:
            category_nav = {category['title']: [os.path.relpath(file, self.wiki_path) for file in category.get("wiki_files", [])]}
            nav.append(category_nav)

        mkdocs_content = {
            "site_name": site_name,
            "nav": nav,
            "plugins": ["techdocs-core"]
        }

        mkdocs_file_path = os.path.join(self.wiki_path, MKDOCS_YAML_FILE_NAME)
        with open(mkdocs_file_path, 'w') as mkdocs_file:
            yaml.dump(mkdocs_content, mkdocs_file, default_flow_style=False)
        logger.info(f"mkdocs.yaml successfully updated at {mkdocs_file_path}")

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
                category["wiki_files"] = [set_path(f) for f in files]
            else:
                category["wiki_files"] = []      

    def _read_file(self, file_path):
        return read_file(file_path, self.settings.project_path)

    def _get_file_wiki_name(self, source):
        return slugify(source.replace(self.settings.project_path, "")) + ".wiki_file"

    def _get_ai(self) -> AI:
        """Create and return an AI engine instance for processing."""
        return AI(settings=self.settings, llm_model=self.settings.get_wiki_model())

    def _ai_chat(self, prompt, tags=""):
        tags = f"{tags},wiki" if tags else "wiki"
        headers = {
            "tags": tags
        }
        messages = self._get_ai().chat(prompt=prompt, headers=headers)
        prompt = "Review last message and return the wiki document without any extra comment or surrounding decorators, just the wiki markdown"
        return self._get_ai().chat(messages=[messages[-1]], headers=headers)
```

### Explanation:
1. **Import YAML Library**: Added the `yaml` library to handle reading and writing YAML files for `mkdocs.yaml`.
   
2. **`_update_mkdocs` Method**: A new method `_update_mkdocs` has been created to update or create the `mkdocs.yaml` file. It constructs a navigation structure based on the available categories and files, then writes this structure to the `mkdocs.yaml` file.

3. **Integration with `create_wiki_document`**: After creating a new wiki document, the code checks if the current mode is `mkdocs` and calls `_update_mkdocs` to ensure the `mkdocs.yaml` is up-to-date.

This implementation ensures that the `mkdocs.yaml` file is kept current with the project's wiki structure whenever a new document is added.
## [[{"doc_id": "727ffc56-909c-4c4a-af85-1d5a24aaf559", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-06 17:42:44.346171", "updated_at": "2025-09-06 17:42:44.346202", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Best strategy to generate mkdocs will be to list all files and directories under wiki_path and convert the files tree into mkdocs structure.


Create a MkDocs class copying DisplayablePath class to generate the mkdocs structure and dump into yaml
## [[{"doc_id": "98f13059-3ca7-4c4a-990a-4145c8dabb3b", "role": "assistant", "task_item": "analysis", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-06 17:42:44.346171", "updated_at": "2025-09-06 17:42:44.346202", "images": [], "files": [], "meta_data": {"time_taken": 78.63896155357361, "first_chunk_time_taken": 0.00020503997802734375, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
```python /shared/codx-junior/api/codx/junior/wiki/wiki_manager.py
import os
import shutil
import json
import logging
import datetime
import yaml  # Import yaml for handling mkdocs.yaml
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

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND_MESSAGE = "No matching category found for file: %s"
WIKI_FILE_PATH_TEMPLATE = "/{slug}.md"
HOME_PAGE_UPDATE_EVENT = "Build home page"
WIKI_TREE_FILE_NAME = 'wiki_tree.json'
MKDOCS_YAML_FILE_NAME = 'mkdocs.yaml'  # Define mkdocs.yaml file name

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

class DisplayablePath:
    display_filename_prefix_middle = "├── "
    display_filename_prefix_last = "└── "
    display_parent_prefix_middle = "    "
    display_parent_prefix_last = "│   "

    def __init__(self, path: Path, parent=None, is_last=False):
        self.path = Path(str(path))
        self.parent = parent
        self.is_last = is_last
        self.depth = self.parent.depth + 1 if self.parent else 0

    @property
    def display_name(self):
        return self.path.name + '/' if self.path.is_dir() else self.path.name

    @classmethod
    def make_tree(cls, root: Union[str, Path], parent=None, is_last=False, criteria=None):
        root = Path(str(root))
        criteria = criteria or cls._default_criteria

        displayable_root = cls(root, parent, is_last)
        yield displayable_root

        children = sorted(
            list(path for path in root.iterdir() if criteria(path)),
            key=lambda s: str(s).lower(),
        )
        count = 1
        for path in children:
            is_last = count == len(children)
            if path.is_dir():
                yield from cls.make_tree(
                    path, parent=displayable_root, is_last=is_last, criteria=criteria
                )
            count += 1

    @classmethod
    def _default_criteria(cls, path: Path) -> bool:
        return path.is_dir()

    @classmethod
    def make_tree_from_folders(cls, folders: List[Path], parent=None, is_last=False):
        if not folders:
            return

        # Sort folders to ensure consistent order
        folders = sorted(folders, key=lambda s: str(s).lower())

        # Create a dictionary to hold the folder structure
        folder_dict = {}
        for folder in folders:
            parts = folder.parts
            current_level = folder_dict
            for part in parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]

        # Helper function to recursively create DisplayablePath objects
        def create_displayable_paths(current_level, parent, is_last):
            items = sorted(current_level.items(), key=lambda s: str(s[0]).lower())
            count = 1
            for name, sub_level in items:
                path = Path(name)
                displayable_path = cls(path, parent, is_last=(count == len(items)))
                yield displayable_path
                if sub_level:
                    yield from create_displayable_paths(sub_level, displayable_path, is_last)
                count += 1

        # Start creating DisplayablePath objects from the root level
        yield from create_displayable_paths(folder_dict, parent, is_last)

    def displayable(self) -> str:
        if self.parent is None:
            return self.display_name

        _filename_prefix = (
            self.display_filename_prefix_last
            if self.is_last
            else self.display_filename_prefix_middle
        )

        parts = ["{!s} {!s}".format(_filename_prefix, self.display_name)]

        parent = self.parent
        while parent and parent.parent is not None:
            parts.append(
                self.display_parent_prefix_middle
                if parent.is_last
                else self.display_parent_prefix_last
            )
            parent = parent.parent

        return "".join(reversed(parts))

class MkDocs:
    def __init__(self, wiki_path):
        self.wiki_path = wiki_path

    def generate_structure(self) -> List[Dict[str, Any]]:
        tree_generator = DisplayablePath.make_tree(self.wiki_path)
        nav = []
        for node in tree_generator:
            if node.path.is_file():
                relative_path = os.path.relpath(node.path, self.wiki_path)
                nav.append({node.path.stem: relative_path})
            else:
                nav.append({node.path.name: []})
        return nav

    def dump_to_yaml(self, site_name: str):
        mkdocs_content = {
            "site_name": site_name,
            "nav": self.generate_structure(),
            "plugins": ["techdocs-core"]
        }
        mkdocs_file_path = os.path.join(self.wiki_path, MKDOCS_YAML_FILE_NAME)
        with open(mkdocs_file_path, 'w') as mkdocs_file:
            yaml.dump(mkdocs_content, mkdocs_file, default_flow_style=False)
        logger.info(f"mkdocs.yaml successfully updated at {mkdocs_file_path}")

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
        self.is_wiki_active = True if self.wiki_path else False
        self.wiki_home_path = os.path.join(self.wiki_path, "index.md")

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
        repository_files = [f for f in repository_files if not f.startswith(self.wiki_path)]
        repository_files = "\n".join(sorted(repository_files))
        
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
                * "files": (Mandatory) The list of files matching this category. Remove the category if you can't find any matching file.
            Return updated wiki_settings JSON object
            Generated content must be in user_language: { user_language }
            """
            messages = self._ai_chat(prompt=summary_prompt)
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

    def create_wiki_document(self, source: str) -> Document:
        if not self.is_wiki_active:
            return None
            
        file_content = self._read_file(source)
        wiki_settings = self.load_wiki_settings()
        categories = self._get_all_categories(wiki_settings["categories"])
        # Check if we have already assigned a category 
        category = next((c for c in categories if source in c.get("files", [])), None)
        user_language = wiki_settings.get("language", "English")
        user_instructions = wiki_settings.get("prompt", "")
        
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
            <user_instructions>
            { user_instructions }
            </user_instructions>
            <user_language>
            { user_language }
            </user_language>

            Analyze this document and match the best category from the list of categories for this document.
            Only categories from the list are valid response and always return a .
            Return a JSON dictionary with the "path" field category
            Generated content must be in user_language: { user_language }
            """
            messages = self._ai_chat(prompt=summary_prompt)
            metadata = next(extract_json_blocks(messages[-1].content))
            wiki_path = metadata["path"]
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
        <user_instructions>
        { user_instructions }
        </user_instructions>
        <user_language>
        { user_language }
        </user_language>

        Given this document generate a full detailed, fine-grained wiki documentation with examples and tips.
        Resulting document must be in markdown syntax without further decoration or enclosing marks.
        Do not include the name of the file in the document.
        Important: Use only information from the document don't make it from other sources and add references to the document sections.
        Generated content must be in user_language: { user_language }
        """
        messages = self._ai_chat(prompt=summary_prompt)
        page_content = messages[-1].content
        
        wiki_file_path = path_join(self.wiki_path, wiki_path, self._get_file_wiki_name(source))
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
        self.build_wiki_home(page_content)

        # Update mkdocs.yaml if mode is mkdocs
        if wiki_settings.get("mode") == "mkdocs":
            mkdocs = MkDocs(self.wiki_path)
            mkdocs.dump_to_yaml(self.settings.project_name)

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
            futures = [executor.submit(self.create_wiki_document, file) for file in category.get("files", [])]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(f"Failed to create wiki document. Error: {e}")

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
        Generated content must be in user_language: {user_language}
        """
        
        try:
            messages = self._ai_chat(prompt=relevance_prompt)
            updated_home_content = messages[-1].content
            
            # Write the updated content to the home page file
            write_file(self.wiki_home_path, updated_home_content)
            logger.info(f"Wiki home page successfully updated at {self.wiki_home_path}")
            
        except Exception as e:
            logger.exception(f"Error updating wiki home page: {e}")

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
                category["wiki_files"] = [set_path(f) for f in files]
            else:
                category["wiki_files"] = []      

    def _read_file(self, file_path):
        return read_file(file_path, self.settings.project_path)

    def _get_file_wiki_name(self, source):
        return slugify(source.replace(self.settings.project_path, "")) + ".wiki_file"

    def _get_ai(self) -> AI:
        """Create and return an AI engine instance for processing."""
        return AI(settings=self.settings, llm_model=self.settings.get_wiki_model())

    def _ai_chat(self, prompt, tags=""):
        tags = f"{tags},wiki" if tags else "wiki"
        headers = {
            "tags": tags
        }
        messages = self._get_ai().chat(prompt=prompt, headers=headers)
        prompt = "Review last message and return the wiki document without any extra comment or surrounding decorators, just the wiki markdown"
        return self._get_ai().chat(messages=[messages[-1]], headers=headers)
```

### Explanation:
1. **MkDocs Class**: A new `MkDocs` class is introduced, utilizing a modified version of the `DisplayablePath` class to generate the mkdocs structure and dump it into a YAML file.
   
2. **Integration with `create_wiki_document`**: The `MkDocs` class is used in the `create_wiki_document` method to update the `mkdocs.yaml` file by calling the `dump_to_yaml` method after creating a new wiki document.

3. **DisplayablePath Class**: This class is copied and used for generating the directory structure, supporting the creation of a structured navigation for `mkdocs.yaml`.
## [[{"doc_id": "64dc4bb4-6c11-4cb2-ac2d-e6a5b38ba6eb", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-07 06:57:55.405563", "updated_at": "2025-09-07 06:57:55.405594", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
use ai to update mkdocs, take current content from mkdocs.yaml file and all the files and folders from the wiki_path.
Ask AI to update the existing mkdocs.yaml or generate new one.
## [[{"doc_id": "46d8bdbb-177f-4cee-b4a9-d18cc41caf67", "role": "assistant", "task_item": "analysis", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-07 06:57:55.405563", "updated_at": "2025-09-07 06:57:55.405594", "images": [], "files": [], "meta_data": {"time_taken": 21.29869055747986, "first_chunk_time_taken": 7.867813110351562e-05, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To implement the required functionality of using AI to update the `mkdocs.yaml` file, taking into account the current content of the `mkdocs.yaml` file and all the files and folders from the `wiki_path`, we can create a new method in the `WikiManager` class. This method will read the existing `mkdocs.yaml` file, gather the current wiki files, and then generate an updated `mkdocs.yaml` content using AI. Here's how you can implement this:

```python
import yaml
from pathlib import Path

def update_mkdocs_with_ai(self) -> None:
    """
    Use AI to update the mkdocs.yaml file, taking into account the current content
    of the mkdocs.yaml file and all the files and folders from the wiki_path.
    """
    mkdocs_file_path = Path(self.wiki_path) / MKDOCS_YAML_FILE_NAME

    # Read the existing mkdocs.yaml content
    current_mkdocs_content = {}
    if mkdocs_file_path.exists():
        with open(mkdocs_file_path, 'r') as mkdocs_file:
            current_mkdocs_content = yaml.safe_load(mkdocs_file)

    # Gather all files and folders from the wiki_path
    wiki_files = []
    for root, dirs, files in os.walk(self.wiki_path):
        for file in files:
            if file != MKDOCS_YAML_FILE_NAME:
                wiki_files.append(os.path.relpath(os.path.join(root, file), self.wiki_path))

    # Prepare the prompt for AI
    update_prompt = f"""
    <current_mkdocs_content>
    {yaml.dump(current_mkdocs_content, default_flow_style=False)}
    </current_mkdocs_content>
    <wiki_files>
    {yaml.dump(wiki_files, default_flow_style=False)}
    </wiki_files>

    Update the mkdocs.yaml content to reflect any changes in the wiki structure, 
    including new or removed files and folders. Ensure that the navigation structure 
    remains clear and logical.
    """

    try:
        messages = self._ai_chat(prompt=update_prompt)
        updated_mkdocs_content = messages[-1].content

        # Write the updated content to the mkdocs.yaml file
        with open(mkdocs_file_path, 'w') as mkdocs_file:
            mkdocs_file.write(updated_mkdocs_content)
        logger.info(f"mkdocs.yaml successfully updated at {mkdocs_file_path}")

    except Exception as e:
        logger.exception(f"Error updating mkdocs.yaml: {e}")
```

In this method, we:

1. Read the existing `mkdocs.yaml` content if it exists.
2. Gather all files and folders from the `wiki_path`, excluding the `mkdocs.yaml` file itself.
3. Prepare a prompt for the AI to update the `mkdocs.yaml` content based on the current content and the list of wiki files.
4. Use AI to generate the updated `mkdocs.yaml` content.
5. Write the updated content back to the `mkdocs.yaml` file.

Make sure to integrate this method into the `WikiManager` class and call it where necessary to update the `mkdocs.yaml` file using AI.
## [[{"doc_id": "ce47688a-ea2b-4ab8-9577-a2da360a9738", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-07 06:57:55.405563", "updated_at": "2025-09-07 06:57:55.405594", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Update existing _update_mkdocs
## [[{"doc_id": "e0063f07-95ab-49ca-862e-7d47b63e12e7", "role": "assistant", "task_item": "analysis", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-07 06:57:55.405563", "updated_at": "2025-09-07 06:57:55.405594", "images": [], "files": [], "meta_data": {"time_taken": 13.253337383270264, "first_chunk_time_taken": 0.00020575523376464844, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
```python
import yaml
from pathlib import Path

def _update_mkdocs(self) -> None:
    """
    Use AI to update the mkdocs.yaml file, taking into account the current content
    of the mkdocs.yaml file and all the files and folders from the wiki_path.
    """
    mkdocs_file_path = Path(self.wiki_path) / MKDOCS_YAML_FILE_NAME

    # Read the existing mkdocs.yaml content
    current_mkdocs_content = {}
    if mkdocs_file_path.exists():
        with open(mkdocs_file_path, 'r') as mkdocs_file:
            current_mkdocs_content = yaml.safe_load(mkdocs_file)

    # Gather all files and folders from the wiki_path
    wiki_files = []
    for root, dirs, files in os.walk(self.wiki_path):
        for file in files:
            if file != MKDOCS_YAML_FILE_NAME:
                wiki_files.append(os.path.relpath(os.path.join(root, file), self.wiki_path))

    # Prepare the prompt for AI
    update_prompt = f"""
    <current_mkdocs_content>
    {yaml.dump(current_mkdocs_content, default_flow_style=False)}
    </current_mkdocs_content>
    <wiki_files>
    {yaml.dump(wiki_files, default_flow_style=False)}
    </wiki_files>

    Update the mkdocs.yaml content to reflect any changes in the wiki structure, 
    including new or removed files and folders. Ensure that the navigation structure 
    remains clear and logical.
    """

    try:
        messages = self._ai_chat(prompt=update_prompt)
        updated_mkdocs_content = messages[-1].content

        # Write the updated content to the mkdocs.yaml file
        with open(mkdocs_file_path, 'w') as mkdocs_file:
            mkdocs_file.write(updated_mkdocs_content)
        logger.info(f"mkdocs.yaml successfully updated at {mkdocs_file_path}")

    except Exception as e:
        logger.exception(f"Error updating mkdocs.yaml: {e}")
```
## [[{"doc_id": "29b47335-3f28-4fad-882d-9282291375b9", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-08 07:53:19.021904", "updated_at": "2025-09-08 07:53:19.021958", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Update WikiManager so:

When reading the existing wiki files for the mkdocs configuration, generate a "Tree" representation instead of a list of files. So its clear which files gelongs to each category and shows the subcategories levels.

So convert the wiki path directory into this yaml structure:
```yaml
nav:
  - folder_name:
    - subfolder_name:
       - file_path.md 
       - file_path_2.md
   - folder_2_name:
     - file_name
```

Then in the AI message pass the current "nav" yaml and ask AI to make it "user friendly" converting file names in user friendly names and only return the yaml content.

Then take the new generated "nav" yaml content and replace exising mkdocs nav section
## [[{"doc_id": "17d947ff-ede7-4086-9263-0f9e1a7e58db", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-08 07:53:19.021904", "updated_at": "2025-09-08 07:53:19.021958", "images": [], "files": [], "meta_data": {"time_taken": 38.214664697647095, "first_chunk_time_taken": 0.00020074844360351562, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To update the `WikiManager` class as per the user's comments, we'll modify the `_update_mkdocs` method to generate a tree representation of the wiki path directory structure. This involves creating a nested YAML structure for the `nav` section and then passing it to the AI for generating user-friendly names. Here's how you can implement the changes:

```python
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
    current_mkdocs_content = {}
    if mkdocs_file_path.exists():
        with open(mkdocs_file_path, 'r') as mkdocs_file:
            current_mkdocs_content = yaml.safe_load(mkdocs_file)

    # Gather all files and folders from the wiki_path and create a tree structure
    wiki_tree = self._create_wiki_tree(self.wiki_path)

    # Prepare the prompt for AI
    update_prompt = f"""
    <current_nav_content>
    {yaml.dump(current_mkdocs_content.get('nav', []), default_flow_style=False)}
    </current_nav_content>
    <wiki_tree>
    {yaml.dump(wiki_tree, default_flow_style=False)}
    </wiki_tree>
    <user_instructions>
    {user_instructions}
    </user_instructions>
    <user_language>
    {user_language}
    </user_language>

    Convert the file paths in the wiki_tree to user-friendly names and return the updated 'nav' section.
    Only return the yaml content.
    Generated content must be in user_language: {user_language}
    """

    try:
        messages = self._ai_chat(prompt=update_prompt)
        updated_nav_content = yaml.safe_load(messages[-1].content)

        # Update the 'nav' section in the mkdocs.yaml content
        current_mkdocs_content['nav'] = updated_nav_content

        # Write the updated content to the mkdocs.yaml file
        with open(mkdocs_file_path, 'w') as mkdocs_file:
            yaml.dump(current_mkdocs_content, mkdocs_file, default_flow_style=False)
        logger.info(f"mkdocs.yaml successfully updated at {mkdocs_file_path}")

    except Exception as e:
        logger.exception(f"Error updating mkdocs.yaml: {e}")

def _create_wiki_tree(self, base_path: str) -> List[Dict[str, Any]]:
    """
    Create a tree representation of the wiki directory structure.

    Args:
        base_path: The base path of the wiki directory.

    Returns:
        A list representing the directory tree structure.
    """
    tree = []
    for root, dirs, files in os.walk(base_path):
        # Create a nested dictionary for each directory
        path_parts = Path(root).relative_to(base_path).parts
        current_level = tree
        for part in path_parts:
            # Find the existing dictionary for this level or create a new one
            next_level = next((d for d in current_level if part in d), None)
            if not next_level:
                next_level = {part: []}
                current_level.append(next_level)
            current_level = next_level[part]

        # Add files to the current directory level
        for file in files:
            if file != MKDOCS_YAML_FILE_NAME:
                current_level.append(file)

    return tree
```

### Explanation:

1. **Tree Representation**: The `_create_wiki_tree` method walks through the wiki directory and creates a nested list representation of the directory structure, which includes folders and files.

2. **AI Prompt Update**: The `_update_mkdocs` method now includes the current `nav` content and the newly generated `wiki_tree` in the AI prompt. The AI is tasked with converting file paths into user-friendly names.

3. **YAML Update**: The AI-generated `nav` content replaces the existing `nav` section in the `mkdocs.yaml` file.

This solution ensures that the `mkdocs.yaml` file reflects a structured and user-friendly navigation layout, making it easier for users to navigate the wiki.