import json
import logging
import sqlite3
from slugify import slugify
from gpt_engineer.core.settings import GPTEngineerSettings


logger = logging.getLogger(__name__)

class KnowledgeKeywords:
    def __init__(self, settings: GPTEngineerSettings):
        self.settings = settings
        self.path = self.settings.project_path
        self.index_name = slugify(str(self.path))
        self.db_path = f"{settings.gpteng_path}/db/{self.index_name}"
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
        with open(self.db_keywords_file, 'w') as f:
            f.write(json.dumps(keywords, indent=2))

    def remove_keywords(self, file_path):
        keywords = self.get_keywords()
        if file_path in keywords:
            del keywords[file_path]
            with open(self.db_keywords_file, 'w') as f:
                f.write(json.dumps(keywords, indent=2))