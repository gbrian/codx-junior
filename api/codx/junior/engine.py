import logging
import os
import shutil
from contextlib import contextmanager
from typing import List, Optional

from codx.junior.ai import AI
from codx.junior.changes.change_manager import ChangeManager
from codx.junior.chat_manager import ChatManager
from codx.junior.db import Chat
from codx.junior.events.event_manager import EventManager
from codx.junior.globals import (
    find_project_by_id
)
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.mentions.mention_manager import MentionManager
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.settings import CODXJuniorSettings
from codx.junior.sio.session_channel import SessionChannel

logger = logging.getLogger(__name__)


class CODXJuniorSession:
    def __init__(
        self,
        settings: CODXJuniorSettings = None,
        codx_path: str = None,
        channel: Optional[SessionChannel] = None,
    ) -> None:
        self.settings = settings or CODXJuniorSettings.from_project_file(f"{codx_path}/project.json")
        self.channel = channel
        self.event_manager = EventManager(codx_path=codx_path, channel=channel)
        self.change_manager = ChangeManager(settings=self.settings, event_manager=self.event_manager)

    def switch_project(self, project_id: str) -> 'CODXJuniorSession':
        if not project_id or project_id == self.settings.project_id:
            return self
        settings = find_project_by_id(project_id=project_id)
        return CODXJuniorSession(settings=settings, channel=self.channel) if settings else self

    def log_info(self, msg: str) -> None:
        logger.info("[%s] %s", self.settings.project_name, msg)

    def log_error(self, msg: str) -> None:
        logger.error("[%s] %s", self.settings.project_name, msg)

    def log_exception(self, msg: str) -> None:
        logger.exception("[%s] %s", self.settings.project_name, msg)

    def coder_open_file(self, file_name: str) -> List[str]:
        if not file_name.startswith(self.settings.project_path):
            file_name = f"{self.settings.project_path}/{file_name}".replace("//", "/")
        os.system(f"code-server -r {file_name}")
        return [self.settings.project_path, file_name, file_name.startswith(self.settings.project_path)]

    @contextmanager
    def chat_action(self, chat: Chat, event: str) -> None:
        self.event_manager.chat_event(chat=chat, message=f"{event} starting")
        self.log_info("Start chat %s", chat.name)
        try:
            yield
        except Exception as ex:
            self.event_manager.chat_event(chat=chat, message=f"{event} error: {ex}", event_type="error")
            self.log_exception("Chat %s %s error: %s", chat.name, event, ex)
        finally:
            self.event_manager.chat_event(chat=chat, message=f"{event} done")
            self.log_info("Chat done %s", chat.name)

    def delete_project(self) -> None:
        shutil.rmtree(self.settings.codx_path)
        logger.error("PROJECT REMOVED %s", self.settings.codx_path)

    def get_mention_manager(self) -> MentionManager:
        return MentionManager(settings=self.settings, event_manager=self.event_manager)

    def get_chat_manager(self) -> ChatManager:
        return ChatManager(settings=self.settings)

    def get_profile_manager(self) -> ProfileManager:
        return ProfileManager(settings=self.settings)

    def get_ai(self, llm_model: Optional[str] = None) -> AI:
        return AI(settings=self.settings, llm_model=llm_model)

    def get_knowledge(self) -> Knowledge:
        return Knowledge(settings=self.settings)

    def get_wiki(self):
        from codx.junior.wiki.wiki_manager import WikiManager
        return WikiManager(session=self)

    def get_browser(self):
        from codx.junior.browser.browser import Browser
        return Browser(session=self)

    # The remaining methods follow...


