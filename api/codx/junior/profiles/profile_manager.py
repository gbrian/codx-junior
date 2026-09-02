import os
import json
import pathlib
import logging
import re
import shutil

from typing import List

from codx.junior.settings import CODXJuniorSettings
from codx.junior.model.model import Profile
from codx.junior.utils.utils import write_file

from codx.junior.project.project_discover import (
    find_project_parents,
    find_project_by_name
)

logger = logging.getLogger(__name__)

def generate_llm_tree(root_path, indent="", is_last=True, ignore_list=None):
    if ignore_list is None:
        ignore_list = {'.git', '__pycache__', '.vscode', '.DS_Store', 'node_modules', 'venv'}
    
    path = pathlib.Path(root_path)
    if not path.exists():
        return "Invalid Path"

    # Header for the root on the first call
    tree_str = f"{indent}{'└── ' if is_last else '├── '}{path.name}/\n"
    
    # Update indent for children
    new_indent = indent + ("    " if is_last else "│   ")
    
    # Filter and sort items (directories first, then files)
    items = [i for i in path.iterdir() if i.name not in ignore_list]
    items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
    
    for i, item in enumerate(items):
        last_item = (i == len(items) - 1)
        if item.is_dir():
            tree_str += generate_llm_tree(item, new_indent, last_item, ignore_list)
        #else:
        #    connector = "└── " if last_item else "├── "
        #    tree_str += f"{new_indent}{connector}{item.name}\n"
            
    return tree_str

class ProfileManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.profiles_path = f"{settings.codx_path}/profiles"
        os.makedirs(self.profiles_path, exist_ok=True)

        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        self.base_profiles_path = f"{current_directory}"

    def base_profiles(self):
        def _files (file_gen):
            return [str(file) for file in file_gen]

        base_profiles = _files(pathlib.Path(self.base_profiles_path).rglob("**/*.profile"))
        return _files(base_profiles)

    def project_profile_paths(self):
        def _files (file_gen):
            return [str(file) for file in file_gen]

        # Look for profiles in both old format (flat) and new format (in folders)
        profiles = []
        # New format: [profile_name]/[profile_name].profile
        profiles.extend(_files(list(pathlib.Path(self.profiles_path).rglob("*/*.profile"))))
        # Old format fallback: *.profile (for backward compatibility)
        profiles.extend(_files(list(pathlib.Path(self.profiles_path).glob("*.profile"))))
        
        return profiles

    def list_all_profiles(self):
        parent_projects = find_project_parents(project=self.settings)
        codx_junior = find_project_by_name("codx-junior")
        if codx_junior:
            parent_projects.append(codx_junior)
        logger.info("list_all_profiles: %s", [p.project_name for p in parent_projects])
        
        all_profiles = {}
        
        # 1. Parent and codx-junior project profiles
        for project in parent_projects:
            profiles = ProfileManager(settings=project).list_profiles()
            for profile in profiles:
                all_profiles[profile.name] = profile
        
        # 2. Current project profiles (can override parent profiles)
        for profile in self.list_profiles():
            all_profiles[profile.name] = profile

        # 3. Built-in base profiles from source code (only if not already defined)
        for profile_path in self.base_profiles():
            profile = self.load_profile(profile_path)
            if profile and profile.name not in all_profiles:
                all_profiles[profile.name] = profile
        
        return [self.get_profile_With_content(profile=p) for p in list(all_profiles.values())]


    def list_profiles(self):
        profiles = [self.load_profile(profile_path) for profile_path in self.project_profile_paths()]
        return [p for p in profiles if p is not None]

    def read_profile(self, profile_name) -> Profile:
        project_profile_paths = self.project_profile_paths()
        match_profiles = [profile_path for profile_path in project_profile_paths if profile_name in profile_path]
        return self.load_profile(match_profiles[0]) if match_profiles else None

    def load_profile(self, profile_path) -> Profile:
        profile = None
        try:
            with open(profile_path, 'r') as f:
                content = f.read()
                
                # Validate content is not empty
                if not content or not content.strip():
                    logger.warning(f"Profile file is empty, using defaults: {profile_path}")
                    profile = Profile(name=pathlib.Path(profile_path).stem)
                else:
                    try:
                        profile = Profile(**json.loads(content))
                    except json.JSONDecodeError as json_ex:
                        logger.error(f"Invalid JSON in profile {profile_path}: {json_ex}. Using defaults.")
                        profile = Profile(name=pathlib.Path(profile_path).stem)
                
                profile.path = profile_path

            # Load content from markdown file in new format: [profile_name]/[profile_name].md
            profile_dir = os.path.dirname(profile_path)
            markdown_content_path = os.path.join(profile_dir, f"{profile.name}.md")
            
            if os.path.isfile(markdown_content_path):
                with open(markdown_content_path, 'r') as f:
                    profile.content = f.read()
                logger.info(f"Loaded profile content from: {markdown_content_path}")
            
            if not profile.avatar:
                profile.avatar = f"https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r={profile.name}"
            profile.project_id = self.settings.project_id
            return profile
        except Exception as ex:
            logger.exception(f"Error loading profile: {profile_path} {ex}")
            # Return a minimal valid profile instead of raising
            return Profile(
                name=pathlib.Path(profile_path).stem,
                path=profile_path,
                project_id=self.settings.project_id,
                avatar=f"https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r={pathlib.Path(profile_path).stem}"
            )

    def _migrate_profile_to_folder(self, profile_name: str, old_profile_path: str):
        """Migrate a profile from flat structure to folder structure"""
        profile_folder = os.path.join(self.profiles_path, profile_name)
        os.makedirs(profile_folder, exist_ok=True)
        
        new_profile_path = os.path.join(profile_folder, f"{profile_name}.profile")
        
        # Move profile JSON file
        if os.path.isfile(old_profile_path) and old_profile_path != new_profile_path:
            shutil.move(old_profile_path, new_profile_path)
            logger.info(f"Migrated profile from {old_profile_path} to {new_profile_path}")
        
        # Move associated markdown content file (old format: [profile_name].md.profile or [profile_name].profile.md)
        old_markdown_paths = [
            f"{old_profile_path.replace('.profile', '')}.md.profile",
            f"{old_profile_path.replace('.profile', '')}.profile.md"
        ]
        
        for old_markdown_path in old_markdown_paths:
            if os.path.isfile(old_markdown_path):
                new_markdown_path = os.path.join(profile_folder, f"{profile_name}.md")
                shutil.move(old_markdown_path, new_markdown_path)
                logger.info(f"Migrated markdown content from {old_markdown_path} to {new_markdown_path}")
                break

    def save_profile(self, profile: Profile):
        if not profile.name:
            raise Exception('Invalid profile')

        # Create profile folder
        profile_folder = os.path.join(self.profiles_path, profile.name)
        os.makedirs(profile_folder, exist_ok=True)
        
        # New profile path in folder structure
        profile_path = os.path.join(profile_folder, f"{profile.name}.profile")
        
        logger.info(f"Save profile {profile_path}")
        
        # Check if profile exists in old flat format and migrate it
        old_profile_path = os.path.join(self.profiles_path, f"{profile.name}.profile")
        if os.path.isfile(old_profile_path) and old_profile_path != profile_path:
            self._migrate_profile_to_folder(profile.name, old_profile_path)
        
        # Save profile content to markdown file in new format: [profile_name]/[profile_name].md
        if profile.content:
            markdown_content_path = os.path.join(profile_folder, f"{profile.name}.md")
            with open(markdown_content_path, 'w') as f:
                f.write(profile.content)
            logger.info(f"Saved profile content to: {markdown_content_path}")
        
        # Save profile JSON without content property
        with open(profile_path, 'w') as f:
            profile_data = profile.model_dump()
            profile_data['content'] = None
            profile_data['parsed_content'] = None
            f.write(json.dumps(profile_data, indent=2))

    def delete_profile(self, profile_name):
        # Delete profile in new folder structure
        profile_folder = os.path.join(self.profiles_path, profile_name)
        if os.path.isdir(profile_folder):
            shutil.rmtree(profile_folder)
            logger.info(f"Deleted profile folder: {profile_folder}")
        
        # Also check and delete old flat format (backward compatibility)
        old_profile_path = os.path.join(self.profiles_path, f"{profile_name}.profile")
        if os.path.isfile(old_profile_path):
            os.remove(old_profile_path)
            logger.info(f"Deleted old format profile: {old_profile_path}")
            
            old_markdown_paths = [
                f"{old_profile_path.replace('.profile', '')}.md.profile",
                f"{old_profile_path.replace('.profile', '')}.profile.md"
            ]
            for old_markdown_path in old_markdown_paths:
                if os.path.isfile(old_markdown_path):
                    os.remove(old_markdown_path)
                    logger.info(f"Deleted old format markdown: {old_markdown_path}")

    def is_profile_match(self, profile: Profile, file_path: str):
        try:
            return profile.file_match and re.search(profile.file_match, file_path)
        except:
            return False

    def get_file_profiles_by_file_path(self, file_path: str):
        file_profiles = [profile for profile in self.list_all_profiles() \
          if self.is_profile_match(profile=profile, file_path=file_path)]
        return self.reduce_linked_profiles(profiles=file_profiles)

    def get_profiles_by_name(self, profiles: []):
        return [p for p in self.list_all_profiles() if p.name in profiles]

    def get_profile_content_context(self, profile: Profile):
        return {
          "project_path": lambda: self.settings.abs_project_path,
          "project_name": lambda: self.settings.project_name,
          # "project_tree": lambda: generate_llm_tree(self.settings.abs_project_path)
        }

    def get_profile_With_content(self, profile: Profile):
        context = self.get_profile_content_context(profile=profile)
        
        # Regex explains:
        # {{    -> Matches literal opening braces
        # \s*   -> Matches optional whitespace
        # (\w+) -> Captures the variable name (alphanumeric/underscore)
        # \s*   -> Matches optional whitespace
        # }}    -> Matches literal closing braces
        pattern = r'\{\{\s*(\w+)\s*\}\}'

        def replacement_logic(match):
            variable_name = match.group(1)
            # Returns the value if found, otherwise keeps the original {{var}} text
            fnc = context.get(variable_name, None)
            if fnc:
                return str(fnc())
            return match.group(0)

        profile.parsed_content = re.sub(pattern, replacement_logic, profile.content or "")
        return profile

    def get_all_linked_profiles(self, profile: Profile, seen: set = None) -> List[Profile]:
        # Fix: Initialize seen inside the function to avoid state leakage
        if seen is None:
            seen = []
        
        # We use a list for the return value to maintain order, but a set for O(1) lookups
        results = []
        
        # Combine current profile with its neighbors
        neighbors = [profile] + self.get_profiles_by_name(profile.profiles or [])
        
        for linked_profile in neighbors:
            # Use a unique identifier (like an ID) for the set check
            if linked_profile not in seen:
                seen.append(linked_profile)
                results.append(linked_profile)
                # Extend results with nested links
                results.extend(self.get_all_linked_profiles(linked_profile, seen))
                
        return results

    def reduce_linked_profiles(self, profiles: List[Profile]) -> List[Profile]:
        all_unique_seen = []
        deduplicated_list = []
        
        for profile in profiles:
            # This will now correctly start fresh for each top-level profile
            for linked in self.get_all_linked_profiles(profile):
                if linked not in all_unique_seen:
                    all_unique_seen.append(linked)
                    deduplicated_list.append(linked)
                    
        return deduplicated_list