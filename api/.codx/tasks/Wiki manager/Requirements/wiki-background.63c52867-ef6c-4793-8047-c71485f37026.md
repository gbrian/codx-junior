# [[{"id": "63c52867-ef6c-4793-8047-c71485f37026", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/wiki/wiki_manager.py", "/shared/codx-junior/api/codx/junior/background.py", "/shared/codx-junior/api/codx/junior/changes/change_manager.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Wiki background", "description": "The conversation involves integrating new functionalities into a project management system. A method `get_last_update` is added to the `WikiManager` class to fetch the last update date of wiki files. The `Background` and `ChangeManager` classes are updated to call a new method in `WikiManager` that refreshes wiki documents based on file changes since the last update. This ensures that the wiki is kept up-to-date with project changes. The changes also involve concurrent processing using asyncio for efficient handling of project changes. The overall goal is to enhance the system's ability to maintain accurate and current documentation.", "created_at": "2025-09-07 10:30:21.143424", "updated_at": "2025-09-08T06:49:13.214283", "mode": "task", "kanban_id": "", "column_id": "", "board": "Wiki manager", "column": "Requirements", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Wiki manager/Requirements/wiki-background.63c52867-ef6c-4793-8047-c71485f37026.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": [], "chat_links": [], "pr_view": {}}]]
## [[{"doc_id": "a5fef8d0-4aeb-40e7-8ed0-17a0046bbed2", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-07 10:30:21.140960", "updated_at": "2025-09-07 10:30:21.140988", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Background process to update wiki docs.
WikiManager will have "get_last_update" that will return the last creation date of a wiki file.
Background and change management must call periodically WikiManager refresh with files changes since last wiki update and create the wiki documents

## [[{"doc_id": "b8b9eb1d-cb52-4f93-9811-350fbcaf49f9", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-07 10:30:21.140960", "updated_at": "2025-09-07 10:30:21.140988", "images": [], "files": [], "meta_data": {"time_taken": 79.43925762176514, "first_chunk_time_taken": 0.00012803077697753906, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To incorporate the user comments into the existing code, we need to make several changes. We'll add a new method `get_last_update` to the `WikiManager` class to fetch the last update date of a wiki file. Also, we'll update the `Background` and `ChangeManager` classes to periodically call a new method in `WikiManager` that refreshes wiki documents based on file changes since the last update.

Here's how the updated files would look:

```python /shared/codx-junior/api/codx/junior/wiki/wiki_manager.py
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
        self.is_wiki_active = True if self.wiki_path else False
        self.wiki_home_path = os.path.join(self.wiki_path, "index.md")
        self.wiki_settings_path = os.path.join(self.settings.codx_path, "wiki_settings.json")

    def get_last_update(self) -> datetime.datetime:
        """
        Get the last update date of the wiki files.

        Returns:
            A datetime object representing the last update date.
        """
        try:
            latest_update = max(
                datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(root, file)))
                for root, _, files in os.walk(self.wiki_path) for file in files
            )
            return latest_update
        except ValueError:
            return datetime.datetime.min

    def refresh_wiki(self, changed_files: List[str]) -> None:
        """
        Refresh the wiki documents for files that have changed since the last update.

        Args:
            changed_files: A list of file paths that have changed since the last update.
        """
        for file_path in changed_files:
            try:
                self.create_wiki_document(file_path)
            except Exception as ex:
                logger.exception(f"Error refreshing wiki document for file {file_path}: {ex}")

    # Other methods remain unchanged...
```

```python /shared/codx-junior/api/codx/junior/background.py
import asyncio
import logging
import time
from datetime import datetime, timedelta
from threading import Thread, Lock
from typing import Dict

from codx.junior.ai import AIManager
from codx.junior.changes.change_manager import ChangeManager
from codx.junior.globals import (
    CODX_JUNIOR_API_BACKGROUND,
)
from codx.junior.project.project_discover import (
    find_all_projects
)
from codx.junior.settings import read_global_settings

# Setup logging
logger = logging.getLogger(__name__)

# A global tracking dictionary to manage files currently being processed
FILES_CHECKING = {}
FILES_CHECKING_LOCK = Lock()
CHECK_TIMEOUT = timedelta(minutes=1)

# Quarantine settings
QUARANTINE_TRACKER: Dict[str, Dict] = {}
QUARANTINE_LOCK = Lock()
QUARANTINE_DELAYS = [0, 1, 10, 30, 120]  # Minutes

def start_background_services(app) -> None:
    """
    Function to start background services for project watching and processing.
    """
    if not CODX_JUNIOR_API_BACKGROUND:
        return
    logger.info("*** Starting background processes ***")
    reload_models()

    # Start the project checking in a separate thread
    Thread(target=check_projects, args=(True,)).start()

    # Start the project checking in a separate thread
    Thread(target=check_projects).start()

def reload_models() -> None:
    """
    Reload AI models based on the current global settings.
    """
    try:
        AIManager().reload_models(read_global_settings())
        logger.info("AI models reloaded successfully.")
    except Exception as ex:
        logger.exception(f"Failed to reload AI models: {ex}")


def is_project_in_quarantine(project_name: str) -> bool:
    """
    Determine if a project is in quarantine based on its last check time and the delay.
    """
    quarantine_info = QUARANTINE_TRACKER.get(project_name)
    if not quarantine_info:
        return False

    delay_minutes = QUARANTINE_DELAYS[min(quarantine_info["fail_count"], len(QUARANTINE_DELAYS) - 1)]
    next_allowed_check = quarantine_info["last_checked"] + timedelta(minutes=delay_minutes)
    return datetime.now() < next_allowed_check


def update_quarantine_status(project_name: str, success: bool) -> None:
    """
    Update the quarantine status of a project depending on whether the check was successful.
    """
    with QUARANTINE_LOCK:
        quarantine_info = QUARANTINE_TRACKER.setdefault(project_name, {"fail_count": 0, "last_checked": datetime.min})

        if success:
            quarantine_info["fail_count"] = 0  # Reset on success
        else:
            quarantine_info["fail_count"] += 1
            logger.info(f'Adding project to quarantine: {project_name} - error count: {quarantine_info["fail_count"]}')

        quarantine_info["last_checked"] = datetime.now()


def check_projects(mention_only = False) -> None:
    """
    Continuously checks for updates in all projects.
    """

    async def check_project(project) -> None:
        """
        Process and handle the changes in a project asynchronously.
        """
        try:
            session = ChangeManager(settings=project)
            #if not session.settings.metrics:
            #    session.update_project_metrics()
            await session.process_project_changes(mention_only)
            update_quarantine_status(project.project_name, success=True)
        except Exception as ex:
            update_quarantine_status(project.project_name, success=False)
            project.last_error = str(ex)
            logger.exception(f"Error processing project changes: {project.project_name}\n{ex}")

    while True:
        try:
            projects = find_all_projects()
            for project in projects.values():
                if is_project_in_quarantine(project.project_name):
                    continue

                try:
                    asyncio.run(check_project(project=project))
                except Exception as ex:
                    logger.error(f"Unhandled exception during project checking: {ex}")
        except Exception as ex:
            logger.exception(f"Error checking projects: {ex}")
        time.sleep(0.1)

        # Trigger wiki refresh
        try:
            latest_update = WikiManager(settings=project).get_last_update()
            changed_files = [file for file in projects if os.path.getmtime(file) > latest_update.timestamp()]
            WikiManager(settings=project).refresh_wiki(changed_files)
        except Exception as ex:
            logger.exception(f"Error refreshing wiki documents: {ex}")

```

```python /shared/codx-junior/api/codx/junior/changes/change_manager.py
import os
import time
import logging
import asyncio  # Import asyncio for concurrency

from codx.junior.events.event_manager import EventManager
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.globals import (
  MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS,
  MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS,
  CODX_JUNIOR_API_BACKGROUND
)
from codx.junior.mentions.mention_manager import MentionManager
from codx.junior.profiling.profiler import profile_function
from codx.junior.wiki.wiki_manager import WikiManager

from codx.junior.whisper.audio_manager import AudioManager

from langchain.schema.document import Document

logger = logging.getLogger(__name__)

class ChangeManager:
    def __init__(self, settings, event_manager=None):
        self.settings = settings
        if not event_manager:
            event_manager = EventManager(codx_path=settings.codx_path)
        self.event_manager = event_manager
        self.mention_manager = MentionManager(settings=settings, event_manager=event_manager)
        self.knowledge = Knowledge(settings=self.settings)
        self.wiki_manager = WikiManager(settings=settings)
        self.audio_manager = AudioManager()

    async def process_project_changes(self, mention_only: bool):
        if not self.settings.is_valid_project():
            logger.error(f"Checking project error, not valid: {self.settings.project_name}") 
            
            return

        if not mention_only:
            self.knowledge.clean_deleted_documents()
        current_sources_and_updates = self.knowledge.get_db().get_all_sources()
        new_files, _ = self.knowledge.detect_changes(current_sources_and_updates)
            
        tasks = []  # List to hold tasks

        TOUT = MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS if mention_only else \
                MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS
        def is_valid_file(file_path):
            if (int(time.time()) - int(
                    os.stat(file_path).st_mtime) < TOUT):
                return True
            return False

        new_files = [file_path for file_path in new_files if is_valid_file(file_path)]
        
        if not new_files:
            return
        
        logger.info(f"Checking project {self.settings.project_name} - files: {new_files}") 
        
        for file_path in new_files:  # Process files concurrently
            if mention_only:
                tasks.append(self.process_project_mentions(file_path=file_path))  # Append coroutine to tasks
            elif self.settings.watching:
                tasks.append(self.process_project_change(file_path=file_path))  # Append coroutine to tasks

        await asyncio.gather(*tasks)  # Run tasks concurrently

        # Refresh the wiki with the new files
        self.wiki_manager.refresh_wiki(new_files)

    async def process_project_mentions(self, file_path: str):
        await self.mention_manager.check_file_for_mentions(file_path=file_path)

    async def process_project_change(self, file_path: str):
        logger.info(f"[process_project_changes] Processing file changes {file_path}")
        is_media_file = self.audio_manager.is_valid_media_file(file_path=file_path)
        logger.info(f"Reload knowledge file {file_path} - is media: {is_media_file}")    
        if is_media_file:
            logger.info(f"Converting media file {file_path}")
            transcript_info = self.audio_manager.transcribe_from_file(file_path=file_path)
            self.knowledge.get_db().index_documents(documents=[Document(page_content="", metadata={
              "source": file_path,
              "language": file_path.split(".")[-1],
              "type": "audio"
            })])
            if transcript_info["is_new"]:
                file_path = transcript_info["transcript_file_path"]
            else:
                return
        
        self.knowledge.reload_path(path=file_path)
        self.event_manager.send_knowled_event(type="loaded", file_path=file_path)
        
        if self.settings.project_wiki:
            try:
                await self.wiki_manager.build_file(file_path=file_path)
            except Exception as ex:
                logger.exception(f"Error processing wiki changes for file {file_path}", ex)
```

These changes ensure that the wiki documents are updated based on the latest changes in the project files, leveraging the background processing capabilities.