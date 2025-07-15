# codx/junior/changes/change_manager.py

import os
import time
import logging

from codx.junior.events.event_manager import EventManager
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.globals import MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS
from codx.junior.mentions.mention_manager import MentionManager

logger = logging.getLogger(__name__)


class ChangeManager:
    def __init__(self, settings, event_manager = None):
        self.settings = settings
        if not event_manager:
            event_manager = EventManager(codx_path=settings.codx_path)
        self.event_manager = event_manager
        self.mention_manager = MentionManager(settings=settings, event_manager=event_manager)

    def check_project_changes(self):
        if not self.settings.is_valid_project():
            return False

        knowledge = Knowledge(settings=self.settings)
        knowledge.clean_deleted_documents()
        new_files = knowledge.detect_changes()

        if not new_files:
            logger.info(f"check_project_changes {self.settings.project_name} no changes")
            return False

        return True

    async def process_project_changes(self):
        if not self.settings.is_valid_project():
            return

        knowledge = Knowledge(settings=self.settings)
        knowledge.clean_deleted_documents()
        new_files, _ = knowledge.detect_changes()
        if not new_files:
            return

        def changed_file():
            for file_path in new_files:
                if (int(time.time()) - int(
                        os.stat(file_path).st_mtime) < MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS):
                    return file_path
            return None

        file_path = changed_file()  # process one file at a time by modified time
        if not file_path:
            return

        logger.info(f"[process_project_changes] Processing file changes {file_path}")
        res = await self.mention_manager.check_file_for_mentions(file_path=file_path)
        if res == "processing":
            logger.info(f"[process_project_changes] Skipping file {file_path} - mentions: {res}")
            return

        if self.settings.watching:
            logger.info(f"Reload knowledge files {file_path}")
            knowledge.reload_path(path=file_path)
            self.event_manager.send_knowled_event(type="loaded", file_path=file_path)
