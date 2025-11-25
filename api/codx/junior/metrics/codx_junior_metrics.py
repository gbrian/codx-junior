import logging

from datetime import datetime, timedelta

from codx.junior.chat_manager import ChatManager

from .chat_heatmap import ChatHeatmapReport
from .chat_wall import ChatWallReport

logger = logging.getLogger(__name__)

class CODXJuniorMetrics:
    def __init__(self, settings):
        self.settings = settings

    def project_metrics(self):
      try:
          chat_manager = ChatManager(settings=self.settings)
          chats = chat_manager.list_chats()
          last_update = datetime.today() - timedelta(days=5)
          last_chats = chat_manager.find_chats(last_update)
          chat_heatmap = ChatHeatmapReport()
          chat_wall = ChatWallReport()
          return {
            "heatmap": chat_heatmap.generate_report(chats=chats),
            "wall": chat_wall.generate_report(chats=last_chats),
          }
      except Exception as ex:
          logger.error("Error getting heatmapo metrics: %s", str(ex))
          return {
            "error": str(ex)
          }
