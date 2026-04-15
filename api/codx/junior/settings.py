import os
import json
import logging
import pathlib
import uuid
import traceback

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from codx.junior.global_settings import (
  get_model_settings,
  read_global_settings,
  get_global_settings
)

from codx.junior.utils.utils import (
  write_file
)
from codx.junior.model.model import (
    ProjectScript,
    AISettings
)

logger = logging.getLogger(__name__)

ROOT_PATH = os.path.dirname(__file__)
HOME=os.environ.get("HOME")

CODX_JUNIOR_SETTINGS_COMPUTED_PROPERTIES = ["codx_path", "metrics", "users", "is_git_root"]
        
class CODXJuniorSettings(BaseModel):
    project_id: Optional[str] = Field(default=None)

    project_name: Optional[str] = Field(default=None)
    project_path: Optional[str] = Field(default="")
    abs_project_path: Optional[str] = Field(default="")
    project_branches: Optional[List[str]] = Field(default=[])
    
    codx_path: Optional[str] = Field(default=None)
    project_wiki: Optional[bool] = Field(default=False)
    project_wiki_path: Optional[str] = Field(default=None)
    project_dependencies: Optional[str] = Field(default=None)

    project_preview_url: Optional[str] = Field(default=None)

    knowledge_extract_document_tags: Optional[bool] = Field(default=False)
    knowledge_search_type: Optional[str] = Field(default="similarity")
    knowledge_search_document_count: Optional[int] = Field(default=10)
    knowledge_enrich_documents: Optional[bool] = Field(default=False)
    knowledge_context_cutoff_relevance_score: Optional[float] = Field(default=0.9)
    knowledge_context_rag_distance: Optional[float] = Field(default=0.4)
    knowledge_external_folders: Optional[str] = Field(default="")
    knowledge_query_subprojects: Optional[bool] = Field(default=True)
    knowledge_file_ignore: Optional[str] = Field(default=".codx")

    knowledge_generate_training_dataset: Optional[bool] = Field(default=False)

    save_mentions: Optional[bool] = Field(default=False)

    watching: Optional[bool] = Field(default=False)
    use_knowledge: Optional[bool] = Field(default=True)
    knowledge_hnsw_M: Optional[int] = Field(default=1024)
    project_icon: Optional[str] = Field(default="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQRhLNgwkP06cH3_D3Unp8DqL9eFCyhI8lHwQ&s")

    log_ignore: Optional[str] = Field(default="")

    last_access_time: Optional[str] = Field(default="")

    project_scripts: Optional[List[ProjectScript]] = Field(default=[])

    embeddings_model:  str = Field(default="")
    llm_model: str = Field(default="")
    rag_model: str = Field(default="")
    wiki_model: str = Field(default="")

    last_error: str = Field(default="")

    urls: Optional[List[str]] = Field(default=[])

    repo_url: Optional[str] = Field(default=None)

    is_git_root: Optional[bool] = Field(default=False)

    def __str__(self):
        return str(self.model_dump())

    def get_agent_max_iterations(self):
        return get_global_settings().agent_settings.max_agent_iteractions

    def get_llm_settings(self, llm_model: str = None) -> AISettings:
        if not llm_model:
            llm_model = self.llm_model 
        if not llm_model:
            llm_model = get_global_settings().llm_model

        return get_model_settings(llm_model)   

    def get_embeddings_settings(self) -> AISettings:
        embeddings_model = self.embeddings_model 
        if not embeddings_model:
            embeddings_model = get_global_settings().embeddings_model

        return get_model_settings(embeddings_model)

    def get_project_settings_file(self):
        return f"{self.codx_path}/project.json"

    def get_project_workspaces(self):
        global_settings = read_global_settings()
        return [w for w in global_settings.workspaces if self.project_id in w.project_ids]

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
            # User set absolute path in project_path
            if settings.project_path \
                and settings.project_path.startswith("/") \
                and os.path.isdir(settings.project_path):
                settings.abs_project_path = settings.project_path
            else:
                # User set reltive project_path
                if settings.project_path:
                    norm_project_path = os.path.normpath(os.path.join(base.project_path, settings.project_path))
                    settings.abs_project_path = norm_project_path        
            # project_path is empty, use same as base
            if not settings.abs_project_path:
                settings.abs_project_path = base.project_path
    
            if not settings.project_id:
                return settings.save_project()
            settings.is_git_root = os.path.isdir(f"{settings.abs_project_path}/.git")
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
        return [k for k in keys if k not in CODX_JUNIOR_SETTINGS_COMPUTED_PROPERTIES]

    def save_project(self):
        valid_keys = CODXJuniorSettings.get_valid_keys()
        path = f"{self.codx_path}/project.json"
        os.makedirs(self.codx_path, exist_ok=True)
        project_path_folders = self.abs_project_path.split("/")
        codx_path_folders = self.codx_path.split("/")[:-1]
        logging.info(f"Saving settings without project_path {project_path_folders} {codx_path_folders}")
            
        if project_path_folders == codx_path_folders: # Check for custom project_path
            self.abs_project_path = None
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

        return CODXJuniorSettings.from_project_file(path)

    def get_sub_projects(self):
        try:
            all_project_files = pathlib.Path(self.abs_project_path).rglob(
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
        ai_settings = self.get_llm_settings()
        return True if ai_settings.api_url or ai_settings.provider == 'llmfactory' else False

    def get_dbs(self):
        from codx.junior import build_dbs

        return build_dbs(settings=self)

    def get_ai(self):
        from codx.junior import build_ai

        return build_ai(settings=self)

    def get_project_wiki_path(self):
        if not self.project_wiki_path:
            return os.path.join(self.codx_path, "wiki")

        if self.project_wiki_path[0] == "/":
            return self.project_wiki_path
        return os.path.join(self.abs_project_path, self.project_wiki_path)

    def get_project_dependencies(self):
        if self.project_dependencies:
            return [d for d in self.project_dependencies.split(",") if d]
        return []

    def get_log_ai(self):
        return get_global_settings().log_ai

    def get_sub_projects_paths(self):
        sub_projects = self.get_sub_projects()
        return [project.abs_project_path for project in sub_projects]


    def get_ignore_patterns(self):
        ignore_patterns = [".git", "node_modules"]
        if self.project_wiki_path:
            wiki_path = os.path.join(self.abs_project_path, self.project_wiki_path)
            ignore_patterns.append(wiki_path)
        if self.knowledge_file_ignore:
            ignore_patterns = ignore_patterns + \
                            [i.strip() for i  in self.knowledge_file_ignore.split(",")] + \
                            self.get_sub_projects_paths()
        return ignore_patterns

    def is_valid_project_file(self, file_path: str):
        return not [p for p in self.get_ignore_patterns() if p in file_path]

    def get_wiki_model(self):
        return self.wiki_model or get_global_settings().wiki_model

    def get_rag_model(self):
        return self.rag_model or get_global_settings().rag_model

    def get_project_ai_models(self):
        return get_global_settings().ai_models


class CODXJuniorProject(CODXJuniorSettings):
    metrics: Optional[Dict] = Field(default={})
    workspaces: Optional[List[Dict]] = Field(default=[])
    users: Optional[List[dict]] = Field(default=[])
    permissions: Optional[str] = Field(default="")