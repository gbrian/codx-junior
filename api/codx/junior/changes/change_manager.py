import os
import time
import logging
import asyncio  # Import asyncio for concurrency

from codx.junior.events.event_manager import EventManager
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.globals import MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS, CODX_JUNIOR_API_BACKGROUND
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

    def check_project_changes(self):
        if not self.settings.is_valid_project():
            return False

        self.knowledge.clean_deleted_documents()
        new_files = self.knowledge.detect_changes()

        if not new_files:
            logger.info(f"check_project_changes {self.settings.project_name} no changes")
            return False

        return True

    async def process_project_changes(self):
        if not self.settings.is_valid_project():
            logger.error(f"Checking project error, not valid: {self.settings.project_name}") 
            
            return

        self.knowledge.clean_deleted_documents()
        new_files, _ = self.knowledge.detect_changes()
            
        tasks = []  # List to hold tasks

        if self.settings.project_name == "der-viewer":
            logger.info(f"Checking project {self.settings.project_name} - files: {new_files}") 
        
        def is_valid_file(file_path):
            if self.settings.project_name == "der-viewer":
                return True
            if (int(time.time()) - int(
                    os.stat(file_path).st_mtime) < MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS):
                return True
            return False

        new_files = [file_path for file_path in new_files if is_valid_file(file_path)]
        
        if not new_files:
            return
        
        logger.info(f"Checking project {self.settings.project_name} - files: {new_files}") 
        
        for file_path in new_files:  # Process files concurrently
            tasks.append(self.process_project_change(file_path=file_path))  # Append coroutine to tasks

        await asyncio.gather(*tasks)  # Run tasks concurrently

    async def process_project_change(self, file_path: str):
        res = await self.mention_manager.check_file_for_mentions(file_path=file_path)
        if res == "processing":
            logger.info(f"[process_project_changes] Skipping file {file_path} - mentions: {res}")
            return

        if not self.settings.watching:
            return 

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

    @profile_function
    async def check_file(self, file_path: str, force: bool = False):
        res = await self.mention_manager.check_file_for_mentions(file_path=file_path)
        logger.info(f"Check file {file_path} for mentions: {res}")
        if res == "processing":
            return

        if CODX_JUNIOR_API_BACKGROUND:
            self.event_manager.send_event(f"Check file: {file_path}")

            # Reload knowledge
            if force or self.settings.watching:
                self.knowledge.reload_path(path=file_path)
                self.event_manager.send_event(f"Kownledge updated for: {file_path}")
            if self.settings.project_wiki:
                self.wiki_manager.build_file(file_path=file_path)

