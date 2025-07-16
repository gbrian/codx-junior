import os
import shutil
import json
import logging
import datetime
from slugify import slugify

from pydantic import BaseModel

from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession
from codx.junior.utils.utils import (
  exec_command,
  extract_blocks,
  remove_starting_block
)

from codx.junior.context import (
    generate_markdown_tree,
)
from tests.db.test_db import settings

from .model import *
from ..ai import AI
from ..events.event_manager import EventManager

logger = logging.getLogger(__name__)

from enum import Enum
class ConfigFiles(Enum):
    CONFIG = 'config.json'
    CATEGORIES = 'categories.json'

    def __repr__(self):
        return self.value
    def __str__(self):
        return self.value

class WikiManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.event_manager = EventManager(codx_path=settings.codx_path)
        self.wiki_path = self.settings.get_project_wiki_path()
        if self.wiki_path:
            self.vitepress_dir = os.path.join(self.wiki_path, '.vitepress')
            self.dist_dir = os.path.join(self.vitepress_dir, 'dist')

            self.initialize_vitepress()

    def send_wiki_event(self, event_type, message):
        self.event_manager.send_notification(**{
          "type": "wiki",
          "event_type": event_type,
          "message": message
        })

    def get_ai(self):
        return AI(settings=self.settings, llm_model=self.settings.get_wiki_model())

    def get_categories(self):
        return ProjectCategories(**self.load_config(ConfigFiles.CATEGORIES, {}))

    def get_config(self):
        return WikiConfig(**self.load_config(ConfigFiles.CONFIG, {}))

    def initialize_vitepress(self):
        """Initialize the VitePress configuration if the wiki path is set."""
        if not self.wiki_path:
            return
        if not os.path.exists(self.vitepress_dir):
            self.create_vitepress_config()

    def load_config(self, config_type: ConfigFiles, default: dict = None) -> dict:
        config_path = os.path.join(self.vitepress_dir, str(config_type))
        try:
            if os.path.isfile(config_path):
                with open(config_path, 'r') as file:
                    return json.load(file)
        except:
            pass
        return default

    def save_config(self, config_type: ConfigFiles, config: dict) -> None:
        config_path = os.path.join(self.vitepress_dir, str(config_type))
        with open(config_path, 'w') as file:
            return json.dump(config, file, indent=2)

    def create_vitepress_config(self):
        """Create the default VitePress configuration and build the wiki."""
        template_dir = os.path.join(os.path.dirname(__file__), 'wiki_template')

        if not os.path.exists(self.vitepress_dir):
            self.send_wiki_event("create_vitepress_config", "Creating wiki structure")
            # Create VitePress directory and copy templates into the wiki path
            os.makedirs(self.vitepress_dir)
            shutil.copytree(template_dir, self.wiki_path, dirs_exist_ok=True)
            self.build_wiki()            

    def rebuild_wiki(self):
        self.send_wiki_event("rebuild_wiki", "Starting to rebuild project wiki")
        if os.path.exists(self.vitepress_dir):
            shutil.rmtree(self.vitepress_dir)
        self.create_vitepress_config()

    def build_wiki(self):
        try:
            self.create_config()
            self.create_wiki_tree()
            self.build_config_sidebar()
            self.build_home()
            self.compile_wiki()
            return self.get_config()
        except Exception as ex:
            self.send_wiki_event("error", f"ERROR: Error creating wiki: {ex}")
        finally:
            self.send_wiki_event(__name__, "Build wiki done")        
            
    def create_config(self):
        """Replace template content in a specified file."""
        self.send_wiki_event(__name__, "Create wiki config")
        config = self.get_config()

        config.project.name = self.settings.project_name
        config.project.description = f"{self.settings.project_name} wiki"
        config.project.icon = self.settings.project_icon

        std, err = exec_command("git config --get remote.origin.url", cwd=self.settings.project_path)
        if std and std.startswith("http"):
            config.project.repository = std

        self.save_config(ConfigFiles.CONFIG, config.model_dump())

    def compile_wiki(self):
        """Execute the wiki build process using a shell command."""
        self.send_wiki_event(__name__, "Compile wiki")
        std, err = exec_command('bash wiki-manager.sh', cwd=self.wiki_path)
        if not os.path.isdir(self.dist_dir):
            raise Exception(f"Error building wiki: {std} - {err}")
        config = self.get_config()
        config.last_update = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        self.save_config(ConfigFiles.CONFIG, config.model_dump())

    def get_sources(self):
        knowledge = self.session.get_knowledge()
        return [source for source in knowledge.get_all_sources() if self.wiki_path not in source]
        
    def create_wiki_tree(self) -> dict:
        """
        Based on project config and project files will return a sidebar definition
        """
        self.send_wiki_event(__name__, "Create wiki tree")
        valid_sources = self.get_sources()
        sources = "\n".join(valid_sources)

        categories = self.get_categories()
        if categories.categories:
            # is_recent = (datetime.datetime.now() - categories.last_update) < datetime.timedelta(hours=1)
            return categories

        side_bar_example = ProjectCategories(
            categories=[
              ProjectCategoryFiles(
                  caregory=f"About {self.settings.project_name}",
                  files=[
                      "/project_path/readme.md",
                      "/project_path/file_with_info_about_the_project.md"
                  ]
              )
            ]
        )

        wiki_profile = self.session.read_profile("wiki").content
        prompt = f"""
        { wiki_profile }
        You must geneate a wiki config json.
        This is the current wiki config json:
        ```json
        { categories.model_dump_json() }
        ``` 

        Analyse the project's files.
        Extract top 5 categories from the files information.
        Classify all files into: 
         * "Welcome" for files talking about the project
         * Use one of the top 5 extracted if the files match the category
         * or "Miscellaneous" one for all other files
        
        Files:
        ```bash
        { sources }
        ```
        
        Generate the sidebar category list like:
        ```json
        { side_bar_example.model_dump_json() }
        ```
        Return the categories where:
         * "category": is the name of the category grouping multiple files
         * "files": Project's files path to gorup under this category
        """
        response = self.get_ai().chat(prompt=prompt)[-1]
        categories = WIKI_CATEGORY_PARSER.invoke(response.content)
        logger.info(f"Wiki project's categories: {categories}")
        self.save_config(ConfigFiles.CATEGORIES, categories.model_dump())

        return categories

    def build_config_sidebar(self):
        self.send_wiki_event(__name__, "Create sidebar")
        
        categories = self.get_categories()
        config = self.get_config()
            
        config.sidebar = []
        for category in categories.categories:
            config.sidebar.append(SidebarSection(
                text=category.category,
                items=[SidebarItem(text=category.category, link=f"/{slugify(category.category)}.md")]
            ))
            self.build_category_file(config=config, category=category)
        
        self.save_config(ConfigFiles.CONFIG, config.model_dump())
        return config

    def build_category_file(self, config: WikiConfig, category:ProjectCategoryFiles):
        self.send_wiki_event(__name__, f"Build category: {category.category}")
        
        category_file = os.path.join(self.wiki_path, f"{slugify(category.category)}.md")
        wiki_profile = self.session.read_profile("wiki").content
        
        for file in category.files:
            if not os.path.isfile(file):
                continue
            exec_command(f"touch {file}")

    def build_file(self, file_path):
        categories = self.get_categories()
        category = [c for c in categories if file_path in c.files][0]
        
        category_file = file_path.split("/")[-1]
        self.send_wiki_event(__name__, f"Processing file: {category_file} ({category.category})")
        
        file_content = f"# {category.category}"
        if os.path.isfile(category_file):
            with open(category_file, 'r') as f:
              file_content = f.read()

        file_changes = ""
        extension = ""
        if "." in category_file:
            extension = category_file.split('.')[-1]
        with open(file_path, 'r') as f:
          file_changes = f.read()
        prompt = f"""
        { wiki_profile }

        Project configuration:
        ```json
        { config.model_dump_json() }
        ```
        Update wiki page with the latest file changes.
        
        ## Current wiki page:
        ```md
        { file_content }
        ```

        ## Latest file changes:
        File: {file}
        ```{extension}
        { file_changes }
        ```

        ## Instructions
        * Use repository url if present for the project files references
        * Wiki page must start with the name of the category in H1
        * Analyze file content and extract useful information for the wiki
        * Generate useful and clear documentation pages based on code changes
        * Do not add any reference to this instruction or conversation
        * Add parts of the file content to enrich documentation
        * Add examples of usage or hints if they are relevant
        * Add mermaid diagrams for complex parts of the documentation
        * Return file content without surronding it by any block decorator like "```"
        """
        response = self.get_ai().chat(prompt=prompt)[-1]
        file_content = remove_starting_block(response.content)
        with open(category_file, 'w') as f:
          f.write(file_content)

    def build_home(self):
        self.send_wiki_event(__name__, "Build home page")
        config = self.get_config()
        home_path = os.path.join(self.wiki_path, "index.md")
        home_content = ""
        with open(home_path, 'r') as f:
            home_content = f.read()

        valid_sources = self.get_sources()
        sources = "\n".join(valid_sources)

        wiki_profile = self.session.read_profile("wiki").content
        prompt = f"""
        { wiki_profile }
        Update wiki home page based on the configuration.
        Update features with the 3 most important categories.

        Project configuration:
        ```json
        { config.model_dump_json() }
        ```

        Project's files:
        ```bash
        { sources }
        ```

        Home page:
        ```md
        { home_content }
        ```

        Respect home page format:
         * Starts with a line "---"
         * Ends with a line "---"
         * Don't add content before the starting "---" or ending "---"
         * Update project info
         * Update the features
         * Keep actions as it is
        """
        response = self.get_ai().chat(prompt=prompt)[-1]
        with open(home_path, 'w') as f:
            f.write(remove_starting_block(response.content))
        

    def process_file_changes(self, new_files, deleted_files):
        """
        Process changes in the project files to reflect those in the wiki.
        
        For every new or modified file, update the wiki. For deleted files, remove the corresponding wiki entry.
        """
        for file_path in new_files:
            self.update_wiki(file_path)
        for file_path in deleted_files:
            self.delete_wiki_file(file_path)

    def update_wiki(self, file_path):
        """
        Generate or update wiki content for a given file path.
        
        This method creates a markdown wiki file corresponding to the file in the wiki directory.
        """
        if not self.wiki_path:
            return
        wiki_content = self.knowledge_wiki.generate_wiki(file_path)
        relative_path = os.path.relpath(file_path, self.settings.project_path)
        wiki_file_path = os.path.join(self.wiki_path, relative_path + '.md')
        wiki_dir = os.path.dirname(wiki_file_path)
        if not os.path.exists(wiki_dir):
            os.makedirs(wiki_dir)
        with open(wiki_file_path, 'w') as file:
            file.write(wiki_content)

    def delete_wiki_file(self, file_path):
        """Delete a markdown wiki file corresponding to the given file path."""
        relative_path = os.path.relpath(file_path, self.settings.project_path)
        wiki_file_path = os.path.join(self.wiki_path, relative_path + '.md')
        if os.path.exists(wiki_file_path):
            os.remove(wiki_file_path)

    def update_vitepress_config(self, new_files, deleted_files):
        """
        Update the VitePress configuration file to add new pages or remove deleted ones.
        
        This modifies the VitePress configuration to ensure navigation reflects the current state.        
        """
        config_path = os.path.join(self.wiki_path, '.vitepress', 'config.json')
        consfig = {}
        with open(config_path, 'r') as file:
            config = json.loads(file.read())
        for file_path in new_files:
            relative_path = os.path.relpath(file_path, self.settings.project_path)
            config += f'\n  .pages.push("/{relative_path}.md");'
        for file_path in deleted_files:
            relative_path = os.path.relpath(file_path, self.settings.project_path)
            config = config.replace(f'"/{relative_path}.md"', '')
        with open(config_path, 'w') as file:
            file.write(config)

    def handle_project_changes(self, new_files, deleted_files):
        """
        Handle changes in project files by updating the wiki and Vitepress configuration.
        
        This method ensures that any addition or deletion in project files is mirrored in the wiki setup.
        """
        self.process_file_changes(new_files, deleted_files)
        self.update_vitepress_config(new_files, deleted_files)

    def update_wiki_tree(self):
        """
        Update the wiki structure based on the current project file structure.
        
        This method reads the existing wiki tree, scans the project directory (excluding the wiki path),
        and uses that information to update the wiki tree to reflect any structural changes.
        """
        # Initialize paths
        wiki_tree_path = os.path.join(self.wiki_path, 'wiki_tree.json')
        project_root_path = self.settings.project_path

        # Load existing wiki tree if available
        if os.path.exists(wiki_tree_path):
            with open(wiki_tree_path, 'r') as file:
                wiki_tree = json.load(file)
        else:
            wiki_tree = {}

        # Extract folder structure from the project directory
        folder_structure = self._get_folder_structure(project_root_path)

        # Use AI or rules to update the wiki tree based on folder structure
        updated_wiki_tree = self._generate_wiki_tree(folder_structure, wiki_tree)

        # Save the updated wiki tree
        with open(wiki_tree_path, 'w') as file:
            json.dump(updated_wiki_tree, file, indent=4)

    def _get_folder_structure(self, root_folder):
        """
        Recursively get the folder structure of the given root folder, ignoring the wiki path.
        
        Returns a list of relative paths for each folder.
        """
        folder_structure = []
        for root, dirs, files in os.walk(root_folder):
            # Ignore the wiki path
            if root.startswith(self.wiki_path):
                continue
            
            relative_root = os.path.relpath(root, root_folder)
            folder_structure.append(relative_root)

        return folder_structure

    def _generate_wiki_tree(self, folder_structure, current_wiki_tree):
        """
        Generate an updated wiki tree based on the current folder structure and existing wiki tree.
        
        This function currently follows a simple rule: it updates the tree with new entries and respects
        the 3-level depth constraint.
        """
        updated_tree = current_wiki_tree  # Start with the current tree

        # Update the tree structure, respecting the 3-level depth constraint
        for folder in folder_structure:
            parts = folder.split(os.sep)
            if len(parts) <= 3:
                subtree = updated_tree
                for part in parts:
                    subtree = subtree.setdefault(part, {})
        
        return updated_tree

