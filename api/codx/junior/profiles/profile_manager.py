import os
import json
import pathlib
import logging
import re

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

        return _files(list(pathlib.Path(self.profiles_path).rglob("*.profile")))

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

            #TODO: Old versions
            profile.content_path = f"{profile_path}.md"
            if os.path.isfile(profile.content_path):
                with open(profile.content_path, 'r') as f:
                  profile.content = f.read()
                self.save_profile(profile=profile)
                os.remove(profile.content_path)
                
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

    def save_profile(self, profile: Profile):
        if not profile.name:
            raise Exception('Invalid profie')

        profile_path = f"{os.path.join(self.profiles_path, profile.name)}.profile"
        
        logger.info(f"Save profile {profile_path}")
        with open(profile_path, 'w') as f:
            profile.parsed_content = None
            f.write(json.dumps(profile.model_dump(), indent=2))

    def delete_profile(self, profile_name):
        project_profile_paths = self.project_profile_paths()
        profile_file_name = f"{profile_name}.profile"
        profile_path = [file_path for file_path in project_profile_paths if file_path.endswith(profile_file_name)]
        if profile_path:
            os.remove(profile_path[0])

    def is_profile_match(self, profile: Profile, file_path: str):
        try:
            return profile.file_match and re.search(profile.file_match, file_path)
        except:
            return False

    def get_file_profiles_by_file_path(self, file_path: str):
        return [profile for profile in self.list_all_profiles() \
          if self.is_profile_match(profile=profile, file_path=file_path)]

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