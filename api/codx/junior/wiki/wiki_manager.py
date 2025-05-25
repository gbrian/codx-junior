import os
import shutil
import json
import logging

from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import Knowledge, ProfileManager
from codx.junior.utils import exec_command

logger = logging.getLogger(__name__)
class WikiManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.wiki_path = self.settings.get_project_wiki_path()
        self.vitepress_dir = os.path.join(self.wiki_path, '.vitepress')
        self.dist_dir = os.path.join(self.vitepress_dir, 'dist')
        self.initialize_vitepress()

    def initialize_vitepress(self):
        if not self.wiki_path:
            return
        if not os.path.exists(self.vitepress_dir):
            self.create_vitepress_config()

    def create_vitepress_config(self):
        index_path = os.path.join(self.wiki_path, 'index.md')
        config_path = os.path.join(self.vitepress_dir, 'config.mts')
        template_dir = os.path.join(os.path.dirname(__file__), 'wiki_template')

        if not os.path.exists(self.vitepress_dir):
            os.makedirs(self.vitepress_dir)
            shutil.copytree(template_dir, self.wiki_path, dirs_exist_ok=True)
            self.replace_template_content_file(config_path)
            self.replace_template_content_file(index_path)
                
            
            self.build_wiki()

    def replace_template_content_file(self, path):
        template_content = ""
        with open(path, 'r') as f:
            template_content = self.replace_template_content(f.read())
        with open(path, 'w') as f:
            f.write(template_content)

    def replace_template_content(self, template_content):
        template_content = template_content.replace("PROJECT_NAME", self.settings.project_name)
        template_content = template_content.replace("PROJECT_DESCRIPTION", f"{self.settings.project_name} wiki")
        template_content = template_content.replace("PROJECT_ICON", self.settings.project_icon)
        return template_content
            
    def build_wiki(self):
        std, err = exec_command('bash wiki-manager.sh', cwd=self.wiki_path)
        if not os.path.isdir(self.dist_dir):
            raise Exception(f"Error building wiki: {std} - {err}")

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
