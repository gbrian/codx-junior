"""
Chat + AI
This module is responsible for the AI chat interaction
"""
import logging
import pathlib
import os
import json
import uuid
import shutil
import yaml

from slugify import slugify
from collections import deque, defaultdict

from typing import Dict, Any, List

from datetime import datetime, timezone, timedelta
from codx.junior.settings import CODXJuniorSettings

from codx.junior.db import Chat, Message
from codx.junior.utils.utils import write_file

from codx.junior.profiling.profiler import profile_function

from codx.junior.chat.chat_export import ChatExport, ExportedDocument

from codx.junior.events.event_manager import EventManager

from codx.junior.project.project_discover import find_project_by_id 

logger = logging.getLogger(__name__)

DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"

class ChatManager:
    def __init__(self, settings: CODXJuniorSettings, event_manager=None):
        self.settings = settings
        self.chat_path = f"{settings.codx_path}/tasks"
        self.event_manager = event_manager if event_manager else EventManager(codx_path=settings.codx_path)
        os.makedirs(self.chat_path, exist_ok=True)
        os.makedirs(f"{self.chat_path}/{DEFAULT_BOARD}/{DEFAULT_COLUMN}", exist_ok=True)

    def get_chat_file(self, chat: Chat):
        chat_file = f"{self.chat_path}/{chat.board}/{chat.column}/{slugify(chat.name)}.{chat.id}.json"
        return chat_file

    def chat_paths(self, last_update: datetime = None):
        """
        Return chat file paths, optionally filtering by last update time.
        
        :param last_update: Only return paths for chats updated since this date.
        :return: List of file paths.
        """
        all_paths = [str(file_path) for file_path in pathlib.Path(self.chat_path).rglob("*.yaml")] + \
                    [str(file_path) for file_path in pathlib.Path(self.chat_path).rglob("*.json")]
        
        if last_update:
            # Filter paths by file modified time
            all_paths = [path for path in all_paths if datetime.fromtimestamp(os.path.getmtime(path)) > last_update]
        
        return all_paths

    def chat_board_column_name_from_path(self, file_path):
        chat_parts = file_path.replace(self.chat_path, "").split("/")[1:]
        if len(chat_parts) != 3:
            return None, None, None
   
        name = chat_parts[-1].replace(".md", "")
        column = chat_parts[-2]
        board = chat_parts[-3]
        return board, column, name

    def list_chats(self, from_date: str = None):
        last_update = None
        if from_date:
            last_update = datetime.fromisoformat(from_date)
        file_paths = self.chat_paths(last_update=last_update)
        def list_chat_chat_info(file_path):
            try:
                chat = self.load_chat_from_path(chat_file=file_path, chat_only=True)
                return chat
            except Exception as ex:
                logger.error(f"Error loading chat '{file_path}': {ex}")
            return None
            
        return sorted([chat \
            for chat in [list_chat_chat_info(file_path) for file_path in file_paths] \
            if chat],
            key=lambda x: str(x.chat_index or x.updated_at),
            reverse=True)

    def save_chat(self, chat: Chat, chat_only=False):
        
        # Check owner_project_id
        if chat.owner_project_id != self.settings.project_id:
            chat_project = find_project_by_id(chat.owner_project_id)
            chat_manager = ChatManager(settings=chat_project, event_manager=self.event_manager)
            return chat_manager.save_chat(chat=chat, chat_only=chat_only)

        if not chat.board:
            chat.board = "kanban"
        if not chat.column:
            chat.column = "tasks"
        if not chat.id:
            chat.id = str(uuid.uuid4())
        if not chat.created_at:
            chat.created_at = chat.updated_at

        chat.updated_at = datetime.now().isoformat()

        current_chat = self.find_by_id(chat_id=chat.id)
        if chat_only and current_chat:
            chat.messages = current_chat.messages
        users = []
        profiles = []
        for msg in chat.messages:
            if not msg.doc_id:
                msg.doc_id = str(uuid.uuid4())
            if msg.user:
                users.append(msg.user)
            profiles = profiles + msg.profiles
        chat.users = list(set(users))
        chat.profiles = list(set(profiles))
        chat.file_path = self.get_chat_file(chat)

        self.store_chat(chat=chat)

        # remove old chat
        # old yaml
        if os.path.isfile(chat.file_path.replace(".json", ".yaml")):
            logger.info("Remove old yaml chat: %s", chat.file_path)
            os.remove(chat.file_path.replace(".json", ".yaml"))
        # old path
        if current_chat:
            logger.info(f"Save chat, current_chat {current_chat.id} at {current_chat.file_path}")
            if chat.file_path != current_chat.file_path:
                self.delete_chat(current_chat.file_path)
        
        self.event_manager.chat_event(chat=chat, event_type="changed")
        
        return chat

    def store_chat(self, chat):
        logger.info("Save chat: %s", chat.file_path)
        os.makedirs(os.path.dirname(chat.file_path), exist_ok=True)
        with open(chat.file_path, 'w') as f:
            f.write(json.dumps(chat.model_dump(), indent=2))

    def delete_chat(self, file_path: str = None, chat_id: str = None):
        logger.info(f"Removing chat by file_path: {file_path}  - chat_id: {chat_id}")
        
        if chat_id:
            chat = self.find_by_id(chat_id)
            file_path = chat.file_path

        if os.path.isfile(file_path) \
            and file_path.startswith(self.chat_path):
            logger.info(f"Removing chat at {file_path}")
            os.remove(file_path)
        else:
            logger.error(f"Removing chat error {file_path}")

    def load_chat(self, board, column = None, chat_name = None):
        chat = Chat(board=board, column=column, name=chat_name)
        chat_file = self.get_chat_file(chat)
        if not os.path.isfile(chat_file):
            chat.file_path = chat_file
            return chat
        return self.load_chat_from_path(chat_file=chat_file)

    def load_chat_from_path(self, chat_file: str, chat_only: bool = False):
        
        with open(chat_file, 'r') as f:
            chat_data = json.loads(f.read())
            chat = Chat(**chat_data)
            if chat_only:
                chat.messages = []
            chat.owner_project_id = self.settings.project_id
            return chat

    def delete_kanban(self, kanban_title: str):
        shutil.rmtree(f"{self.chat_path}/{kanban_title}")

    def chat_count(self):
        return len(self.chat_paths())

    def last_chats(self):
        last_days = (datetime.now() - timedelta(days=2)).timestamp()
        chat_paths = [{
            "chat_path": chat_path,
            "updated_at": os.stat(chat_path).st_ctime
        } for chat_path in self.chat_paths()]
        chat_paths = [c for c in chat_paths if c["updated_at"] > last_days] 
        last_updated_chats = sorted(
                                chat_paths,
                                key=lambda x: x["updated_at"])
        last_updated_chats.reverse()
        last_updated_chats = last_updated_chats[0:3]
        def load_chat(file_path):
            return self.load_chat_from_path(chat_file=file_path)
        return [load_chat(c["chat_path"]) for c in last_updated_chats]

    def find_by_id(self, chat_id):
        if chat_id:
            file_path = next((path for path in self.chat_paths() if chat_id in path), None)
            if file_path:
                return self.load_chat_from_path(chat_file=file_path)
            else:
                logger.error("[chat_id] not found: %s\n%s", chat_id, self.chat_paths())
        return None

    def load_kanban_from_file(self, kanban_file: str):
        kanban = {
          "version": 0.1,
          "boards": {},
          "tags": {}
        }
        if os.path.isfile(kanban_file):
            with open(kanban_file, 'r') as f:
                kanban = json.loads(f.read())
            version = kanban.get("version", None)
            if not version:
                kanban = {
                    "version": 0.1,
                    "boards": kanban,
                    "tags": {}
                }
        logger.info("Loading %s kanban", self.settings.project_name)
        return kanban

    @profile_function
    def load_kanban(self):
        kanban_file = f"{self.chat_path}/kanban.json"
        logger.info(f"load_kanban {kanban_file}")
        # all_chats = self.list_chats()
        return self.load_kanban_from_file(kanban_file=kanban_file)

    def save_kanban(self, kanban):
        kanban_file = f"{self.chat_path}/kanban.json"
        with open(kanban_file, 'w') as f:
            f.write(json.dumps(kanban))


    def find_chats(self, last_update: datetime = None):
        """
        Return chats based on filters.
        
        :param last_update: Return chats updated since this date.
        :return: List of Chat objects.
        """
        filtered_chats = []
        
        # Iterate through all chat file paths with optional last_update filter
        for file_path in self.chat_paths(last_update=last_update):
            chat = self.load_chat_from_path(chat_file=file_path)
            if chat:
                filtered_chats.append(chat)
        
        return filtered_chats


    def traverse_chat_messages(self, chat_id, all_chats: List[Chat]) -> List[Message]:
        """
        Traverse messages in the chat and its descendants, yielding messages.
        """
        messages = []
        chat = self.find_by_id(chat_id)

        # Traverse current chat messages
        logger.info("chat_export traversing chat: %s, messages: %s", chat.name, len(chat.messages))
        for message in chat.messages:
            # Check if there's a chat pointing to this message
            linked_chat = next((c for c in all_chats if c.message_id == message.doc_id), None)
            if linked_chat:
                messages.extend(self.traverse_chat_messages(chat_id=linked_chat.id, all_chats=all_chats))
            
            # Append the message itself
            messages.append(message)
        
        # Find child chats and sort them by child_index
        child_chats = sorted([c for c in all_chats if c.parent_id == chat.id], key=lambda x: x.child_index)
        for child_chat in child_chats:
            messages.extend(self.traverse_chat_messages(chat_id=child_chat.id, all_chats=all_chats))
        
        return messages

    def build_markdown_document(self, chat_id) -> str:
        """
        Traverse the chat and generate a markdown document.
        Ignore messages with the 'hide' flag set to True.
        """
        all_chats = self.list_chats()
        messages = self.traverse_chat_messages(chat_id=chat_id, all_chats=all_chats)
        markdown = ""
        for msg in messages:
            if not msg.hide:
                markdown += f"# {msg.content}\n\n"
        return markdown

    def export_chat(self, chat_id: str, export_format: str) -> ExportedDocument:
        """
        Export a chat and its descendants to the specified format.

        :param chat_id: The ID of the chat to export.
        :param export_format: The format to export to (e.g., markdown, docx, pdf, excel).
        :return: An ExportedDocument containing the exported chat.
        """
        chat = self.find_by_id(chat_id=chat_id)
        content = self.build_markdown_document(chat_id=chat_id)
        # Use ChatExport to export the chat
        chat_exporter = ChatExport(chat=chat, content=content, export_format=export_format)
        return chat_exporter.export_chat()