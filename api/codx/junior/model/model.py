import os
import regex

from pydantic import BaseModel, Field, constr, validator
from enum import Enum
from datetime import datetime

from typing import List, Dict, Union, Optional

# ---------------------------------------------------------------------------
# Import user models from dedicated module
# ---------------------------------------------------------------------------
from codx.junior.model.user import (
    CodxUserLogin,
    CodxUserProjectProfile,
    CodxUser,
)

# ---------------------------------------------------------------------------
# Import AI models from dedicated module
# ---------------------------------------------------------------------------
from codx.junior.model.ai_model import (
    AIProvider,
    AILLMModelSettings,
    AIEmbeddingModelSettings,
    AIModelType,
    AIModel,
    AISettings,
    OLLAMA_PROVIDER,
    OLLAMA_EMBEDDINGS_MODEL,
    OLLAMA_KNOWLEDGE_MODEL,
    KNOWLEDGE_MODEL,
    EMBEDDINGS_MODEL,
)

# ---------------------------------------------------------------------------
# Import profile models from dedicated module
# ---------------------------------------------------------------------------
from codx.junior.model.profile import (
    Profile,
    ProfileApiSettings,
)

# ---------------------------------------------------------------------------
# Import workspace models from dedicated module
# ---------------------------------------------------------------------------
from codx.junior.model.workspace import (
    Workspace,
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)

# ---------------------------------------------------------------------------
# Import image models from dedicated module
# ---------------------------------------------------------------------------
from codx.junior.model.image_model import (
    ImageGenerationRequest,
    ImageAnalysisRequest,
    ImageMetadata,
    ImageGenerationResponse,
    ImageAnalysisResponse,
)


class ImageUrl(BaseModel):
    url: str = Field(default="")

class Content(BaseModel):
    type: str = Field(default='text')
    text: str = Field(default=None)
    image_url: ImageUrl = Field(default=None)

class ChatMessage(BaseModel):
    role: str = Field(default='')
    content: List[Content] = Field(default=[])

class Column(BaseModel):
    name: str = Field(default='')
    chat_ids: List[str] = Field(default=[])
    project_id: str = Field(default='')

class Board(BaseModel):
    name: str = Field(default='')
    description: str = Field(default='')
    remote_url: str = Field(default='')
    bookmark: Optional[bool] = Field(default=False)
    columns: List[Column] = Field(default=[])
    project_id: str = Field(default='')

class Logprobs(BaseModel):
    tokens: List[str]
    token_logprobs: List[float]
    top_logprobs: List[Dict[str, float]]
    text_offset: List[int]

class KnowledgeReloadPath(BaseModel):
    path: str

class KnowledgeDeleteSources(BaseModel):
    sources: List[str]

class KnowledgeSearch(BaseModel):
    search_term: str
    search_type: str = Field(default=None)
    document_search_type: str = Field(default=None)
    document_count: int = Field(default=None)
    document_cutoff_score: float = Field(default=None)
    document_cutoff_rag: float = Field(default=None)

class Tool(BaseModel):
    name: str = Field(default="")
    description: str = Field(default="")

class CodxJuniorBaseTools(BaseModel):
    knowledge: Tool = Tool(name="knowledge", description="Project's knowledge search")

class CommandTool(Tool):
    command: Optional[str] = Field(description="Command", default=None)

class PRView(BaseModel):
    from_branch: Optional[str] = Field(default="")
    to_branch: Optional[str] = Field(default="")

class Document(BaseModel):
    id: int = Field(default=None)
    page_content: str
    metadata: dict

class LiveEdit(BaseModel):
    chat_name: str
    html: str
    url: str
    message: str

class OpenAISettings(BaseModel):
    openai_api_url: Optional[str] = Field(default="")
    openai_api_key: Optional[str] = Field(default="")
    openai_model: Optional[str] = Field(default="gpt-4o")
    
class AnthropicAISettings(BaseModel):
    anthropic_api_url: Optional[str] = Field(default="")
    anthropic_api_key: Optional[str] = Field(default="")
    anthropic_model: Optional[str] = Field(default="claude-3-5-sonnet-20240620")

class MistralAISettings(BaseModel):
    mistral_api_url: Optional[str] = Field(default="")
    mistral_api_key: Optional[str] = Field(default="")
    mistral_model: Optional[str] = Field(default="codestral-latest")

class GitSettings(BaseModel):
    username: Optional[str] = Field(default="")
    email: Optional[str] = Field(default="")

class ProjectScript(BaseModel):
    name: str = Field(description="Script name")
    description: str = Field(description="Script name", default="")
    script: str = Field(description="Bash script", default="")
    status: str = Field(description="Script status: running, stopped, error", default="stopped")
    background: bool = Field(description="Script runs in background", default=False)
    restart: bool = Field(description="Script must be restarted if stopped", default=False)
    pid_file_path: str = Field(default="")
    engine: str = Field(default="bash")

class Bookmark(BaseModel):
    name: str
    icon: Optional[str] = Field(default="")
    title: Optional[str] = Field(default="")
    url: Optional[str] = Field(default="")
    port: Optional[int] = Field(default=None)

class AgentSettings(BaseModel):
    max_agent_iteractions: int = 4

class OAuthProvider(BaseModel):
    name: str = Field(default="")
    client_id: str = Field(default="")
    secret: str = Field(default="")
    token_url: str = Field(default="")

class MCPServer(BaseModel):
    """Model representing a Model Context Protocol (MCP) server configuration."""
    name: str = Field(description="Name of the MCP server")
    url: str = Field(description="URL/endpoint of the MCP server")
    api_key: Optional[str] = Field(default="", description="API key for authentication")
    active: bool = Field(default=True, description="Whether the MCP server is active")

# Define the PluginArgument model
class PluginArgument(BaseModel):
    name: str
    description: str
    default_value: str

# Define the Plugin model with an async property
class Plugin(BaseModel):
    plugin_id: str
    name: str
    description: str
    module_path: str
    plugin_path: str
    method: str
    arguments: List[PluginArgument]
    roles: List[str]
    extends: List[str]
    image: Optional[str] = Field(default=None)
    async_: bool = Field(default=False, alias="async")  # Use alias for async


class GlobalSettings(BaseModel):
    log_ai: bool = Field(default=True)
    
    embeddings_model: str = Field(default=OLLAMA_EMBEDDINGS_MODEL.name)
    llm_model: str = Field(default=OLLAMA_KNOWLEDGE_MODEL.name)
    rag_model: str = Field(default=OLLAMA_KNOWLEDGE_MODEL.name)
    wiki_model: str = Field(default=OLLAMA_KNOWLEDGE_MODEL.name)
    vision_model: str = Field(default=OLLAMA_KNOWLEDGE_MODEL.name)
    image_model: str = Field(default=OLLAMA_KNOWLEDGE_MODEL.name)

    git: GitSettings = Field(default=GitSettings())

    agent_settings: AgentSettings = Field(description="Agent settings", default=AgentSettings())

    projects_root_path: Optional[str] = Field(default=None)
    
    log_ignore: List[str] = Field(default=[])

    codx_junior_avatar: Optional[str] = Field(default="https://img.daisyui.com/images/stock/photo-1534528741775-53994a69daeb.webp")

    enable_file_manager: Optional[bool] = Field(default=False)

    project_scripts: Optional[List[ProjectScript]] = Field(default=[])

    bookmarks: List[Bookmark] = Field(default=[
    ])

    ai_providers: List[AIProvider] = [
        OLLAMA_PROVIDER
    ]

    ai_models: List[AIModel] = [
      OLLAMA_KNOWLEDGE_MODEL,
      OLLAMA_EMBEDDINGS_MODEL
    ]

    users: Optional[List[CodxUser]] = Field(default=[CodxUser(username="admin", role="admin", avatar="/only_icon.png")])
    user_logins: Optional[List[CodxUserLogin]] = Field(default=[])
    secret: Optional[str] = Field(description="Encription secret", default="codx-junior-rules")

    workspaces: Optional[List[Workspace]] = Field(default=[DEFAULT_WORKSPACE])
    workspace_start_port: Optional[int] = Field(default=16000)
    workspace_end_port: Optional[int] = Field(default=17000)
    workspace_docker_settings: Optional[dict] = Field(default={})

    oauth_providers: Optional[List[OAuthProvider]] = Field(default=[])

    env: Optional[dict] = Field(default={})

    plugins: List[Plugin] = Field(default=[])

    chat_global_instructions: str = Field(default="")
    
    
class Screen(BaseModel):
    resolution: str = Field(default='')
    resolutions: List[str] = Field(default=[
      "1920x1080",
      "1920x1200",
      "1600x1200",
      "1680x1050",
      "1400x1050",
      "1360x768",
      "1280x1024",
      "1280x960",
      "1280x800",
      "1280x720",
      "1024x768",
      "800x600",
      "640x480"
    ])