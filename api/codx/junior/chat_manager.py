import logging
import pathlib
import os
import json
from datetime import datetime, timezone
from codx.junior.settings import CODXJuniorSettings

from codx.junior.model import Chat, Message
from codx.junior.utils import write_file

class ChatManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.chat_path = f"{settings.codx_path}/tasks"
        os.makedirs(self.chat_path, exist_ok=True)

    def list_chats(self):
        path = self.chat_path
        file_paths = [str(file_path) for file_path in pathlib.Path(path).rglob("*.md")]
        def chat_info(file_path):
          name = os.path.basename(file_path).split(".")[0]
          chat = self.load_chat(chat_name=name)
          chat.messages = chat.messages[0:1]
          return {
            **chat.__dict__,
            "file_path": file_path
          }
        return sorted([chat_info(file_path) for file_path in file_paths],
            key=lambda x: x["updated_at"],
            reverse=True)

    def save_chat(self, chat: Chat):
        chat_file = f"{self.chat_path}/{chat.name}"
        if not chat_file.endswith(".md"):
            chat_file = chat_file + ".md"
        chat.updated_at = datetime.now().isoformat()
        if not chat.created_at:
            chat.created_at = chat.updated_at
        write_file(chat_file, self.serialize_chat(chat))

    def delete_chat(self, chat_name: str):
        chat_file = f"{self.chat_path}/{chat_name}"
        if not chat_file.endswith(".md"):
            chat_file = chat_file + ".md"
        if os.path.isfile(chat_file):
            os.remove(chat_file)

    def load_chat(self, chat_name):
        chat_file = f"{self.chat_path}/{chat_name}"
        if not chat_file.endswith(".md"):
            chat_file += ".md"
        with open(chat_file, 'r') as f:
            chat = self.deserialize_chat(content=f.read())
            if not chat.created_at:
                stats = os.stat(chat_file)
                chat.created_at = str(datetime.fromtimestamp(stats.st_ctime, tz=timezone.utc))
                chat.updated_at = str(datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc))
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
            chat_message.content = line if not chat_message.content else f"{chat_message.content}\n{line}"
        return chat

    def find_by_id(self, id):
        for chat in self.list_chats():
          if chat["id"] == id:
              return self.load_chat(chat_name=chat["name"])
        return None