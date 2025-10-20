from collections import defaultdict
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatHeatmapReport:
    def __init__(self):
        pass

    def generate_report(self, chats):
        # Dictionary to hold counts for each time interval
        heatmap = defaultdict(int)
        
        for chat in chats:
            # Process chat timestamps
            self.process_datetime(chat.created_at, heatmap, "chat created_at")
            self.process_datetime(chat.updated_at, heatmap, "chat updated_at")
            
            # Process each message in the chat
            for message in chat.messages:
                self.process_datetime(message.created_at, heatmap, "message created_at")
        
        return heatmap

    def process_datetime(self, datetime_str, heatmap, context):
        try:
            # Convert string to datetime object
            dt = datetime.fromisoformat(datetime_str)
            
            # Group by year, month, day, and hour
            time_key = f"{dt.year}-{dt.month}-{dt.day}"
            
            # Increment the count for this time interval
            heatmap[time_key] += 1
            #logger.debug(f"Processed {context} for time key {time_key}")
        except Exception as e:
            logger.error(f"Error processing datetime {datetime_str} for {context}: {e}")

