import os
import shutil
import json
import logging
import datetime
from enum import Enum
from typing import List, Dict, Tuple, Any

from slugify import slugify
from pydantic import BaseModel

from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession
from codx.junior.utils.utils import exec_command, extract_blocks, remove_starting_block
from codx.junior.context import generate_markdown_tree
from .model import *
from ..ai import AI
from ..events.event_manager import EventManager

logger = logging.getLogger(__name__)

class ConfigFiles(Enum):
    """Enum for different configuration files."""
    CONFIG = 'config.json'
    CATEGORIES = 'categories.json'

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value

class WikiManager:
    """Manager class to handle operations for generating and maintaining a project wiki."""
    
    def __init__(self, settings: CODXJuniorSettings) -> None:
        self.settings: CODXJuniorSettings = settings
        self.event_manager = EventManager(codx_path=settings.codx_path)
        self.wiki_path: str = self.settings.get_project_wiki_path()
        self.vitepress_dir: str = ''
        self.dist_dir: str = ''
        
        if self.wiki_path:
            self.vitepress_dir = os.path.join(self.wiki_path, '.vitepress')
            self.dist_dir = os.path.join(self.vitepress_dir, 'dist')
            self.initialize_vitepress()

    def send_wiki_event(self, event_type: str, message: str) -> None:
        """Send wiki-related notification events to the Event Manager."""
        logger.debug("Sending wiki event with type: %s and message: %s", event_type, message)
        self.event_manager.send_notification(type="wiki", event_type=event_type, message=message)

    def get_ai(self) -> AI:
        """Create and return an AI engine instance for processing."""
        return AI(settings=self.settings, llm_model=self.settings.get_wiki_model())

    def get_categories(self) -> ProjectCategories:
        """Load project categories from the configuration file."""
        return ProjectCategories(**self.load_config(ConfigFiles.CATEGORIES, {}))

    def get_config(self) -> WikiConfig:
        """Load the main wiki configuration from the configuration file."""
        return WikiConfig(**self.load_config(ConfigFiles.CONFIG, {}))

    def initialize_vitepress(self) -> None:
        """Initialize the VitePress configuration if the wiki path is set."""
        if not os.path.exists(self.vitepress_dir):
            self.create_vitepress_config()

    def load_config(self, config_type: ConfigFiles, default: Dict = None) -> Dict:
        """Load configuration file of the given type."""
        if default is None:
            default = {}
        
        config_path = os.path.join(self.vitepress_dir, str(config_type))
        try:
            if os.path.isfile(config_path):
                with open(config_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
        except json.JSONDecodeError as e:
            logger.error("Error loading configuration file %s: %s", config_path, e)
        return default

    def save_config(self, config_type: ConfigFiles, config: Dict) -> None:
        """Save the given configuration dictionary to a file of the given type."""
        config_path = os.path.join(self.vitepress_dir, str(config_type))
        with open(config_path, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=2)

    def create_vitepress_config(self):
        """Create the default VitePress configuration and build the wiki."""
        template_dir = os.path.join(os.path.dirname(__file__), 'wiki_template')

        if not os.path.exists(self.vitepress_dir):
            self.send_wiki_event("create_vitepress_config", "Creating wiki structure")
            os.makedirs(self.vitepress_dir)
            shutil.copytree(template_dir, self.wiki_path, dirs_exist_ok=True)
            self.build_wiki()

    def rebuild_wiki(self):
        """Recreate the VitePress configurations and rebuild wiki pages."""
        self.send_wiki_event("rebuild_wiki", "Starting to rebuild project wiki")
        if os.path.exists(self.vitepress_dir):
            shutil.rmtree(self.vitepress_dir)
        self.create_vitepress_config()

    def build_wiki(self) -> WikiConfig:
        """Build and compile the wiki."""
        try:
            self.create_config()
            self.create_wiki_tree()
            self.build_config_sidebar()
            self.build_home()
            self.compile_wiki()
            return self.get_config()
        except Exception as ex:
            self.send_wiki_event("error", "ERROR: Error creating wiki: %s" % ex)
        finally:
            self.send_wiki_event(__name__, "Build wiki done")

    def create_config(self) -> None:
        """Replace and set project details in the configuration."""
        self.send_wiki_event(__name__, "Create wiki config")
        config = self.get_config()

        config.project.name = self.settings.project_name
        config.project.description = f"{self.settings.project_name} wiki"
        config.project.icon = self.settings.project_icon

        try:
            std, err = exec_command("git config --get remote.origin.url", cwd=self.settings.project_path)
            if std and std.startswith("http"):
                config.project.repository = std
        except Exception as ex:
            logger.warning("Error fetching repository URL: %s", ex)

        self.save_config(ConfigFiles.CONFIG, config.model_dump())

    def compile_wiki(self) -> None:
        """Execute the wiki build process using a shell command."""
        self.send_wiki_event(__name__, "Compile wiki")
        std, err = exec_command('bash wiki-manager.sh', cwd=self.wiki_path)
        
        if not os.path.isdir(self.dist_dir):
            raise RuntimeError("Error building wiki: %s - %s" % (std, err))
        
        config = self.get_config()
        config.last_update = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        self.save_config(ConfigFiles.CONFIG, config.model_dump())

    def get_sources(self) -> List[str]:
        """Retrieve a list of project knowledge sources."""
        return [source for source in self.session.get_knowledge().get_all_sources() if self.wiki_path not in source]
        
    def create_wiki_tree(self) -> ProjectCategories:
        """Create a hierarchical tree of the wiki structure based on project content."""
        self.send_wiki_event(__name__, "Create wiki tree")
        valid_sources = self.get_sources()
        sources = "\n".join(valid_sources)

        categories = self.get_categories()
        if categories.categories:
            return categories

        wiki_profile = self.session.read_profile("wiki").content
        side_bar_example = ProjectCategories(
            categories=[
                ProjectCategoryFiles(
                    category=f"About {self.settings.project_name}",
                    files=[
                        "/project_path/readme.md",
                        "/project_path/file_with_info_about_the_project.md"
                    ]
                )
            ]
        )

        prompt = self._generate_prompt_from_sources(wiki_profile, sources, categories, side_bar_example)

        response = self.get_ai().chat(prompt=prompt)[-1]
        categories = WIKI_CATEGORY_PARSER.invoke(response.content)
        logger.info("Wiki project's categories: %s", categories)
        self.save_config(ConfigFiles.CATEGORIES, categories.model_dump())

        return categories

    def _generate_prompt_from_sources(
        self, 
        wiki_profile: str, 
        sources: str, 
        categories: ProjectCategories, 
        side_bar_example: ProjectCategories
    ) -> str:
        """Generate AI prompt to derive categories from sources."""
        return f"""
        {wiki_profile}
        You must generate a wiki config json.
        This is the current wiki config json:
        ```json
        {categories.model_dump_json()}
        ``` 

        Analyze the project's files.
        Extract top 5 categories from the files information.
        Classify all files into: 
         * "Welcome" for files talking about the project
         * Use one of the top 5 extracted if the files match the category
         * or "Miscellaneous" one for all other files

        Files:
        ```bash
        {sources}
        ```

        Generate the sidebar category list like:
        ```json
        {side_bar_example.model_dump_json()}
        ```
        Return the categories where:
         * "category": is the name of the category grouping multiple files
         * "files": Project's files path to group under this category
        """

    def build_config_sidebar(self) -> WikiConfig:
        """Build and update the sidebar configuration."""
        self.send_wiki_event(__name__, "Create sidebar")
        
        categories = self.get_categories()
        config = self.get_config()

        config.sidebar = [
            SidebarSection(
                text=category.category,
                items=[SidebarItem(text=category.category, link=f"/{slugify(category.category)}.md")]
            )
            for category in categories.categories
        ]

        for category in categories.categories:
            self.build_category_file(config=config, category=category)
        
        self.save_config(ConfigFiles.CONFIG, config.model_dump())
        return config

    def build_category_file(self, config: WikiConfig, category: ProjectCategoryFiles) -> None:
        """Build a markdown file for each category."""
        self.send_wiki_event(__name__, f"Build category: {category.category}")
        
        category_file_path = os.path.join(self.wiki_path, f"{slugify(category.category)}.md")
        wiki_profile = self.session.read_profile("wiki").content

        # Create files in the category.
        for file in category.files:
            if not os.path.isfile(file):
                continue
            _output, _err = exec_command(f"touch {file}")

    def build_file(self, file_path: str) -> None:
        """Build a specific markdown file for the wiki."""
        categories = self.get_categories()
        matching_category = next((c for c in categories.categories if file_path in c.files), None)
        
        if not matching_category:
            logger.warning("No matching category for file: %s", file_path)
            return
        
        category_file = file_path.split("/")[-1]
        self.send_wiki_event(__name__, f"Processing file: {category_file} ({matching_category.category})")

        file_content = self._read_existing_file_content(category_file)
        file_changes, extension = self._read_file_changes(file_path)

        response = self._update_wiki_content(file_content, file_changes, extension, matching_category)
        updated_content = remove_starting_block(response.content)

        self._write_to_file(os.path.join(self.wiki_path, f"{slugify(matching_category.category)}.md"), updated_content)

    def _read_existing_file_content(self, category_file: str) -> str:
        """Read content from the existing wiki file, if it exists."""
        if os.path.isfile(category_file):
            with open(category_file, 'r', encoding='utf-8') as f:
                return f.read()
        return f"# {category_file.split('/')[-1]}"

    def _read_file_changes(self, file_path: str) -> Tuple[str, str]:
        """Read the latest file changes and determine the file extension."""
        with open(file_path, 'r', encoding='utf-8') as f:
            file_changes = f.read()
        
        extension = file_path.split('.')[-1] if '.' in file_path else ''
        return file_changes, extension

    def _update_wiki_content(self, file_content: str, file_changes: str, extension: str, category: ProjectCategoryFiles) -> Any:
        """Generate updated content for the wiki file based on the latest changes."""
        wiki_profile = self.session.read_profile("wiki").content
        config = self.get_config()

        prompt = f"""
        {wiki_profile}

        Project configuration:
        ```json
        {config.model_dump_json()}
        ```
        Update wiki page with the latest file changes.

        ## Current wiki page:
        ```md
        {file_content}
        ```

        ## Latest file changes:
        File: {category.category}
        ```{extension}
        {file_changes}
        ```

        ## Instructions
        * Use repository URL if present for the project files references
        * Wiki page must start with the name of the category in H1
        * Analyze file content and extract useful information for the wiki
        * Generate useful and clear documentation pages based on code changes
        * Do not add any reference to this instruction or conversation
        * Add parts of the file content to enrich documentation
        * Add examples of usage or hints if they are relevant
        * Add mermaid diagrams for complex parts of the documentation
        * Return file content without surrounding it with any block decorator like "```"
        """
        return self.get_ai().chat(prompt=prompt)[-1]

    def _write_to_file(self, file_path: str, content: str) -> None:
        """Write content to a file, ensuring any existing content is overwritten."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def build_home(self) -> None:
        """Construct or update the home page for the wiki."""
        self.send_wiki_event(__name__, "Build home page")
        config = self.get_config()
        
        home_path = os.path.join(self.wiki_path, "index.md")
        with open(home_path, 'r', encoding='utf-8') as f:
            home_content = f.read()

        valid_sources = self.get_sources()
        sources = "\n".join(valid_sources)

        wiki_profile = self.session.read_profile("wiki").content
        prompt = self._generate_home_page_prompt(wiki_profile, config, sources, home_content)

        response = self.get_ai().chat(prompt=prompt)[-1]
        self._write_to_file(home_path, remove_starting_block(response.content))

    def _generate_home_page_prompt(self, wiki_profile: str, config: WikiConfig, sources: str, home_content: str) -> str:
        """Generate a prompt for updating the wiki's home page."""
        return f"""
        {wiki_profile}
        Update wiki home page based on the configuration.
        Update features with the 3 most important categories.

        Project configuration:
        ```json
        {config.model_dump_json()}
        ```

        Project's files:
        ```bash
        {sources}
        ```

        Home page:
        ```md
        {home_content}
        ```

        Respect home page format:
         * Starts with a line "---"
         * Ends with a line "---"
         * Don't add content before the starting "---" or ending "---"
         * Update project info
         * Update the features
         * Keep actions as it is
        """

    def process_file_changes(self, new_files: List[str], deleted_files: List[str]) -> None:
        """Process updates and deletions in project files, updating the wiki accordingly."""
        for file_path in new_files:
            self.update_wiki(file_path)
        for file_path in deleted_files:
            self.delete_wiki_file(file_path)

    def update_wiki(self, file_path: str) -> None:
        """Update or create wiki content for an individual file."""
        if not self.wiki_path:
            return
        wiki_content = self.knowledge_wiki.generate_wiki(file_path)
        self._write_wiki_file(file_path, wiki_content)

    def _write_wiki_file(self, file_path: str, content: str) -> None:
        """Write wiki content to a corresponding markdown file."""
        relative_path = os.path.relpath(file_path, self.settings.project_path)
        wiki_file_path = os.path.join(self.wiki_path, relative_path + '.md')
        
        wiki_dir = os.path.dirname(wiki_file_path)
        if not os.path.exists(wiki_dir):
            os.makedirs(wiki_dir)
        
        with open(wiki_file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def delete_wiki_file(self, file_path: str) -> None:
        """Delete markdown wiki file linked to the given project file."""
        relative_path = os.path.relpath(file_path, self.settings.project_path)
        wiki_file_path = os.path.join(self.wiki_path, relative_path + '.md')

        if os.path.exists(wiki_file_path):
            os.remove(wiki_file_path)

    def update_vitepress_config(self, new_files: List[str], deleted_files: List[str]) -> None:
        """Update the VitePress configuration to reflect new and deleted files."""
        config_path = os.path.join(self.wiki_path, '.vitepress', 'config.json')
        
        with open(config_path, 'r', encoding='utf-8') as file:
            config_lines = file.readlines()

        config_lines = self._update_config_with_files(config_lines, new_files, deleted_files)

        with open(config_path, 'w', encoding='utf-8') as file:
            file.writelines(config_lines)

    def _update_config_with_files(self, config_lines: List[str], new_files: List[str], deleted_files: List[str]) -> List[str]:
        """Update configuration lines with new and deleted files."""
        for file_path in new_files:
            relative_path = os.path.relpath(file_path, self.settings.project_path)
            config_lines.append(f'.pages.push("/{relative_path}.md");\n')

        for file_path in deleted_files:
            relative_path = os.path.relpath(file_path, self.settings.project_path)
            pattern = f'"/{relative_path}.md"'
            config_lines = [line for line in config_lines if pattern not in line]

        return config_lines

    def handle_project_changes(self, new_files: List[str], deleted_files: List[str]) -> None:
        """Handle updates to project files and reflect these in the wiki and configurations."""
        self.process_file_changes(new_files, deleted_files)
        self.update_vitepress_config(new_files, deleted_files)

    def update_wiki_tree(self) -> None:
        """Synchronize the wiki structure with the current project file organization."""
        wiki_tree_path = os.path.join(self.wiki_path, 'wiki_tree.json')
        project_root_path = self.settings.project_path

        current_wiki_tree = self._load_wiki_tree(wiki_tree_path)

        folder_structure = self._get_folder_structure(project_root_path)
        updated_wiki_tree = self._generate_wiki_tree(folder_structure, current_wiki_tree)

        with open(wiki_tree_path, 'w', encoding='utf-8') as file:
            json.dump(updated_wiki_tree, file, indent=4)

    def _load_wiki_tree(self, wiki_tree_path: str) -> Dict:
        """Load existing wiki tree from a file."""
        if os.path.exists(wiki_tree_path):
            with open(wiki_tree_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        return {}

    def _get_folder_structure(self, root_folder: str) -> List[str]:
        """Gather the folder structure starting from a root folder, excluding the wiki path."""
        return [
            os.path.relpath(root, root_folder)
            for root, _, _ in os.walk(root_folder)
            if not root.startswith(self.wiki_path)
        ]

    def _generate_wiki_tree(self, folder_structure: List[str], current_wiki_tree: Dict) -> Dict:
        """Generate a wiki tree structure based on the current folder setup."""
        updated_tree = current_wiki_tree

        for folder in folder_structure:
            parts = folder.split(os.sep)
            if len(parts) <= 3:
                subtree = updated_tree
                for part in parts:
                    subtree = subtree.setdefault(part, {})

        return updated_tree
