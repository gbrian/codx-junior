import os

from codx.junior.settings import CODXJuniorSettings

class WikiManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings

    def update_wiki(self, file_path):
        
