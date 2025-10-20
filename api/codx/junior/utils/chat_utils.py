import re
import logging
from typing import List

from pydantic import BaseModel

from codx.junior.project.project_discover import (
  find_project_by_name,
)
from codx.junior.model.model import Profile
from codx.junior.settings import CODXJuniorSettings


class QueryMentions(BaseModel):
    projects: List[CODXJuniorSettings]
    profiles: List[Profile]

logger = logging.getLogger(__name__)
class ChatUtils:
    def __init__(self, profile_manager):
        self.profile_manager = profile_manager

    def get_query_mentions(self, query: str) -> QueryMentions:
        mentions = self.extract_query_mentions(query=query)
        projects = self.find_projects_by_mentions(mentions=mentions)
        profiles = self.find_profiles_by_mentions(mentions=mentions)
        return QueryMentions(**{
          "projects": projects,
          "profiles": profiles
        })

    def extract_query_mentions(self, query: str):
        mentions = re.findall(r'@[a-zA-Z0-9\-\_\.]+', query)
        mentions = list(set([m[1:] for m in mentions])) if mentions else []
        # logger.info("Extracted mentions: %s", mentions)
        return mentions

    def find_projects_by_mentions(self, mentions: [str]):
        return [project for project in [find_project_by_name(mention[1:]) for mention in mentions] if project]

    def find_profiles_by_mentions(self, mentions: [str]):
        profiles = self.profile_manager.list_all_profiles()
        # logger.info("Project profiles: %s", [p.name for p in profiles])
        mention_profiles = [p for p in profiles if p.name in mentions]
        # logger.info("Extracted profiles for '%s': %s", mentions, mention_profiles)
        return self.profile_manager.get_profiles_and_parents(mention_profiles)

