import json
import logging
import sqlite3
from slugify import slugify
from codx.junior.settings import CODXJuniorSettings

from codx.junior.utils.utils import write_file

logger = logging.getLogger(__name__)

class KnowledgeKeywords:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.path = self.settings.project_path
        self.index_name = slugify(str(self.path))
        self.db_path = f"{settings.codx_path}/db/{self.index_name}"
        self.db_keywords_file = f"{self.db_path}/keywords.json"
        
    def get_keywords(self, query: str = None):
        def load():
            try:
                with open(self.db_keywords_file) as f:
                    return json.loads(f.read())
            except:
                pass
            return {}
        keywords = load()
        if query:
            query = query.lower()
            filtered = {}
            for key, value in keywords.items():
                matches = [val for val in value if query in val.lower()]
                if matches:
                    filtered[key] = matches 
            keywords = filtered
        return keywords

    def add_keywords(self, file_path, file_keywords):
        keywords = self.get_keywords()
        keywords[file_path] = [word.strip() for word in file_keywords.split(",")]
        write_file(self.db_keywords_file, json.dumps(keywords, indent=2))

    def remove_keywords(self, file_path):
        keywords = self.get_keywords()
        if file_path in keywords:
            del keywords[file_path]
            write_file(self.db_keywords_file, json.dumps(keywords, indent=2))