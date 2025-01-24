import os
import json
import logging
import pathlib

from codx.junior.utils import write_file
from codx.junior.model import (
    GlobalSettings,
    ProjectScript
)
from codx.junior.utils import exec_command

logger = logging.getLogger(__name__)

ROOT_PATH = os.path.dirname(__file__)
GLOBAL_SETTINGS = None


def read_global_settings():
    global GLOBAL_SETTINGS
    try:
        with open(f"global_settings.json") as f:
            GLOBAL_SETTINGS = GlobalSettings(**json.loads(f.read()))
    except:
        GLOBAL_SETTINGS = GlobalSettings()
    return GLOBAL_SETTINGS


def write_global_settings(global_settings: GlobalSettings):
    global GLOBAL_SETTINGS
    try:
        old_settings = read_global_settings()
        with open(f"global_settings.json", "w") as f:
            f.write(json.dumps(global_settings.dict()))

        if global_settings.git.username:
            exec_command(
                f'git config --global user.name "{global_settings.git.username}"'
            )
        if global_settings.git.email:
            exec_command(f'git config --global user.email "{global_settings.git.email}"')

        GLOBAL_SETTINGS = global_settings
    except Exception as ex:
        logger.exception(f"Error saving global settings: {ex}")


read_global_settings()
logger.info(f"GLOBAL_SETTINGS: {GLOBAL_SETTINGS}")


class CODXJuniorSettings:
    def __init__(self, **kwrgs):
        self.ai_provider = "openai"
        self.ai_model = "gpt-4o"

        self.project_name = ""
        self.project_path = ""
        self.codx_path = ""
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
        self.watching = False
        self.use_knowledge = True
        self.knowledge_hnsw_M = 1024
        self.project_icon = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQRhLNgwkP06cH3_D3Unp8DqL9eFCyhI8lHwQ&s"

        self.log_ignore = ""

        self.project_scripts: ProjectScript = []

        self.urls = []
        if kwrgs:
            keys = CODXJuniorSettings().__dict__.keys()
            for key in kwrgs.keys():
                self.__dict__[key] = kwrgs.get(key)

    def __str__(self):
        return json.dumps(self.__dict__)

    def get_ai_api_key(self):
        if self.ai_provider == "openai":
            return GLOBAL_SETTINGS.openai.openai_api_key
        if self.ai_provider == "anthropic":
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_api_key
        return None

    def get_ai_api_url(self):
        if self.ai_provider == "openai":
            return GLOBAL_SETTINGS.openai.openai_api_url
        if self.ai_provider == "anthropic":
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_api_url
        return None

    def get_ai_model(self):
        if self.ai_model:
            return self.ai_model
        if self.ai_provider == "openai":
            return GLOBAL_SETTINGS.openai.openai_model
        if self.ai_provider == "anthropic":
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_model
        return None

    def get_ai_embeddings_model(self):
        return "text-embedding-3-small"

    def get_ai_embeddings_vector_size(self):
        return 1536

    def get_project_settings_file(self):
        return f"{self.codx_path}/project.json"

    @classmethod
    def from_env(cls):
        base = CODXJuniorSettings()
        gpt_envs = [env for env in os.environ if env.startswith("GPTARG_")]
        envs = [(env.replace("GPTARG_", ""), os.environ[env]) for env in gpt_envs]
        for k, v in envs:
            base.__dict__[k] = v
        return base

    
    @classmethod
    def from_codx_path(cls, codx_path: str):
        return CODXJuniorSettings.from_project_file(f"{codx_path}/project.json")
        
    @classmethod
    def from_project_file(cls, project_file_path: str):
        base = CODXJuniorSettings()
        base.codx_path = project_file_path.replace("/project.json", "")
        base.project_path = base.codx_path.replace("/.codx", "")
        with open(project_file_path, "r") as f:
            settings = json.loads(f.read())
            settings = CODXJuniorSettings(**{**base.__dict__, **settings})
            # Avoid override
            settings.codx_path = base.codx_path
            if not settings.project_path or settings.project_path[0] != "/":
                settings.project_path = base.project_path
            return settings

    @classmethod
    def from_json(cls, settings: dict):
        base = CODXJuniorSettings.from_env()
        new_settings = CODXJuniorSettings(**{ **base.__dict__, **settings })
        logging.info(f"Project from json {settings}")
        logging.info(f"Project from json - settings: {new_settings}")
        return new_settings

    def to_env(self) -> [str]:
        keys = self.__dict__.keys()
        gpt_envs = [f'GPTARG_{key}="{self.__dict__[key]}"' for key in keys]
        return gpt_envs

    @classmethod
    def get_valid_keys(cls):
        keys = CODXJuniorSettings().__dict__.keys()
        return [k for k in keys if k not in ["codx_path"]]

    def save_project(self):
        valid_keys = CODXJuniorSettings.get_valid_keys()
        path = f"{self.codx_path}/project.json"
        os.makedirs(self.codx_path, exist_ok=True)
        project_path_folders = self.project_path.split("/")
        codx_path_folders = self.codx_path.split("/")[:-1]
        logging.info(f"Saving settings without project_path {project_path_folders} {codx_path_folders}")
            
        if project_path_folders == codx_path_folders: # Check for custom project_path
            self.project_path = None

        settings = self.__dict__
        logging.info(f"Saving project {path}: {settings}")
        data = {}
        for key in valid_keys:
            data[key] = settings[key]
        logger.info(f"Saving project {valid_keys}: {data}")
        write_file(path, json.dumps(data, indent=2))

    def get_sub_projects(self):
        try:
            all_project_files = pathlib.Path(self.project_path).rglob(
                "**/.codx/project.json"
            )
            sub_projects = [
                CODXJuniorSettings.from_project_file(str(project_file_path))
                for project_file_path in all_project_files
            ]
            return [sb for sb in sub_projects if sb.codx_path != self.codx_path]
        except Exception as ex:
            logger.debug(f"Error get_sub_projects {ex}")

        return []

    def is_valid_project(self):
        return True if self.get_ai_api_key() else False

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


    def get_ignore_patterns(self):
        ignore_patterns = [".git", "node_modules"]
        if self.knowledge_file_ignore:
            ignore_patterns = ignore_patterns + [i.strip() for i  in self.knowledge_file_ignore.split(",")]
        return ignore_patterns

    def is_valid_project_file(self, file_path: str):
        return not [p for p in self.get_ignore_patterns() if p in file_path]