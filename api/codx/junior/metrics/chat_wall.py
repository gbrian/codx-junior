import logging

from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatWallReport:
    def __init__(self):
        pass

    def generate_report(self, chats):
        # List to hold chats with their last message within the last 3 days
        recent_chats = []
        
        for chat in chats:
            # Add chat with the last message to the list
            visible_messages = [m for m in chat.messages if not m.hide]
            if visible_messages:
                chat.messages = [visible_messages[-1]]
                recent_chats.append(chat)
        
        # Sort chats by the last message creation time
        recent_chats.sort(key=lambda chat: datetime.fromisoformat(chat.updated_at), reverse=True)
        
        return recent_chats
