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
        """Initialize the VitePress configuration if the wiki path is set."""
        if not self.wiki_path:
            return
        if not os.path.exists(self.vitepress_dir):
            self.create_vitepress_config()

    def create_vitepress_config(self):
        """Create the default VitePress configuration and build the wiki."""
        index_path = os.path.join(self.wiki_path, 'index.md')
        config_path = os.path.join(self.vitepress_dir, 'config.mts')
        template_dir = os.path.join(os.path.dirname(__file__), 'wiki_template')

        if not os.path.exists(self.vitepress_dir):
            # Create VitePress directory and copy templates into the wiki path
            os.makedirs(self.vitepress_dir)
            shutil.copytree(template_dir, self.wiki_path, dirs_exist_ok=True)
            self.replace_template_content_file(config_path)
            self.replace_template_content_file(index_path)
            
            # Build the wiki once configuration is set
            self.build_wiki()

    def replace_template_content_file(self, path):
        """Replace template content in a specified file."""
        template_content = ""
        with open(path, 'r') as file:
            template_content = self.replace_template_content(file.read())
        with open(path, 'w') as file:
            file.write(template_content)

    def replace_template_content(self, template_content):
        """
        Replace placeholders in the template content with the project's specific details.
        
        This includes replacing project name, description, and icon.
        """
        template_content = template_content.replace("PROJECT_NAME", self.settings.project_name)
        template_content = template_content.replace("PROJECT_DESCRIPTION", f"{self.settings.project_name} wiki")
        template_content = template_content.replace("PROJECT_ICON", self.settings.project_icon)
        return template_content
            
    def build_wiki(self):
        """Execute the wiki build process using a shell command."""
        std, err = exec_command('bash wiki-manager.sh', cwd=self.wiki_path)
        if not os.path.isdir(self.dist_dir):
            raise Exception(f"Error building wiki: {std} - {err}")

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

    def process_file_changes(self, new_files, deleted_files):
        """
        Process changes in the project files to reflect those in the wiki.
        
        For every new or modified file, update the wiki. For deleted files, remove the corresponding wiki entry.
        """
        for file_path in new_files:
            self.update_wiki(file_path)
        for file_path in deleted_files:
            self.delete_wiki_file(file_path)

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
        config_path = os.path.join(self.wiki_path, '.vitepress', 'config.js')
        with open(config_path, 'r') as file:
            config = file.read()
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

