import os
import json
import logging
import pathlib

logger = logging.getLogger(__name__)

class GPTEngineerSettings:
    def __init__(self, **kwrgs):
        self.ai_provider = "openai"
        self.project_name = None
        self.project_path = "."
        self.project_wiki = None
        self.openai_api_key = None
        self.openai_api_base = None
        self.anthropic_api_key = None
        self.anthropic_model = None
        self.knowledge_extract_document_tags = False
        self.knowledge_search_type = "similarity"
        self.knowledge_search_document_count = 10
        self.temperature = 0.7
        self.model = None
        self.knowledge_file_ignore = None
        self.codx_path = "./.codx"
        self.knowledge_enrich_documents = False
        self.knowledge_context_cutoff_relevance_score = 0.9
        self.knowledge_external_folders = ""
        self.knowledge_query_subprojects = True
        self.watching = False
        self.use_knowledge = True
        self.log_ai = False
        self.knowledge_hnsw_M = 1024
        self.project_icon = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQRhLNgwkP06cH3_D3Unp8DqL9eFCyhI8lHwQ&s"
        if kwrgs:
            keys = GPTEngineerSettings().__dict__.keys()
            for key in kwrgs.keys():
              self.__dict__[key] = kwrgs.get(key)

    @classmethod
    def from_env(cls):
      base = GPTEngineerSettings()
      gpt_envs = [env for env in os.environ if env.startswith("GPTARG_")]
      envs = [(env.replace("GPTARG_", ""), os.environ[env]) for env in gpt_envs]
      for k, v in envs:
        base.__dict__[k] = v
      return base

    @classmethod
    def from_project(cls, codx_path: str):
        base = GPTEngineerSettings()
        base.codx_path = codx_path
        base.project_path = codx_path
        with open(f"{codx_path}/project.json", 'r') as f:
          settings = json.loads(f.read())
          settings = GPTEngineerSettings(**{ **base.__dict__, **settings })
          if not settings.project_name:
              settings.project_name = settings.project_path.split("/")[-1]
          return settings
    
    @classmethod
    def from_json(cls, settings: dict):
      base = GPTEngineerSettings.from_env()
      return GPTEngineerSettings(**{ **base.__dict__, **settings })

    def to_env(self) -> [str]:
      keys = self.__dict__.keys()
      gpt_envs = [f"GPTARG_{key}=\"{self.__dict__[key]}\"" for key in keys]
      return gpt_envs

    def save_project(self):
      settings = self.__dict__
      path = f"{self.codx_path}/project.json"
      os.makedirs(self.codx_path, exist_ok=True)
      logging.info(f"Saving project {path} {settings}")
      with open(path, 'w') as f:
        f.write(json.dumps(settings, indent=2))

    def detect_sub_projects(self):
      try:
        return [str(project_path).replace("/.codx/project.json", "") for project_path in \
          pathlib.Path(self.project_path).rglob("./*/.codx/project.json")]
      except Exception as ex:
        log.debug(f"Error {ex}")

      return []

    def get_dbs(self):
      from codx.junior import build_dbs
      return build_dbs(settings=self)

    def get_ai(self):
      from codx.junior import build_ai
      return build_ai(settings=self)

    def get_sub_projects(self):
        try:
            return self.sub_projects.split(",") if self.sub_projects else []
        except:
            pass
        return []

    def get_project_wiki_path(self):
        if not self.project_wiki: 
            return f"{self.project_path}/wiki"
        return self.project_wiki
