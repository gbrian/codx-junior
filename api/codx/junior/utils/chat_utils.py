import re
import logging

from codx.junior.globals import (
  find_project_by_name,
)

logger = logging.getLogger(__name__)
class ChatUtils:
    def __init__(self, profile_manager):
        self.profile_manager = profile_manager

    def get_query_mentions(self, query: str):
        mentions = self.extract_query_mentions(query=query)
        projects = self.find_projects_by_mentions(mentions=mentions)
        profiles = self.find_profiles_by_mentions(mentions=mentions)
        return {
          "projects": projects,
          "profiles": profiles
        }

    def extract_query_mentions(self, query: str):
        mentions = re.findall(r'@[a-zA-Z0-9\-\_\.]+', query)
        logger.info(f"Extracted mentions: {mentions}")
        return mentions

    def find_projects_by_mentions(self, mentions: [str]):
        return [project for project in [find_project_by_name(mention[1:]) for mention in mentions] if project]

    def find_profiles_by_mentions(self, mentions: [str]):
        profiles = self.profile_manager.list_profiles()
        mention_profiles = [p for p in profiles if p.name in mentions]
        return self.profile_manager.get_profiles_and_parents(mention_profiles)

