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

    def check_files(self):
        """
        Retrieve and filter files modified in the last 30 minutes that need to be processed for wiki updates.
        """
        db = self.get_db()
        all_files = db.get_all_files()
        target_files = []

        # Current time in seconds
        current_time = datetime.now().timestamp()

        for file_path, file_info in all_files.items():
            # Get last modified time of the file in seconds
            file_mod_time = os.path.getmtime(file_path)

            # Check if file was modified in the last 30 minutes (30 * 60 seconds)
            if current_time - file_mod_time < 1800:
                # Check if file needs wiki update
                wiki_update_time = datetime.strptime(file_info.get("wiki_update", "01/01/1970T00:00:00"), "%m/%d/%YT%H:%M:%S").timestamp()
                if wiki_update_time < file_mod_time:
                    target_files.append(file_path)

        return target_files

    def process_file(self, file_path):
        """
        Generate wiki documentation for a specified file.
        """
        # Assuming we have a method like `generate_wiki` defined elsewhere
        try:
            logger.info(f"Processing file for wiki update: {file_path}")
            generate_wiki(file_path)
            logger.info(f"Wiki documentation generated successfully for: {file_path}")
        except Exception as e:
            logger.error(f"Failed to generate wiki for {file_path}: {e}")

    def generate_wiki(file_path):
        """
        Function that generates the wiki documentation for a given file.
        Implementation needed based on project specifics.
        """
        # Hypothetical implementation
        # This should be replaced with the actual logic to generate wiki from the file.
        logger.info(f"Generating wiki for {file_path}")
        pass