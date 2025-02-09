import os
import json
import logging
import pathlib
import uuid
from pydantic import BaseModel, Field
from typing import Optional, List

from codx.junior.utils import write_file
from codx.junior.model import (
    GlobalSettings,
    ProjectScript,
    AISettings,
    EmbeddingAISettings
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
    logger.info(f"GLOBAL_SETTINGS: {global_settings}")
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


class CODXJuniorSettings(BaseModel):
    project_id: Optional[str] = Field(default=None)

    ai_settings: Optional[AISettings] = Field(default=AISettings())

    project_name: Optional[str] = Field(default=None)
    project_path: Optional[str] = Field(default="")
    codx_path: Optional[str] = Field(default=None)
    project_wiki: Optional[str] = Field(default=None)
    project_dependencies: Optional[str] = Field(default=None)

    knowledge_extract_document_tags: Optional[bool] = Field(default=False)
    knowledge_search_type: Optional[str] = Field(default="similarity")
    knowledge_search_document_count: Optional[int] = Field(default=10)
    knowledge_enrich_documents: Optional[bool] = Field(default=False)
    knowledge_context_cutoff_relevance_score: Optional[float] = Field(default=0.9)
    knowledge_external_folders: Optional[str] = Field(default="")
    knowledge_query_subprojects: Optional[bool] = Field(default=True)
    knowledge_file_ignore: Optional[str] = Field(default=".codx")

    temperature: Optional[float] = Field(default=0.7)
    watching: Optional[bool] = Field(default=False)
    use_knowledge: Optional[bool] = Field(default=True)
    knowledge_hnsw_M: Optional[int] = Field(default=1024)
    project_icon: Optional[str] = Field(default="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQRhLNgwkP06cH3_D3Unp8DqL9eFCyhI8lHwQ&s")

    log_ignore: Optional[str] = Field(default="")

    project_scripts: Optional[List[ProjectScript]] = Field(default=[])

    embeddings_ai_settings: Optional[EmbeddingAISettings] = Field(default=EmbeddingAISettings())

    urls: Optional[List[str]] = Field(default=[])

    def __str__(self):
        return str(self.model_dump())

    def get_ai_provider(self):
        if self.ai_settings.provider:
            return self.ai_settings.provider
        return GLOBAL_SETTINGS.ai_provider
 
    def get_ai_api_key(self):
        if self.ai_settings.api_key:
            return self.ai_settings.api_key
        if self.get_ai_provider() in ["openai", "llmlite"]:
            return GLOBAL_SETTINGS.openai.openai_api_key
        if self.get_ai_provider() == "anthropic":
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_api_key
        if self.get_ai_provider() == "mistral":
            return GLOBAL_SETTINGS.mistral_ai.mistral_api_key
        return None

    def get_ai_api_url(self):
        if self.ai_settings.api_url:
            return self.ai_settings.api_url
        if self.get_ai_provider() in ["openai", "llmlite"]:
            return GLOBAL_SETTINGS.openai.openai_api_url
        if self.get_ai_provider() == "anthropic":
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_api_url
        if self.get_ai_provider() == "mistral":
            return GLOBAL_SETTINGS.mistral_ai.mistral_api_url
        return None

    def get_ai_model(self):
        if self.ai_settings.model:
            return self.ai_settings.model
        if self.get_ai_provider() in ["openai", "llmlite"]:
            return GLOBAL_SETTINGS.openai.openai_model
        if self.get_ai_provider() == "anthropic":
            return GLOBAL_SETTINGS.anthropic_ai.anthropic_model
        if self.get_ai_provider() == "mistral":
            return GLOBAL_SETTINGS.mistral_ai.mistral_model
        return None

    def get_ai_embeddings_settings(self):
        if len(self.embeddings_ai_settings.provider or ""):
            return self.embeddings_ai_settings

        return GLOBAL_SETTINGS.embeddings_ai_settings

    def get_project_settings_file(self):
        return f"{self.codx_path}/project.json"

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
            settings = CODXJuniorSettings(**{**base.model_dump(), **settings})
            # Avoid override
            settings.codx_path = base.codx_path
            if not settings.project_path or settings.project_path[0] != "/":
                settings.project_path = base.project_path
            if not settings.project_id:
                return settings.save_project()
            return settings

    @classmethod
    def from_json(cls, settings: dict):
        base = CODXJuniorSettings()
        new_settings = CODXJuniorSettings(**{ **base.__dict__, **settings })
        logging.info(f"Project from json {settings}")
        logging.info(f"Project from json - settings: {new_settings}")
        return new_settings

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
        # project_id
        if not self.project_id:
            self.project_id = str(uuid.uuid4())

        settings = self.model_dump()
        logging.info(f"Saving project {path}: {settings}")
        data = {}
        for key in valid_keys:
            data[key] = settings[key]
        logger.info(f"Saving project {valid_keys}: {data}")
        write_file(path, json.dumps(data, indent=2))

        return self

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

    def get_sub_projects_paths(self):
        sub_projects = self.get_sub_projects()
        return [project.project_path for project in sub_projects]


    def get_ignore_patterns(self):
        ignore_patterns = [".git", "node_modules"]
        if self.knowledge_file_ignore:
            ignore_patterns = ignore_patterns + \
                            [i.strip() for i  in self.knowledge_file_ignore.split(",")] + \
                            self.get_sub_projects_paths()
        return ignore_patterns

    def is_valid_project_file(self, file_path: str):
        return not [p for p in self.get_ignore_patterns() if p in file_path]