import logging
import json
from datetime import datetime

from codx.junior.knowledge.knowledge_db import KnowledgeDB

from concurrent.futures import ThreadPoolExecutor, as_completed

from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

class KnowledgeWiki:
    db: KnowledgeDB
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings

    def get_db(self):
        if not self.db:
          self.db = KnowledgeDB(settings=self.settings)
        return self.db