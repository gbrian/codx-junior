# [[{"id": "3f606924-c977-4456-996c-a5a644c917ef", "doc_id": null, "project_id": null, "parent_id": "511c3d55-1065-4298-bc0a-a1d93cbd99c5", "status": "", "tags": [], "file_list": [], "profiles": ["software_developer"], "users": ["admin"], "name": "Build wiki tree", "description": "In this conversation, you provided a JSON structure representing wiki configuration and requested its conversion into a Pydantic \"WikiConfig\" class. The resulting Python code defines data models to handle the configuration, including classes for sidebar items and project settings. The implementation includes type annotations and logging for tracing and debugging purposes while adhering to best practices for clear documentation and meaningful variable names. This Pydantic model facilitates robust validation and management of wiki configurations in Python.", "created_at": "2025-05-24 14:27:07.049598", "updated_at": "2025-06-04T09:29:09.118726", "mode": "task", "kanban_id": "", "column_id": "", "board": "Wiki manager", "column": "In Development", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/api/.codx/tasks/Wiki manager/In Development/build-wiki-tree.3f606924-c977-4456-996c-a5a644c917ef.md", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "2a92f6c0-24a8-419c-a058-8e171741a804", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-06-04 09:21:48.531201", "updated_at": "2025-06-04 09:21:48.531244", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true}]]
@codx-api load wiki_manager and extract build_tree methods to analyze
## [[{"doc_id": "c9a5788e-8561-43fc-b15a-ba2177a710af", "role": "assistant", "task_item": "analysis", "hide": true, "improvement": false, "created_at": "2025-06-04 09:21:48.531201", "updated_at": "2025-06-04 09:21:48.531244", "images": [], "files": ["/codx/junior/wiki/wiki_template/wiki-amanger.sh"], "meta_data": {"time_taken": 32.77531313896179, "first_chunk_time_taken": 30.811152935028076, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true}]]
```python
# /home/codx-junior/codx-junior/api/codx/junior/wiki/wiki_manager.py

import os
import json
import shutil
from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession
from codx.junior.context import generate_markdown_tree
from codx.junior.utils import exec_command

class WikiManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.session = CODXJuniorSession(settings=settings)
        self.wiki_path = self.settings.get_project_wiki_path()
        self.vitepress_dir = os.path.join(self.wiki_path, '.vitepress')
        self.dist_dir = os.path.join(self.vitepress_dir, 'dist')
        self.config_path = os.path.join(self.vitepress_dir, 'config.json')
        
        self.initialize_vitepress()

    def build_wiki(self):
        """Execute the wiki build process using a shell command."""
        std, err = exec_command('bash wiki-manager.sh', cwd=self.wiki_path)
        if not os.path.isdir(self.dist_dir):
            raise Exception(f"Error building wiki: {std} - {err}")

    def create_wiki_tree(self, config) -> dict:
        """
        Based on project config and project files will return a sidebar definition
        """
        project_tree = generate_markdown_tree(knowledge.get_all_sources())

        prompt = f"""
        """
        response = self.session.get_ai().chat(prompt=prompt)[-1]
```

## [[{"doc_id": "b0ee1e80-a9dd-4c43-979d-01786c837b0c", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-06-04 09:21:48.531201", "updated_at": "2025-06-04 09:21:48.531244", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": [], "done": true}]]
Convert this json to pydatinc "WikIConfig" class:
```json

{
  "project": {
    "name": null,
    "description": null,
    "icon": null,
    "sidebar": [
      {
        "text": "Getting Started",
        "items": [
          { "text": "Quick start", "link": "/getting-started" },
          { "text": "Initial setup", "link": "/initial-setup" }
        ]
      }
    ]
  }
}
```


## [[{"doc_id": "6163b856-9d22-4479-a89e-d0f0e30e2785", "role": "assistant", "task_item": "analysis", "hide": false, "improvement": false, "created_at": "2025-06-04 09:21:48.531201", "updated_at": "2025-06-04 09:21:48.531244", "images": [], "files": [], "meta_data": {"time_taken": 7.638105630874634, "first_chunk_time_taken": 2.3385775089263916, "model": "gpt-4o"}, "profiles": ["software_developer", "software_developer"], "user": null, "knowledge_topics": [], "done": true}]]
```markdown
# Wiki Config Data Model

```python
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

# Define logger
import logging
logger = logging.getLogger(__name__)

class SidebarItem(BaseModel):
    text: str
    link: str

class SidebarSection(BaseModel):
    text: str
    items: List[SidebarItem]

class ProjectConfig(BaseModel):
    name: Optional[Any] = None
    description: Optional[Any] = None
    icon: Optional[Any] = None
    sidebar: List[SidebarSection]

class WikiConfig(BaseModel):
    project: ProjectConfig
```

## Overview

The `WikiConfig` class structure is designed to represent and validate the configuration for a project's wiki setup using Pydantic. This structure reflects the configuration format traditionally serialized as JSON, providing a structured and type-safe way to handle these configurations in Python.

### Components

- **SidebarItem**: Represents each item in a sidebar with `text` for display and `link` for navigation.

- **SidebarSection**: Represents a section in the sidebar, containing a list of `SidebarItem` objects.

- **ProjectConfig**: Represents the entire project configuration with attributes like `name`, `description`, and `icon`. The `sidebar` is a list of `SidebarSection` instances.

- **WikiConfig**: The root configuration class holding the `ProjectConfig`.

### Usage

This Pydantic model will allow developers to easily parse, validate, and manage wiki-related settings, ensuring correct type usage and providing informative error messages when validations fail. The logger is included to log critical activities and errors during manipulation and validation of configuration data.
```