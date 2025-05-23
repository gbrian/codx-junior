# [[{"id": "363a02c2-5f62-4bde-bf0d-2b4aa04f16a1", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "profiles": ["software_developer"], "users": [], "name": "Error parsing chats", "created_at": "2025-05-19 11:23:08.461860", "updated_at": "2025-05-19T11:40:03.605119", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Bugs", "column": "In Development", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/api/.codx/tasks/Bugs/In Development/error-parsing-chats.363a02c2-5f62-4bde-bf0d-2b4aa04f16a1.md", "model": "", "visibility": ""}]]
## [[{"doc_id": "68e52632-b774-4e47-88ce-e2983db651f6", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-19 11:23:08.460248", "updated_at": "2025-05-19 11:23:08.460285", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin"}]]
This method is creating a chat from the file content:
```py

    @profile_function
    def deserialize_chat(self, content) -> Chat:
        logger.info(f"deserialize_chat content length: {len(content)}")
        lines = content.split("\n")
        
        chat_json = json.loads(lines[0][4:-2])
        logger.info("deserialize_chat chat_json")
        
        chat = Chat(**chat_json)
        chat.messages = []
        chat_message = None
        logger.info(f"deserialize_chat lines {len(lines[1:])}")
        
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
```

When there're many messages, content is too big, we need to:
 * Only serialize those not set to "hide"
 * Serilize only last 3 messages

Probably we must find all messages headers and serialize the settings then count the message content lines and decide if we are 
going to add to the resulting chat
## [[{"doc_id": "5059931b-7e70-4818-9bdc-7cdc9ebbd092", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-19 11:33:17.385355", "updated_at": "2025-05-19 11:33:17.385412", "images": [], "files": ["/codx/junior/chat_manager.py", "/codx/junior/app.py"], "meta_data": {"time_taken": 52.548826456069946, "first_chunk_time_taken": 45.702595949172974, "model": "gpt-4o"}, "profiles": ["software_developer"], "user": null}]]
To modify the `deserialize_chat` method to only include messages that are not set to "hide" and to serialize only the last three messages, you'll need to adjust the loop that processes each line of the chat content. Below is an example implementation that achieves this:

```python
from collections import deque

@profile_function
def deserialize_chat(self, content) -> Chat:
    logger.info(f"deserialize_chat content length: {len(content)}")
    lines = content.split("\n")
    
    chat_json = json.loads(lines[0][4:-2])
    logger.info("deserialize_chat chat_json")
    
    chat = Chat(**chat_json)
    chat.messages = []
    chat_message = None
    logger.info(f"deserialize_chat lines {len(lines[1:])}")
    
    # Use a deque to keep track of the last three messages
    last_three_messages = deque(maxlen=3)
    
    for line in lines[1:]:
        if line.startswith("## [[{") and line.endswith("}]]"):
            message_data = json.loads(line[5:-2])
            if message_data.get("hide", False):
                continue
                
            chat_message = Message(**message_data)
            chat_message.content = ""
            
            # Only keep last 3 messages
            last_three_messages.append(chat_message)
            continue
        
        if chat_message:
            chat_message.content = line if not chat_message.content else f"{chat_message.content}\n{line}"

    # Set the messages for the chat
    chat.messages = list(last_three_messages)
    return chat
```

### Explanation:

1. **Using a Deque**: A `deque` (double-ended queue) is used to maintain only the last three messages, automatically discarding the oldest message when a new one is appended.

2. **Filtering Messages**: When a message is parsed, it's checked for a `"hide"` flag. If this flag is `True`, the message is skipped.

3. **Appending to Deque**: When a message is not hidden, it is added to the `last_three_messages` deque. This ensures that only the last three messages will be retained.

4. **Chat Messages Assignment**: After processing all lines, the chat's `messages` attribute is set with the messages stored in the deque.