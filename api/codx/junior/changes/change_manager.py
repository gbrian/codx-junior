import os
import time
import logging
import asyncio 

from datetime import datetime, timedelta

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
from codx.junior.chat_manager import ChatManager

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
        self.chat_manager = ChatManager(settings=self.settings)

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

    def update_project_metrics(self):
        last_check_str = self.settings.metrics.get("last_check", None)
        if last_check_str:
            last_check = datetime.fromisoformat(last_check_str)
            if datetime.now() - last_check < timedelta(minutes=2):
                return self.settings.metrics

        last_check = datetime.now().isoformat()

        try:
            number_of_chats = self.chat_manager.chat_count()
            chat_changed_last = self.chat_manager.last_chats()

            last_update = None
            if chat_changed_last:
                last_update = chat_changed_last[0].updated_at
            return {
                "last_check": last_check,
                "last_update": last_update,
                "number_of_chats": number_of_chats,
                "chats_changed_last": chat_changed_last
            }
        except Exception as ex:
            logger.error("Error processing project metrics: %s - %s", self.settings.project_name, ex)
            return {
                "error": str(ex)
            }

