import logging
import pathlib
import os
import json
import uuid

from datetime import datetime, timezone, timedelta
from codx.junior.settings import CODXJuniorSettings

from codx.junior.model import Chat, Message
from codx.junior.utils import write_file

logger = logging.getLogger(__name__)

DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"

class ChatManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.chat_path = f"{settings.codx_path}/tasks"
        os.makedirs(self.chat_path, exist_ok=True)
        os.makedirs(f"{self.chat_path}/{DEFAULT_BOARD}/{DEFAULT_COLUMN}", exist_ok=True)

    def get_chat_file(self, chat: Chat):
        chat_file = f"{self.chat_path}/{chat.board or 'kanban'}/{chat.column or 'tasks'}/{chat.name}" if chat.board else f"{self.chat_path}/{chat.name}"
        if not chat_file.endswith(".md"):
            chat_file = chat_file + ".md"
        return chat_file

    def chat_paths(self):
        return [str(file_path) for file_path in pathlib.Path(self.chat_path).rglob("*.md")]

    def chat_board_column_name_from_path(self, file_path):
        chat_parts = file_path.replace(self.chat_path, "").split("/")[1:]
        if len(chat_parts) != 3:
            return None, None, None
   
        name = chat_parts[-1].replace(".md", "")
        column = chat_parts[-2]
        board = chat_parts[-3]
        return board, column, name
          
    def list_chats(self):
        file_paths = self.chat_paths() 
        def chat_info(file_path):
            chat = self.load_chat_from_path(chat_file=file_path)
            chat.messages = [c for c in chat.messages if not c.hide][0:1]
            return chat
        return sorted([chat_info(file_path) for file_path in file_paths],
            key=lambda x: str(x.chat_index or x.updated_at),
            reverse=True)

    def save_chat(self, chat: Chat):
        if not chat.board:
            chat.board = "kanban"
        if not chat.column:
            chat.column = tasks
        chat_file = self.get_chat_file(chat)
        chat.updated_at = datetime.now().isoformat()
        if not chat.id:
            chat.id = str(uuid.uuid4())
        if not chat.created_at:
            chat.created_at = chat.updated_at
        logger.info(f"Save chat at {chat_file}")
        write_file(chat_file, self.serialize_chat(chat))

    def delete_chat(self, board, chat_name):
        chat_file = self.get_chat_file(Chat(board=board or "", name=chat_name))
        if os.path.isfile(chat_file):
            os.remove(chat_file)

    def load_chat(self, board, column, chat_name):
        chat = Chat(board=board, column=column, name=chat_name)
        chat_file = self.get_chat_file(chat)
        if not os.path.isfile(chat_file):
            chat
        return self.load_chat_from_path(chat_file=chat_file)

    def load_chat_from_path(self, chat_file):
        board, column, name = self.chat_board_column_name_from_path(chat_file)
        # wrong setup?
        if not board or not column:
            new_chat_file = f"{self.chat_path}/{DEFAULT_BOARD}/{DEFAULT_COLUMN}/{name}.md"
            os.rename(chat_file, new_chat_file)
            chat_file = new_chat_file
            board = DEFAULT_BOARD
            column = DEFAULT_COLUMN

        with open(chat_file, 'r') as f:
            chat = self.deserialize_chat(content=f.read())
            if not chat.created_at:
                stats = os.stat(chat_file)
                chat.created_at = str(datetime.fromtimestamp(stats.st_ctime, tz=timezone.utc))
                chat.updated_at = str(datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc))
            chat.board = board
            chat.column = column
            chat.file_path = chat_file
            return chat

    def serialize_chat(self, chat: Chat):
        chat_json = { **chat.__dict__ }
        del chat_json["messages"]  
        header = f"# [[{json.dumps(chat_json)}]]"
        def serialize_message(message):
            if not message.created_at:
                message.created_at = datetime.now().isoformat()
            message_json = { **message.__dict__ }
            del message_json["content"]
            return "\n".join([
                    f"## [[{json.dumps(message_json)}]]",
                    message.content
                ]
            )
        messages = [serialize_message(message) for message in chat.messages]
        chat_content = "\n".join([header] + messages)
        return chat_content

    def deserialize_chat(self, content) -> Chat:
        lines = content.split("\n")
        chat_json = json.loads(lines[0][4:-2])
        chat = Chat(**chat_json)
        chat.messages = []
        chat_message = None
        for line in lines[1:]:
            if line.startswith("## [[{") and line.endswith("}]]"):
                chat_message = Message(**json.loads(line[5:-2]))
                chat_message.content = ""
                chat.messages.append(chat_message)
                continue
            if chat_message:
                    chat_message.content = line \
                        if not chat_message.content \
                        else f"{chat_message.content}\n{line}"
        return chat

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

    def find_by_id(self, id):
        for chat in self.list_chats():
          if chat.id == id:
              return self.load_chat_from_path(chat_file=chat.file_path)
        return None

    def load_boards(self):
        boards_file = f"{self.chat_path}/boards.json"
        all_chats = self.list_chats()
        boards = {}
        if os.path.isfile(boards_file):
            with open(boards_file, 'r') as f:
                boards = json.loads(f.read())

        all_board_dirs = [board for board in os.listdir(f"{self.chat_path}") \
                            if os.path.isdir(f"{self.chat_path}/{board}")]
        for board in set([chat.board for chat in all_chats] + all_board_dirs):
            if not boards.get(board):
                boards[board] = {}
            if not boards[board].get("columns"):
                boards[board]["columns"] = {}

            all_board_columns = [col for col in os.listdir(f"{self.chat_path}/{board}") \
                        if os.path.isdir(f"{self.chat_path}/{board}/{col}") ]
            for col in set([chat.column for chat in all_chats if chat.board == board]
                            +
                            all_board_columns):
                if not boards[board]["columns"].get(col):
                    boards[board]["columns"][col] = {}

        return boards

    def save_boards(self, boards):
        boards_file = f"{self.chat_path}/boards.json"
        with open(boards_file, 'w') as f:
            f.write(json.dumps(boards))