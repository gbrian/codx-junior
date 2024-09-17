import os
import pathlib
import logging

from gpt_engineer.core.dbs import DBs
from gpt_engineer.core.settings import GPTEngineerSettings
from gpt_engineer.api.model import Profile
from gpt_engineer.api.profiles.coding import get_coding_profiles

class ProfileManager:
    def __init__(self, settings: GPTEngineerSettings):
        self.settings = settings
        self.profiles_path = f"{settings.gpteng_path}/profiles"
        os.makedirs(self.profiles_path, exist_ok=True)

        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        self.base_profiles_path = f"{current_directory}/profiles"

    def get_profiles (self):
        def _files (file_gen):
            return [str(file) for file in file_gen]

        base_profiles = _files(pathlib.Path(self.base_profiles_path).rglob("*"))
        project_profiles = _files(pathlib.Path(self.profiles_path).rglob("*"))
        return _files(base_profiles), _files(project_profiles)

    def list_profiles(self):
        base_profiles , project_profiles = self.get_profiles()
        profiles = list(set([os.path.basename(file) for file in base_profiles + project_profiles]))
        logging.info(f"List profiles {self.profiles_path} - {self.base_profiles_path}: {profiles}")
        return profiles

    def read_profile(self, profile_name) -> Profile:
        base_profiles , project_profiles = self.get_profiles()
        profile_path = [file_path for file_path in project_profiles if file_path.endswith(profile_name)]
        if not profile_path:
            profile_path = [file_path for file_path in base_profiles if file_path.endswith(profile_name)]
        if profile_path:
            with open(profile_path[0], 'r') as f:
                content = f.read()
                return Profile(name=profile_name, content=content)

    def create_profile(self, profile: Profile):
        with open(os.path.join(self.profiles_path, profile.name), 'w') as f:
            f.write(profile.content)

    def delete_profile(self, profile_name):
        _, project_profiles = self.get_profiles()
        profile_path = [file_path for file_path in project_profiles if file_path.endswith(profile_name)]
        if profile_path:
            os.remove(profile_path[0])

    def get_coding_profiles(self, file_paths: [str]):
        return get_coding_profiles(file_paths)