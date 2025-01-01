import os
import json
import pathlib
import logging


from codx.junior.settings import CODXJuniorSettings
from codx.junior.model import Profile
from codx.junior.utils import write_file

logger = logging.getLogger(__name__)

class ProfileManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.profiles_path = f"{settings.codx_path}/profiles"
        os.makedirs(self.profiles_path, exist_ok=True)

        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        self.base_profiles_path = f"{current_directory}"

    def get_profiles (self):
        def _files (file_gen):
            return [str(file) for file in file_gen]

        base_profiles = _files(pathlib.Path(self.base_profiles_path).rglob("**/*.profile"))
        project_profiles = _files(pathlib.Path(self.profiles_path).rglob("**/*.profile"))
        return _files(base_profiles), _files(project_profiles)

    def list_profiles(self):
        base_profiles , project_profiles = self.get_profiles()
        
        def is_oveeriden(project_file_path):
            base_name = os.path.basename(project_file_path)
            return [project_profile for project_profile in project_profiles if base_name in project_profile]
        
        base_profiles = [profile_path for profile_path in base_profiles if not is_oveeriden(profile_path)]
        profiles = [self.load_profile(profile_path) for profile_path in base_profiles + project_profiles]
        return profiles

    def read_profile(self, profile_name) -> Profile:
        profiles = self.list_profiles()
        return [p for p in profiles if p.name == profile_name][0]

    def load_profile(self, profile_path) -> Profile:
        with open(profile_path, 'r') as f:
            content = f.read()
            profile = Profile(**json.loads(content))
            profile.path = profile_path
            return profile

    def save_profile(self, profile: Profile):
        if not profile.name:
            raise 'Invalid profie'
        profile_path = f"{os.path.join(self.profiles_path, profile.name)}.profile"
        logger.info(f"Save profile {profile_path}")
        with open(profile_path, 'w') as f:
            f.write(json.dumps(profile.__dict__))
        return self.read_profile(profile_name=profile.name)

    def delete_profile(self, profile_name):
        _, project_profiles = self.get_profiles()
        profile_file_name = f"{profile_name}.profile"
        profile_path = [file_path for file_path in project_profiles if file_path.endswith(profile_file_name)]
        if profile_path:
            os.remove(profile_path)
