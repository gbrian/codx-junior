import os
import json
import logging
import pathlib

from codx.junior.utils import write_file
from codx.junior.model import GlobalSettings
from codx.junior.utils import (
    exec_command
)

logger = logging.getLogger(__name__)

ROOT_PATH=os.path.dirname(__file__)

def read_global_settings():
    try:
        with open(f"global_settings.json") as f:
            return GlobalSettings(**json.loads(f.read()))
    except:
        return GlobalSettings()

def write_global_settings(global_settings: GlobalSettings):
    try:
        old_settings = read_global_settings()
        with open(f"global_settings.json", 'w') as f:
            f.write(json.dumps(global_settings.dict()))

        if global_settings.git.username:
            exec_command(f'git config --global user.name "{global_settings.git.username}"')
        if global_settings.git.email:
            exec_command(f'git config --global user.email "{global_settings.git.email}"')

        GLOBAL_SETTINGS=global_settings
    except Exception as ex:
        logger.exception(f"Error saving global settings: {ex}")


GLOBAL_SETTINGS=read_global_settings()

class CODXJuniorSettings:
    def __init__(self, **kwrgs):
        self.ai_provider = "openai"
        self.ai_model = "gpt-4o"
        
        self.project_name = ""
        self.project_path = "."
        self.project_wiki = ""
        self.project_dependencies = ""
        
        self.knowledge_extract_document_tags = False
        self.knowledge_search_type = "similarity"
        self.knowledge_search_document_count = 10
        self.knowledge_enrich_documents = False
        self.knowledge_context_cutoff_relevance_score = 0.9
        self.knowledge_external_folders = ""
        self.knowledge_query_subprojects = True
        self.knowledge_file_ignore = ".codx"
        
        self.temperature = 0.7
        self.codx_path = "./.codx"
        self.watching = False
        self.use_knowledge = True
        self.knowledge_hnsw_M = 1024
        self.project_icon = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQRhLNgwkP06cH3_D3Unp8DqL9eFCyhI8lHwQ&s"

        self.log_ignore = ""
        
        self.urls = []
        if kwrgs:
            keys = CODXJuniorSettings().__dict__.keys()
            for key in kwrgs.keys():
              self.__dict__[key] = kwrgs.get(key)

    
    def get_ai_api_key(self):
        if self.ai_provider == 'openai':
            return GLOBAL_SETTINGS.openai.openai_api_key
        if self.ai_provider == 'anthropic':
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_api_key
        return None

    def get_ai_api_url(self):
        if self.ai_provider == 'openai':
            return GLOBAL_SETTINGS.openai.openai_api_url
        if self.ai_provider == 'anthropic':
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_api_url
        return None

    def get_ai_model(self):
        if self.ai_model:
            return self.ai_model
        if self.ai_provider == 'openai':
            return GLOBAL_SETTINGS.openai.openai_model
        if self.ai_provider == 'anthropic':
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_model
        return None

    @classmethod
    def from_env(cls):
      base = CODXJuniorSettings()
      gpt_envs = [env for env in os.environ if env.startswith("GPTARG_")]
      envs = [(env.replace("GPTARG_", ""), os.environ[env]) for env in gpt_envs]
      for k, v in envs:
        base.__dict__[k] = v
      return base

    @classmethod
    def from_project(cls, codx_path: str):
        base = CODXJuniorSettings()
        base.codx_path = codx_path
        base.project_path = codx_path
        project_file = codx_path
        if not project_file.endswith("/project.json"):
            project_file = f"{codx_path}/project.json" 
        with open(project_file, 'r') as f:
          settings = json.loads(f.read())
          settings = CODXJuniorSettings(**{ **base.__dict__, **settings })
          if not settings.project_name:
              settings.project_name = settings.project_path.split("/")[-1]
          return settings
    
    @classmethod
    def from_json(cls, settings: dict):
      base = CODXJuniorSettings.from_env()
      return CODXJuniorSettings(**{ **base.__dict__, **settings })

    def to_env(self) -> [str]:
      keys = self.__dict__.keys()
      gpt_envs = [f"GPTARG_{key}=\"{self.__dict__[key]}\"" for key in keys]
      return gpt_envs

    def save_project(self):
      settings = self.__dict__
      valid_keys = CODXJuniorSettings().__dict__.keys()
      path = f"{self.codx_path}/project.json"
      os.makedirs(self.codx_path, exist_ok=True)
      logging.info(f"Saving project {path} {settings}")
      data = {}
      for key in valid_keys:
          data[key] = settings[key]
      logger.info(f"Saving project {valid_keys}: {data}")
      write_file(path, json.dumps(data, indent=2))

    def get_sub_projects(self):
      try:
            all_project_files = pathlib.Path(self.project_path).rglob("**/.codx/project.json")
            sub_projects = [
                CODXJuniorSettings.from_project(str(project_file_path)) \
                    for project_file_path in \
                        all_project_files]

            sub_projects = [sub_project for sub_project in sub_projects \
                                if sub_project.codx_path != self.codx_path]
            # logger.info(f"get_sub_projects for {self.project_name}: {[p.project_name for p in sub_projects]}")
            return sub_projects
      except Exception as ex:
            logger.debug(f"Error get_sub_projects {ex}")

      return []

    def get_dbs(self):
      from codx.junior import build_dbs
      return build_dbs(settings=self)

    def get_ai(self):
      from codx.junior import build_ai
      return build_ai(settings=self)

    def get_project_wiki_path(self):
        if not self.project_wiki: 
            return None
        if self.project_wiki[0] == "/":
            return self.project_wiki
        return os.path.join(self.project_path, self.project_wiki)

    def get_project_dependencies(self):
        if self.project_dependencies:
            return [d for d in self.project_dependencies.split(",") if d]
        return []

    def get_log_ai(self):
        return GLOBAL_SETTINGS.log_ai