from collections import defaultdict
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatWallReport:
    def __init__(self):
        pass

    def generate_report(self, chats):
        # List to hold chats with their last message within the last 3 days
        recent_chats = []
        
        # Calculate the cutoff datetime for 3 days ago
        three_days_ago = datetime.now() - timedelta(days=3)
        
        logger.info(f"Total chats retrieved: {len(chats)}")
        
        for chat in chats:
            # Filter messages from the last 3 days
            recent_messages = [msg for msg in chat.messages if datetime.fromisoformat(msg.created_at) >= three_days_ago]
            
            if recent_messages:
                # Sort messages by creation time and take the last message
                recent_messages.sort(key=lambda msg: datetime.fromisoformat(msg.created_at))
                last_message = recent_messages[-1]
                
                # Add chat with the last message to the list
                chat.messages = [last_message]
                recent_chats.append(chat)
        
        # Sort chats by the last message creation time
        recent_chats.sort(key=lambda chat: datetime.fromisoformat(chat.messages[0].created_at))
        
        return recent_chats
