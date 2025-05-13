import os
import shutil
import json
from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_wiki import KnowledgeWiki
from codx.junior.engine import Knowledge, ProfileManager
from codx.junior.background import check_file_worker
from codx.junior.utils import exec_command, find_project_from_file_path, find_all_projects
from codx.junior.chat import ChatManager
from codx.junior.ai import AICodeGenerator
from codx.junior.logger import logger
from threading import Thread


class WikiManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.wiki_path = self.settings.get_project_wiki_path()
        self.initialize_vitepress()
        self.knowledge_wiki = KnowledgeWiki(settings=settings)

    def initialize_vitepress(self):
        if not self.wiki_path:
            return
        if not os.path.exists(self.wiki_path):
            os.makedirs(self.wiki_path)
            self.create_vitepress_config()

    def create_vitepress_config(self):
        vitepress_dir = os.path.join(self.wiki_path, '.vitepress')
        config_path = os.path.join(vitepress_dir, 'config.js')
        template_dir = os.path.join(os.path.dirname(__file__), 'wiki_template')

        if not os.path.exists(vitepress_dir):
            os.makedirs(vitepress_dir)
            shutil.copytree(template_dir, vitepress_dir, dirs_exist_ok=True)
            config_content = None
            with open(config_path, 'r') as f:
                config_content = f.read()
            config_content.replace("PROJECT_NAME", self.settings.project_name)
            config_content.replace("PROJECT_DESCRIPTION", f"{self.settings.project_name} wiki")
            with open(config_path, 'w') as f:
                f.write(config_content)
            

    def update_wiki(self, file_path):
        if not self.wiki_path:
            return
        wiki_content = self.knowledge_wiki.generate_wiki(file_path)
        relative_path = os.path.relpath(file_path, self.settings.project_path)
        wiki_file_path = os.path.join(self.wiki_path, relative_path + '.md')
        wiki_dir = os.path.dirname(wiki_file_path)
        if not os.path.exists(wiki_dir):
            os.makedirs(wiki_dir)
        with open(wiki_file_path, 'w') as f:
            f.write(wiki_content)

    def process_file_changes(self, new_files, deleted_files):
        for file_path in new_files:
            self.update_wiki(file_path)
        for file_path in deleted_files:
            self.delete_wiki_file(file_path)

    def delete_wiki_file(self, file_path):
        relative_path = os.path.relpath(file_path, self.settings.project_path)
        wiki_file_path = os.path.join(self.wiki_path, relative_path + '.md')
        if os.path.exists(wiki_file_path):
            os.remove(wiki_file_path)

    def update_vitepress_config(self, new_files, deleted_files):
        config_path = os.path.join(self.wiki_path, '.vitepress', 'config.js')
        with open(config_path, 'r') as f:
            config = f.read()
        for file_path in new_files:
            relative_path = os.path.relpath(file_path, self.settings.project_path)
            config += f'\n  .pages.push("/{relative_path}.md");'
        for file_path in deleted_files:
            relative_path = os.path.relpath(file_path, self.settings.project_path)
            config = config.replace(f'"/{relative_path}.md"', '')
        with open(config_path, 'w') as f:
            f.write(config)

    def handle_project_changes(self, new_files, deleted_files):
        self.process_file_changes(new_files, deleted_files)
        self.update_vitepress_config(new_files, deleted_files)
