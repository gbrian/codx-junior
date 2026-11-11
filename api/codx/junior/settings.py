import os
import json
import logging
import pathlib
import uuid
import traceback

from urllib.parse import quote

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
    AISettings,
    MCPServer
)
from codx.junior.traefik.model import TraefikRule

logger = logging.getLogger(__name__)

ROOT_PATH = os.path.dirname(__file__)
HOME=os.environ.get("HOME")

CODX_JUNIOR_SETTINGS_COMPUTED_PROPERTIES = ["codx_path", "metrics", "users", "is_git_root"]

# Folder (relative to the project root unless it starts with "/") where the
# project images are stored: generated images, images uploaded to a chat...
DEFAULT_IMAGES_FOLDER = ".codx/images"

# API prefix that serves the project images folder, see codx/junior/api/images.py
IMAGES_URL_PREFIX = "/api/images"

# Mask used when a project secret (git token) is shown in the UI
GIT_ACCESS_TOKEN_MASK = "••••••••"

# Environment variables checked (in order) when no token is stored in the
# settings, so a container can authenticate without writing the secret to disk
GIT_ACCESS_TOKEN_ENV_VARS = [
    "CODX_JUNIOR_GIT_TOKEN",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITLAB_TOKEN",
    "BITBUCKET_TOKEN",
]
        
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
    # Search (knowledge, wiki, files) runs over the current project plus its
    # children and its dependencies. Disable it to keep every search local.
    search_related_projects: Optional[bool] = Field(default=True)

    # Wiki maintenance. Updates are queued and applied only after the project
    # has been quiet for `wiki_update_debounce_seconds`, capped by
    # `wiki_update_max_delay_seconds` so a long editing session still refreshes.
    wiki_auto_update: Optional[bool] = Field(
        default=True,
        description="Update the project wiki in the background when files change",
    )
    wiki_update_debounce_seconds: Optional[int] = Field(
        default=60,
        description="Seconds of quiet before a queued wiki update runs",
    )
    wiki_update_max_delay_seconds: Optional[int] = Field(
        default=600,
        description="Maximum seconds a queued wiki update may wait while changes keep arriving",
    )
    wiki_assistant_enabled: Optional[bool] = Field(
        default=True,
        description="Enable the documentation AI assistant for this project",
    )
    wiki_search_children: Optional[bool] = Field(
        default=True,
        description="Include child project documentation in wiki search and the assistant",
    )
    wiki_search_depth: Optional[int] = Field(
        default=2,
        description="How many child-project levels wiki search and the assistant may traverse",
    )

    project_preview_url: Optional[str] = Field(default=None)

    # Project atlas: an incremental SQLite index of files, symbols, routes,
    # docs and their graph. It replaces grep/glob/semantic search for project
    # discovery when enabled, and is refreshed from the working tree on demand.
    project_atlas_enabled: Optional[bool] = Field(
        default=True,
        description="Expose the project atlas (map/locate/trace/impact) to agents",
    )
    project_atlas_force: Optional[bool] = Field(
        default=True,
        description=(
            "Hide project_grep/project_glob/project_search from models so "
            "discovery goes through the atlas"
        ),
    )
    project_atlas_max_files: Optional[int] = Field(
        default=5000,
        description="Maximum files indexed by the project atlas",
    )
    project_atlas_ttl_seconds: Optional[int] = Field(
        default=5,
        description="Reuse the freshness check for this many seconds",
    )

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
    guardrail_model: str = Field(default="")

    # Image models. The names are the SAME in the global and the project
    # settings: the global ones are the installation default and these override
    # it per project. Empty means "use the global setting", see
    # get_image_generation_model() and get_image_vision_model().
    #
    # Generating an image (text -> image) and analysing one (image -> text) are
    # two different capabilities, so neither ever falls back to the other's
    # model.
    image_generation_model: Optional[str] = Field(
        default="",
        description=(
            "Project image generation model (text -> image). Empty uses the "
            "global image_generation_model"
        )
    )
    image_vision_model: Optional[str] = Field(
        default="",
        description=(
            "Project image vision model (image -> text). Empty uses the global "
            "image_vision_model"
        )
    )

    # Folder where the project images are stored: generated images, images
    # uploaded to a chat, etc. Relative to the project root unless it starts
    # with "/". Images are project resources, so they live inside the project
    # instead of a global static mount.
    images_folder: Optional[str] = Field(
        default=DEFAULT_IMAGES_FOLDER,
        description=(
            "Folder where the project images are stored (generated images, chat "
            "uploads...). Relative to the project root unless it starts with '/'. "
            "Defaults to '.codx/images'"
        )
    )
    image_max_file_size_mb: Optional[int] = Field(
        default=100,
        description="Maximum size of an image uploaded to the project (MB)"
    )

    last_error: str = Field(default="")

    urls: Optional[List[str]] = Field(default=[])

    repo_url: Optional[str] = Field(default=None)

    mcp_servers: Optional[List[MCPServer]] = Field(default=[], description="List of MCP servers configured for this project")

    # Custom Traefik routers stored with the project (they travel with the
    # project's .codx/project.json to other codx-junior instances). Global rules
    # live in GlobalSettings.traefik_rules instead.
    traefik_rules: List[TraefikRule] = Field(
        default_factory=list,
        description="Custom Traefik rules owned by this project",
    )

    is_git_root: Optional[bool] = Field(default=False)

    # Git PR settings (PRs are handled locally by codx-junior)
    git_pr_branch_prefix: Optional[str] = Field(
        default="codx-junior",
        description="Prefix used when naming PR branches automatically"
    )
    git_worktrees_path: Optional[str] = Field(
        default="",
        description="Folder where PR worktrees are created (absolute or relative to the project path)"
    )

    # Git identity used by codx-junior when it signs commits on this project
    git_user_name: Optional[str] = Field(
        default="",
        description="Git user name used for commits made by codx-junior (falls back to the global git settings)"
    )
    git_user_email: Optional[str] = Field(
        default="",
        description="Git user email used for commits made by codx-junior (falls back to the global git settings)"
    )

    # Git access token (PAT) used to authenticate fetch/pull/push against the
    # project remote. It is a secret: the API must mask it before sending the
    # settings to a client and only admins should be able to change it.
    git_access_token: Optional[str] = Field(
        default="",
        description=(
            "Personal access token (PAT) used to authenticate fetch, pull and push "
            "against the project remote. Supports ${ENV_VAR} references so the "
            "secret can stay out of project.json"
        )
    )

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

    def get_worktrees_path(self) -> str:
        """
        Return the folder used to create PR branches as git worktrees.

        When `git_worktrees_path` is empty a sibling folder of the project is
        used (`<project-parent>/<project-name>-worktrees`), so worktrees never
        pollute the repository working tree.

        Returns:
            Absolute path to the worktrees folder.
        """
        if self.git_worktrees_path:
            if self.git_worktrees_path.startswith("/"):
                return self.git_worktrees_path
            return os.path.join(self.abs_project_path, self.git_worktrees_path)

        project_path = (self.abs_project_path or self.project_path or "").rstrip("/")
        if not project_path:
            return os.path.join(self.codx_path or "", "worktrees")

        return os.path.join(
            os.path.dirname(project_path), f"{os.path.basename(project_path)}-worktrees"
        )

    def get_git_identity(self) -> Dict[str, str]:
        """
        Return the git user name and email configured for this project.

        The project values win over the global ones, so a single project can
        commit with a different author than the rest of the installation. Empty
        values are returned when nothing is configured: the git engine then
        falls back to the repository git configuration.

        Returns:
            Dict with 'name', 'email' and 'source' ('project', 'global' or ''
            when nothing is configured).

        Example:
            >>> settings.git_user_name = "Jane Doe"
            >>> settings.git_user_email = "jane@acme.com"
            >>> settings.get_git_identity()
            {'name': 'Jane Doe', 'email': 'jane@acme.com', 'source': 'project'}
        """
        name = str(self.git_user_name or "").strip()
        email = str(self.git_user_email or "").strip()
        source = "project" if (name or email) else ""

        if name and email:
            return {"name": name, "email": email, "source": source}

        global_git = getattr(get_global_settings(), "git", None)
        global_name = str(getattr(global_git, "username", "") or "").strip()
        global_email = str(getattr(global_git, "email", "") or "").strip()

        if not name and global_name:
            name = global_name
            source = source or "global"
        if not email and global_email:
            email = global_email
            source = source or "global"

        return {"name": name, "email": email, "source": source}

    def get_git_access_token(self) -> str:
        """
        Return the git access token (PAT) used to authenticate remote operations.

        Resolution order:
            1. the project setting (`git_access_token`)
            2. the global git settings (`git.git_access_token`)
            3. the environment (`CODX_JUNIOR_GIT_TOKEN`, `GITHUB_TOKEN`,
               `GH_TOKEN`, `GITLAB_TOKEN`, `BITBUCKET_TOKEN`)

        The stored value may reference an environment variable
        (`${GITHUB_TOKEN}`), so the secret never has to be written into
        `project.json`. A reference to an unset variable is treated as "no
        token" instead of being sent to the remote as a literal.

        Returns:
            Token string, empty when no usable token is configured.

        Example:
            Store the literal token:
                >>> settings.git_access_token = "ghp_1234567890abcdef"
                >>> settings.get_git_access_token()
                'ghp_1234567890abcdef'

            Or read it from the environment (recommended):
                >>> settings.git_access_token = "${GITHUB_TOKEN}"
                >>> settings.get_git_access_token()
                'ghp_1234567890abcdef'
        """
        token = str(self.git_access_token or "").strip()

        if not token:
            global_git = getattr(get_global_settings(), "git", None)
            token = str(getattr(global_git, "git_access_token", "") or "").strip()

        if not token:
            for env_name in GIT_ACCESS_TOKEN_ENV_VARS:
                token = str(os.environ.get(env_name, "") or "").strip()
                if token:
                    break

        if not token:
            return ""

        expanded = os.path.expandvars(token).strip()
        if not expanded or (expanded.startswith("${") and expanded.endswith("}")):
            logger.warning(
                "Git access token references an unset environment variable, ignoring it"
            )
            return ""

        return expanded

    def has_git_access_token(self) -> bool:
        """
        Return True when a usable git access token is configured.

        Safe to expose to any client: it tells the UI whether remote operations
        are authenticated without revealing the secret.
        """
        return bool(self.get_git_access_token())

    def masked_git_access_token(self) -> str:
        """
        Return a masked hint of the git access token, safe to send to the UI.

        Only the last 4 characters are kept, so an admin can recognize which
        token is stored while the secret never leaves the server.

        Returns:
            Hint such as '••••••••a1b2', empty when no token is configured.

        Example:
            >>> settings.masked_git_access_token()
            '••••••••a1b2'
        """
        token = self.get_git_access_token()
        if not token:
            return ""
        if len(token) <= 8:
            return GIT_ACCESS_TOKEN_MASK
        return f"{GIT_ACCESS_TOKEN_MASK}{token[-4:]}"

    def get_active_mcp_servers(self) -> List[MCPServer]:
        """Get list of active MCP servers."""
        return [server for server in self.mcp_servers if server.active]

    def get_mcp_server_by_name(self, name: str) -> Optional[MCPServer]:
        """Get MCP server by name."""
        return next((server for server in self.mcp_servers if server.name == name), None)

    def get_images_folder(self) -> str:
        """
        Return the configured images folder (relative or absolute).

        Returns:
            The configured folder, `.codx/images` when nothing is set.

        Example:
            >>> settings.images_folder = "assets/images"
            >>> settings.get_images_folder()
            'assets/images'
        """
        return (self.images_folder or "").strip() or DEFAULT_IMAGES_FOLDER

    def get_images_folder_path(self) -> str:
        """
        Return the absolute path of the project images folder.

        Created on demand by the callers (`ImageEngine`, images router).

        Returns:
            Absolute, normalized folder path.

        Example:
            >>> settings.abs_project_path = "/projects/app"
            >>> settings.images_folder = ".codx/images"
            >>> settings.get_images_folder_path()
            '/projects/app/.codx/images'
        """
        folder = self.get_images_folder()
        if folder.startswith("/"):
            return os.path.normpath(folder)
        if folder.startswith("./"):
            folder = folder[2:]
        return os.path.normpath(os.path.join(self.abs_project_path or "", folder))

    def get_image_relative_path(self, absolute_path: str) -> str:
        """
        Return the path of an image relative to the project root.

        Image metadata stores project-relative paths, so the project can be
        moved or cloned without breaking the references.

        Args:
            absolute_path: Absolute path of the image file.

        Returns:
            Path relative to the project root, the absolute path when it cannot
            be made relative, or an empty string for an empty input.

        Example:
            >>> settings.get_image_relative_path("/projects/app/.codx/images/a.png")
            '.codx/images/a.png'
        """
        if not absolute_path:
            return ""
        if not absolute_path.startswith("/"):
            return absolute_path
        project_path = self.abs_project_path or ""
        if project_path:
            try:
                return os.path.relpath(absolute_path, project_path)
            except ValueError:
                logger.debug("Cannot make '%s' relative to '%s'", absolute_path, project_path)
        return absolute_path

    def get_image_url(self, relative_path: str) -> str:
        """
        Build the URL that serves a file stored in the images folder.

        The URL carries the ``codx_path`` query parameter because the API
        resolves the project from it: a browser request made by an
        ``<img src="...">`` does not send the ``x-codx-path`` header.

        Args:
            relative_path: Path relative to the images folder, e.g.
                ``generated/a1b2c3.png``.

        Returns:
            URL such as ``/api/images/generated/a1b2c3.png?codx_path=%2Fp%2F.codx``.

        Example:
            >>> settings.codx_path = "/projects/app/.codx"
            >>> settings.get_image_url("generated/a1b2c3.png")
            '/api/images/generated/a1b2c3.png?codx_path=%2Fprojects%2Fapp%2F.codx'
        """
        path = (relative_path or "").lstrip("/")
        url = f"{IMAGES_URL_PREFIX}/{path}"
        if self.codx_path:
            url = f"{url}?codx_path={quote(self.codx_path, safe='')}"
        return url

    def get_image_max_file_size_mb(self) -> int:
        """Return the maximum size (MB) allowed for an uploaded image."""
        try:
            return max(1, int(self.image_max_file_size_mb or 0))
        except (TypeError, ValueError):
            return 100

    def _resolve_image_model(self, project_value: str, global_attr: str) -> str:
        """
        Resolve an image model: the project value first, then the global one.

        Both scopes use the same field name, so the caller only has to pass its
        own value plus the name of the field to read from the global settings.

        Args:
            project_value: Value stored in the project settings.
            global_attr: Name of the field in ``GlobalSettings``.

        Returns:
            The resolved model name, empty string when neither scope sets it.
        """
        value = (project_value or "").strip()
        if value:
            return value

        global_value = getattr(get_global_settings(), global_attr, "") or ""
        return global_value.strip()

    def get_image_generation_model(self) -> str:
        """
        Resolve the image GENERATION model (text -> image).

        Resolution order (first non-empty wins):
            1. project `image_generation_model` (override)
            2. global `image_generation_model` (default)

        The vision model is a different capability and is never used as a
        fallback here.

        Returns:
            Model name, empty string when no image generation model is configured.

        Example:
            Only the global default is set:
                >>> # global_settings.json -> image_generation_model: "gemini-3.1-flash-lite-image"
                >>> settings.get_image_generation_model()
                'gemini-3.1-flash-lite-image'

            The project overrides it:
                >>> settings.image_generation_model = "dall-e-3"
                >>> settings.get_image_generation_model()
                'dall-e-3'
        """
        return self._resolve_image_model(
            project_value=self.image_generation_model,
            global_attr="image_generation_model",
        )

    def get_image_vision_model(self) -> str:
        """
        Resolve the image VISION model (image -> text).

        Resolution order (first non-empty wins):
            1. project `image_vision_model` (override)
            2. global `image_vision_model` (default)

        The generation model is a different capability and is never used as a
        fallback here.

        Returns:
            Model name, empty string when no image vision model is configured.

        Example:
            Only the global default is set:
                >>> # global_settings.json -> image_vision_model: "gpt-4o"
                >>> settings.get_image_vision_model()
                'gpt-4o'

            The project overrides it:
                >>> settings.image_vision_model = "gemini-3.1-flash"
                >>> settings.get_image_vision_model()
                'gemini-3.1-flash'
        """
        return self._resolve_image_model(
            project_value=self.image_vision_model,
            global_attr="image_vision_model",
        )

    def is_image_generation_enabled(self) -> bool:
        """Check if image generation is enabled (a generation model resolves)."""
        return bool(self.get_image_generation_model())

    def is_image_vision_enabled(self) -> bool:
        """Check if image vision is enabled (a vision model resolves)."""
        return bool(self.get_image_vision_model())

    def get_image_generation_settings(self) -> AISettings:
        """Get AI settings for the resolved image generation model."""
        image_generation_model = self.get_image_generation_model()
        if not image_generation_model:
            return AISettings()
        return get_model_settings(image_generation_model)

    def get_image_vision_settings(self) -> AISettings:
        """Get AI settings for the resolved image vision model."""
        image_vision_model = self.get_image_vision_model()
        if not image_vision_model:
            return AISettings()
        return get_model_settings(image_vision_model)

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

    def get_dependency_names(self) -> List[str]:
        """
        Return the configured dependency project names as a clean list.

        The value is persisted as a comma separated string (the legacy format
        that `.codx/project.json` files and the client store already use), so it
        is normalized here: entries are trimmed, empty ones dropped and
        duplicates removed while keeping the declared order.
        """
        if not self.project_dependencies:
            return []
        names: List[str] = []
        for raw_name in self.project_dependencies.split(","):
            name = (raw_name or "").strip()
            if name and name not in names:
                names.append(name)
        return names

    def get_project_dependencies(self):
        """Deprecated alias of :meth:`get_dependency_names`."""
        return self.get_dependency_names()

    def _dependency_candidate_paths(self, name: str) -> List[str]:
        """
        Folders where a dependency name may live, most specific first.

        A dependency is stored by name, so it can be a folder next to the
        project ("company-commercial" beside "website"), an absolute path or a
        folder inside the project itself.
        """
        if os.path.isabs(name):
            return [name]
        candidates: List[str] = []
        if self.abs_project_path:
            parent_path = os.path.dirname(os.path.normpath(self.abs_project_path))
            if parent_path:
                candidates.append(os.path.join(parent_path, name))
            candidates.append(os.path.join(self.abs_project_path, name))
        return candidates

    def find_dependency_project(self, name: str) -> Optional["CODXJuniorSettings"]:
        """
        Resolve one dependency name to its project settings.

        Returns ``None`` when the name points to no codx-junior project. A
        project is recognized by its `.codx/project.json` file, so an arbitrary
        folder or a library name never turns into a "project".
        """
        for candidate in self._dependency_candidate_paths(name):
            project_file = os.path.join(candidate, ".codx", "project.json")
            if not os.path.isfile(project_file):
                continue
            try:
                return CODXJuniorSettings.from_project_file(project_file)
            except Exception as ex:
                logger.warning(
                    "Project '%s': dependency '%s' could not be loaded: %s",
                    self.project_name, name, ex,
                )
        return None

    def get_dependency_projects(self) -> List["CODXJuniorSettings"]:
        """
        Resolve the configured dependencies to real projects.

        Names that do not resolve are skipped (and logged) so a stale entry
        never breaks a search; the settings UI shows them as a warning.
        """
        dependencies: List["CODXJuniorSettings"] = []
        seen = {self.codx_path}
        for name in self.get_dependency_names():
            project = self.find_dependency_project(name)
            if not project:
                logger.warning(
                    "Project '%s': dependency '%s' does not match any project",
                    self.project_name, name,
                )
                continue
            if project.codx_path in seen:
                continue
            seen.add(project.codx_path)
            dependencies.append(project)
        return dependencies

    def get_related_projects(
        self,
        include_children: bool = True,
        include_dependencies: bool = True,
    ) -> List["CODXJuniorSettings"]:
        """
        Projects searched together with this one: children + dependencies.

        The current project is never part of the result (callers add it) and
        the list is deduplicated by `codx_path`, so a project that is both a
        child and a declared dependency is searched only once. Returns an empty
        list when `search_related_projects` is disabled.
        """
        if not self.search_related_projects:
            return []
        candidates: List["CODXJuniorSettings"] = []
        if include_children:
            candidates.extend(self.get_sub_projects())
        if include_dependencies:
            candidates.extend(self.get_dependency_projects())

        related: List["CODXJuniorSettings"] = []
        seen = {self.codx_path}
        for project in candidates:
            if project.codx_path in seen:
                continue
            seen.add(project.codx_path)
            related.append(project)
        return related

    def get_log_ai(self):
        return get_global_settings().log_ai

    def get_sub_projects_paths(self):
        sub_projects = self.get_sub_projects()
        return [project.abs_project_path for project in sub_projects]


    def get_ignore_patterns(self):
        # `.codx` is the control plane (tasks, profiles, sessions, chats, db):
        # it is never codebase content and must never be indexed as such.
        ignore_patterns = [".git", ".codx", "node_modules"]
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

    def get_guardrail_model(self):
        return self.guardrail_model or get_global_settings().guardrail_model

    def get_project_ai_models(self):
        return get_global_settings().ai_models


class CODXJuniorProject(CODXJuniorSettings):
    metrics: Optional[Dict] = Field(default={})
    workspaces: Optional[List[Dict]] = Field(default=[])
    users: Optional[List[dict]] = Field(default=[])
    permissions: Optional[str] = Field(default="")