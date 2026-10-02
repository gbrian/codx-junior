This document defines the `CODXJuniorSettings` and `CODXJuniorProject` classes, which are used to manage project-specific configurations and settings within the codx-api project.

### Global Settings Management

The module handles global settings for codx-junior, including AI provider configurations, LLM models, and general application settings.

-   **`GLOBAL_SETTINGS_PATH`**: Defines the path to the global settings JSON file, defaulting to `$HOME/global_settings.json` or a path specified by the `CODX_JUNIOR_CONFIG_FOLDER` environment variable.
-   **`read_global_settings()`**: Reads global settings from the `GLOBAL_SETTINGS_PATH`. If the file doesn't exist or an error occurs, it initializes and saves default settings.
-   **`write_global_settings()`**: Saves the current global settings to the `GLOBAL_SETTINGS_PATH`. It also includes a backup mechanism and attempts to update global Git configuration if username and email are provided.
-   **`backup_up_global_settings()`**: Creates a backup of the global settings file with a timestamp and maintains the last 20 backups.
-   **`get_provider_settings()`**: Retrieves AI provider settings by name from the global configuration.
-   **`get_model()`**: Finds an AI model configuration by its name or alias.
-   **`save_model()`**: Updates or adds an AI model configuration to the global settings.
-   **`get_model_settings()`**: Returns detailed AI settings for a given LLM model, combining model-specific configurations with provider details.

### CODXJuniorSettings Class

This class represents the core settings for a codx junior project.

-   **Fields**:
    -   `project_id`: Unique identifier for the project.
    -   `project_name`: Name of the project.
    -   `project_path`: File system path to the project.
    -   `project_branches`: List of branches associated with the project.
    -   `codx_path`: Path to the `.codx` directory within the project.
    -   `project_wiki`: Boolean indicating if project wiki is enabled.
    -   `project_wiki_path`: Path to the project wiki.
    -   `project_dependencies`: Comma-separated string of project dependencies.
    -   `project_preview_url`: URL for project preview.
    -   `knowledge_extract_document_tags`: Whether to extract tags from documents for knowledge.
    -   `knowledge_search_type`: Type of search for knowledge (e.g., "similarity").
    -   `knowledge_search_document_count`: Number of documents to retrieve in knowledge search.
    -   `knowledge_enrich_documents`: Whether to enrich documents for knowledge.
    -   `knowledge_context_cutoff_relevance_score`: Relevance score cutoff for knowledge context.
    -   `knowledge_context_rag_distance`: Distance threshold for RAG in knowledge context.
    -   `knowledge_external_folders`: Paths to external folders for knowledge.
    -   `knowledge_query_subprojects`: Whether to query subprojects for knowledge.
    -   `knowledge_file_ignore`: Comma-separated list of files/directories to ignore for knowledge.
    -   `knowledge_generate_training_dataset`: Whether to generate a training dataset for knowledge.
    -   `save_mentions`: Whether to save mentions.
    -   `watching`: Whether the project is being watched.
    -   `use_knowledge`: Whether to use the knowledge base.
    -   `knowledge_hnsw_M`: Parameter 'M' for HNSW index in knowledge base.
    -   `project_icon`: URL for the project's icon.
    -   `log_ignore`: Comma-separated list of patterns to ignore in logs.
    -   `last_access_time`: Timestamp of the last project access.
    -   `project_scripts`: List of `ProjectScript` objects for custom scripts.
    -   `embeddings_model`: Name of the embeddings model to use.
    -   `llm_model`: Name of the LLM model to use.
    -   `rag_model`: Name of the RAG model to use.
    -   `wiki_model`: Name of the wiki model to use.
    -   `last_error`: Stores the last error message encountered.
    -   `urls`: List of URLs associated with the project.
    -   `repo_url`: URL of the project's repository.
    -   `is_git_root`: Boolean indicating if the project path is a Git root.

-   **Methods**:
    -   `__str__()`: Returns a string representation of the settings.
    -   `get_agent_max_iterations()`: Retrieves the maximum agent iterations from global settings.
    -   `get_llm_settings()`: Gets the AI settings for the LLM model, prioritizing project settings over global ones.
    -   `get_embeddings_settings()`: Gets the AI settings for the embeddings model.
    -   `get_project_settings_file()`: Returns the absolute path to the project's settings file (`project.json`).
    -   `get_project_workspaces()`: Retrieves workspaces associated with the current project.
    -   `from_codx_path()`: Class method to create `CODXJuniorSettings` from a project's `.codx` path.
    -   `from_project_file()`: Class method to load settings from a `project.json` file.
    -   `from_json()`: Class method to create settings from a dictionary.
    -   `get_valid_keys()`: Class method to get valid keys for project settings, excluding computed properties.
    -   `save_project()`: Saves the current project settings to `project.json`. It handles project ID generation and updates the project path if necessary.
    -   `get_sub_projects()`: Finds and returns sub-projects within the current project's directory structure.
    -   `is_valid_project()`: Checks if the project has valid AI settings configured.
    -   `get_dbs()`: Builds and returns database configurations for the project.
    -   `get_ai()`: Builds and returns AI configurations for the project.
    -   `get_project_wiki_path()`: Determines the absolute path to the project wiki.
    -   `get_project_dependencies()`: Parses and returns the list of project dependencies.
    -   `get_log_ai()`: Checks if AI logging is enabled globally.
    -   `get_sub_projects_paths()`: Returns a list of file paths for all sub-projects.
    -   `get_ignore_patterns()`: Generates a list of file/directory patterns to ignore during file operations, including sub-projects and wiki paths.
    -   `is_valid_project_file()`: Checks if a given file path should be ignored based on project settings.
    -   `get_wiki_model()`: Retrieves the wiki model name, prioritizing project settings.
    -   `get_rag_model()`: Retrieves the RAG model name, prioritizing project settings.
    -   `get_project_ai_models()`: Returns the list of available AI models from global settings.
    -   `write_file_resource()`: Placeholder for writing file resources.
    -   `read_file_resource()`: Placeholder for reading file resources.
    -   `delete_file_resource()`: Placeholder for deleting file resources.

### CODXJuniorProject Class

This class inherits from `CODXJuniorSettings` and adds project-specific project-level data.

-   **Fields**:
    -   `metrics`: Dictionary to store project metrics.
    -   `workspaces`: List of workspace configurations for the project.
    -   `users`: List of user information related to the project.
    -   `permissions`: String defining project permissions.

```python /codx/junior/settings.py
import os
import json
import logging
import pathlib
import uuid
import traceback

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from codx.junior.utils.utils import (
  write_file,
  exec_command
)
from codx.junior.model.model import (
    GlobalSettings,
    ProjectScript,
    AISettings,
    AIModel,
    AIProvider,
    AILLMModelSettings,
    AIModelType
)

logger = logging.getLogger(__name__)

ROOT_PATH = os.path.dirname(__file__)
GLOBAL_SETTINGS = None
HOME=os.environ.get("HOME")

GLOBAL_SETTINGS_FOLDER=os.environ.get("CODX_JUNIOR_CONFIG_FOLDER", HOME)
GLOBAL_SETTINGS_PATH=f"{GLOBAL_SETTINGS_FOLDER}/global_settings.json"

def backup_up_global_settings():
    backup_dir = os.path.join(os.path.dirname(GLOBAL_SETTINGS_PATH), "codx-junior-backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create a backup file name with the current date and time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"global_settings_backup_{timestamp}.json")
    logger.info("Saving global_settings backup: %s", backup_file)
    try:
        with open(GLOBAL_SETTINGS_PATH, "r") as f:
            settings_data = f.read()
        
        with open(backup_file, "w") as f:
            f.write(settings_data)
    except Exception as ex:
        logger.error(f"Error backing up global settings: {ex}")

    try:        
        # Maintain only the last 20 backups
        backups = sorted(pathlib.Path(backup_dir).glob("global_settings_backup_*.json"), key=os.path.getmtime)
        if len(backups) > 20:
            for old_backup in backups[:-20]:
                old_backup.unlink()
    except Exception as ex:
        logger.error(f"Error cleaning up global backup settings: {ex}")


logger.info(f"GLOBAL_SETTINGS_PATH is: {GLOBAL_SETTINGS_PATH}")

CODX_JUNIOR_SETTINGS_COMPUTED_PROPERTIES = ["codx_path", "metrics", "users", "is_git_root"]

def get_provider_settings(ai_provider: str, global_settings = None) -> AIProvider:
    global_settings = global_settings or GLOBAL_SETTINGS
    ai_provider_settings = [p for p in global_settings.ai_providers if p.name == ai_provider]
    if not ai_provider_settings:
        raise Exception(f"LLM AI provider not found: {ai_provider}")
    
    ai_provider = ai_provider_settings[0]
    ai_provider.api_url = os.path.expandvars(ai_provider.api_url or "")
    ai_provider.api_key = os.path.expandvars(ai_provider.api_key or "")

    return ai_provider

def get_model(llm_model: str, global_settings = None) -> AIModel:
    global_settings = global_settings or GLOBAL_SETTINGS
    return next((m for m in global_settings.ai_models if m.name == llm_model or m.ai_model == llm_model), None)

def save_model(model: AIModel, global_settings = None) -> AIModel:
    global_settings = read_global_settings()
    global_settings.ai_models = [m for m in global_settings.ai_models if m.name != model.name] + [model]
    write_global_settings(global_settings=global_settings)

def get_model_settings(llm_model: str, global_settings = None) -> AISettings:
    global_settings = global_settings or GLOBAL_SETTINGS
    model_settings = get_model(llm_model, global_settings)

    if not model_settings:
        raise Exception(f"LLM model not found: {llm_model}")
    model: AIModel = model_settings
    provider = get_provider_settings(model.ai_provider, global_settings=global_settings)
    ai_settings = AISettings(
        **model.settings.__dict__,
        provider=provider.provider,
        api_url=provider.api_url,
        api_key=provider.api_key,
        model=model.ai_model or model.name,
        model_type=model.model_type,
        system=model.system,
        prompt_template=model.prompt_template,
        url=model.url
    )
    return ai_settings

def read_global_settings():
    global GLOBAL_SETTINGS
    try:
        with open(GLOBAL_SETTINGS_PATH) as f:
            GLOBAL_SETTINGS = GlobalSettings(**json.loads(f.read()))
    except Exception as ex:
        logger.error(f"Error {ex} loading global settings from {GLOBAL_SETTINGS_PATH}")
        GLOBAL_SETTINGS = GlobalSettings()
        write_global_settings(GLOBAL_SETTINGS)
    return GLOBAL_SETTINGS


def write_global_settings(global_settings: GlobalSettings):
    global GLOBAL_SETTINGS
    logger.exception(f"WRITE GLOBAL_SETTINGS ({GLOBAL_SETTINGS_PATH}): {global_settings}, \n{traceback.format_stack()}")
    try:
        global_settings_data = json.dumps(global_settings.dict())

        backup_up_global_settings()
        
        with open(GLOBAL_SETTINGS_PATH, "w") as f:
            f.write(global_settings_data)

        if global_settings.git.username:
            exec_command(
                f'git config --global user.name "{global_settings.git.username}"'
            )
        if global_settings.git.email:
            exec_command(f'git config --global user.email "{global_settings.git.email}"')

        GLOBAL_SETTINGS = global_settings
    except Exception as ex:
        logger.exception(f"Error saving global settings: {ex}: \n {global_settings}")

def get_oauth_provider(oauth_provider: str):
    global_settings = read_global_settings()
    return next((provider for provider in global_settings.oauth_providers \
                if provider.name == oauth_provider), None)

read_global_settings()
# logger.info(f"GLOBAL_SETTINGS: {GLOBAL_SETTINGS}")


class DevOpsRepository(BaseModel):
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        
class ProjectResource(BaseModel):
    resource_id: str = None
    creation_date: datetime = datetime.now()
    metadata: Optional[dict] = None
    content: Optional[List] = None

class CODXJuniorSettings(BaseModel):
    project_id: Optional[str] = Field(default=None)

    project_name: Optional[str] = Field(default=None)
    project_path: Optional[str] = Field(default="")
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
        return GLOBAL_SETTINGS.agent_settings.max_agent_iteractions

    def get_llm_settings(self, llm_model: str = None) -> AISettings:
        if not llm_model:
            llm_model = self.llm_model 
        if not llm_model:
            llm_model = GLOBAL_SETTINGS.llm_model

        return get_model_settings(llm_model)   

    def get_embeddings_settings(self) -> AISettings:
        embeddings_model = self.embeddings_model 
        if not embeddings_model:
            embeddings_model = GLOBAL_SETTINGS.embeddings_model

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
            if not settings.project_path or settings.project_path[0] != "/":
                settings.project_path = base.project_path
            # if settings.project_path[0] == '.': # relative
            #     resolve_path = os.path.join(settings.codx_path, settings.project_path)
            #     settings.project_path = os.path.abspath()
            if not settings.project_id:
                return settings.save_project()
            settings.is_git_root = os.path.isdir(f"{settings.project_path}/.git")
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

        return CODXJuniorSettings.from_project_file(path)

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
        return os.path.join(self.project_path, self.project_wiki_path)

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
        if self.project_wiki_path:
            wiki_path = os.path.join(self.project_path, self.project_wiki_path)
            ignore_patterns.append(wiki_path)
        if self.knowledge_file_ignore:
            ignore_patterns = ignore_patterns + \
                            [i.strip() for i  in self.knowledge_file_ignore.split(",")] + \
                            self.get_sub_projects_paths()
        return ignore_patterns

    def is_valid_project_file(self, file_path: str):
        return not [p for p in self.get_ignore_patterns() if p in file_path]

    def get_wiki_model(self):
        return self.wiki_model or GLOBAL_SETTINGS.wiki_model

    def get_rag_model(self):
        return self.rag_model or GLOBAL_SETTINGS.rag_model

    def get_project_ai_models(self):
        return GLOBAL_SETTINGS.ai_models

    def write_file_resource(self, file_path: str, content) -> ProjectResource:
        """Stores a file resource in the project's file resources"""
        pass

    def read_file_resource(self, file_path: str) -> ProjectResource:
        """Reads a file resource in the project's file resources"""
        pass

    def delete_file_resource(self, file_path: str):
        """Deletes a file resource in the project's file resources"""
        pass


class CODXJuniorProject(CODXJuniorSettings):
    metrics: Optional[Dict] = Field(default={})
    workspaces: Optional[List[Dict]] = Field(default=[])
    users: Optional[List[dict]] = Field(default=[])
    permissions: Optional[str] = Field(default="")
```