This document defines various data models used within the codx-api project, primarily for configuration, user management, AI settings, and project-related structures.

### Core Models

*   **ImageUrl**: Represents an image with a URL.
*   **Content**: Defines content with a type (e.g., 'text', 'image') and associated data.
*   **ChatMessage**: Structures a message for chat interactions, including role and content.
*   **Column**: Represents a column in a board, with its name, associated chat IDs, and project ID.
*   **Board**: Defines a project board with a name, description, remote URL, bookmark status, columns, and project ID.
*   **Logprobs**: Stores log probabilities for tokens, useful for analyzing language model outputs.
*   **KnowledgeReloadPath**: Specifies a path for reloading knowledge base data.
*   **KnowledgeDeleteSources**: Lists sources to be deleted from the knowledge base.
*   **KnowledgeSearch**: Defines parameters for searching the knowledge base, including search terms, types, and cutoffs.
*   **Tool**: A general model for tools with a name and description.
*   **CodxJuniorBaseTools**: A specific set of tools available in codx-junior, currently including 'knowledge'.
*   **CommandTool**: Extends the `Tool` model to include a command.

### User and Project Models

*   **ProjectPermission**: Defines permissions a user has for a specific project, including children project access and app-specific permissions.
*   **PRView**: Specifies branches for a pull request view.
*   **CodxUserLogin**: Stores user credentials for login.
*   **CodxUserProjectProfile**: Defines a user's profile within a project, indicating coder and admin privileges.
*   **CodxUser**: Represents a user with details like username, email, avatar, theme, projects, role, token, and GitHub information.

### Profile and API Settings Models

*   **ProfileApiSettings**: Configures API visibility and details for a profile.
*   **Profile**: Represents a user or system profile, including name, URL, avatar, description, category, file matching, content, associated LLM models, tools, tags, API settings, chat mode, and project/chat IDs.

### Data and AI Models

*   **Document**: Represents a document with an ID, page content, and metadata.
*   **LiveEdit**: Stores information for live editing of web content.
*   **OpenAISettings**: Configuration for OpenAI API.
*   **AnthropicAISettings**: Configuration for Anthropic API.
*   **MistralAISettings**: Configuration for Mistral AI.
*   **GitSettings**: Stores Git username and email.
*   **ProjectScript**: Defines a script to be run within a project, including its name, description, script content, status, and execution options.
*   **Bookmark**: Represents a saved bookmark with a name, icon, title, URL, and port.
*   **AIProvider**: Configures an AI service provider, including its name, protocol, API URLs, and keys.
*   **AILLMModelSettings**: Settings specific to Large Language Models (LLMs), such as temperature and context length.
*   **AIEmbeddingModelSettings**: Settings for embedding models, like vector size and chunk size.
*   **AIModelType**: An enumeration for AI model types: 'llm', 'embeddings', 'image'.
*   **AIModel**: A comprehensive model for AI models, including name, type, provider, settings, metadata, and system prompts.

### Workspace and Global Settings Models

*   **WorkspaceApp**: Defines an application within a workspace.
*   **Workspace**: Represents a workspace with an ID, name, description, associated projects, applications, and update information.
*   **AgentSettings**: Settings for AI agents, such as the maximum number of iterations.
*   **OAuthProvider**: Configuration for OAuth authentication providers.

**Default Configurations**:

*   **DEFAULT_WORKSPACE**: A predefined workspace configuration with common applications like Coder, Desktop, and LiteLLM.
*   **OLLAMA_PROVIDER**: Default AI provider configuration for Ollama.
*   **OLLAMA_EMBEDDINGS_MODEL**: Default embedding model configuration.
*   **OLLAMA_KNOWLEDGE_MODEL**: Default knowledge model configuration.

### Plugin and Global Settings

*   **PluginArgument**: Defines an argument for a plugin.
*   **Plugin**: Represents a plugin with its ID, name, description, module path, method, arguments, roles, and extension points. The `async_` field is aliased from `async`.
*   **GlobalSettings**: Contains global application settings, including AI model configurations, Git settings, agent settings, project paths, logging options, bookmarks, AI providers and models, user management, workspace settings, and plugin configurations.

### Screen Model

*   **Screen**: Defines screen resolution settings, including the current resolution and a list of available resolutions.

```python /codx/junior/model/model.py
import os
import regex

from pydantic import BaseModel, Field, constr, validator
from enum import Enum
from datetime import datetime

from typing import List, Dict, Union, Optional

KNOWLEDGE_MODEL = os.environ.get('CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL')
EMBEDDINGS_MODEL = os.environ.get('CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL')

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

class ProjectPermission(BaseModel):
    project_id: str
    permissions: str = Field(description="User permissions for the project", default=[])
    children: Optional[bool] = Field(description="Same access to children projects", default=True)
    apps: Optional[List[str]] = Field(default=[])

class PRView(BaseModel):
    from_branch: Optional[str] = Field(default="")
    to_branch: Optional[str] = Field(default="")

class CodxUserLogin(BaseModel):
    username: Optional[str] = Field(default="")
    password: Optional[str] = Field(default="")
    email: Optional[str] = Field(default="")
    token: Optional[str] = Field(default="")

class CodxUserProjectProfile(BaseModel):
    name: Optional[str] = Field(default="")
    coder: Optional[bool] = Field(description="Can access to coder and change project files", default=False)
    admin: Optional[bool] = Field(description="Can access to project's admin", default=False)

class CodxUser(BaseModel):
    username: Optional[str] = Field(default="")
    email: Optional[str] = Field(default="")
    avatar: Optional[str] = Field(default="")
    theme: Optional[str] = Field(default="dim")
    projects: Optional[List[ProjectPermission]] = Field(default=[])
    role: Optional[str] = Field(description="User role", default="user")
    token: Optional[str] = Field(default="")
    disabled: Optional[bool] = Field(default=False)
    github: Optional[str] = Field(default="")
    apps: Optional[List[str]] = Field(default=[])
    api_key: Optional[str] = Field(default="")
    env: Optional[dict] = Field(default={})
    
class ProfileApiSettings(BaseModel):
    active: bool = Field(description="Model is visible through API", default=False)
    model_name: Optional[str] = Field(description="Model's name", default=None)
    description: Optional[str] = Field(description="Model's description", default=None)

class Profile(BaseModel):
    name: str = Field(default="")
    url: str = Field(default="")
    avatar: str = Field(default="")
    description: str = Field(default="")
    category: str = Field(default="", description="Profile category: global, file, coding, ...")
    file_match: str = Field(default="",
        description="Optional regex to apply profiles based on file absolute path.")
    content: Optional[str] = Field(default=None)
    path: str = Field(default="")
    content_path: str = Field(default="")
    profiles: Optional[List[str]] = Field(default=[])
    llm_model: Optional[str] = Field(default='')
    use_knowledge: Optional[bool] = Field(default=True)
    user: Optional[CodxUser] = Field(default=CodxUser())
    tools: Optional[List[str]] = Field(default=[])
    tags: Optional[List[str]] = Field(default=[])
    api_settings: Optional[ProfileApiSettings] = Field(description="Indicates if the profile is accessible through the LLM API", default=ProfileApiSettings())
    chat_mode: Optional[str] = Field(description="Affects on how conversation works. Like writing a document or chat messages", default=None)
    project_id: Optional[str] = Field(description="Profile's project", default=None)
    chat_id: Optional[str] = Field(default="", description="Unique identifier for chat")

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

class AIProvider(BaseModel):
    name: Optional[str] = Field(default="", description="Provider name") 
    provider: Optional[str] = Field(default="llmfactory", description="OpenAI compatible LLM protocols like: OpenAI, Ollama") 
    api_url: Optional[str] = Field(description="Optional url if provider is remote", default="http://0.0.0.0:11434/v1")
    api_key: Optional[str] = Field(description="Optional api key", default="sk-llmfactory")
    admin_url: Optional[str] = Field(description="Optional url if provider has an admin url", default="")

class AILLMModelSettings(BaseModel):
    temperature: Optional[float] = Field(default=1, description="Model temperature")
    context_length: Optional[int] = Field(default=0)
    merge_messages: Optional[bool] = Field(description="Flat conversation into a single message before sending to model", default=False)
    
class AIEmbeddingModelSettings(BaseModel):
    vector_size: Optional[int] = Field(default=1536, description="Model vector size")
    chunk_size: Optional[int] = Field(default=8190, description="Model chunk_size")

class AIModelType(str, Enum):
    llm = 'llm'
    embeddings = 'embeddings'
    image = 'image'

class AIModel(BaseModel):
    name: str = Field(description="Model name")    
    model_type: AIModelType = Field(description="Model type", default=AIModelType.llm)
    ai_provider: str = Field(description="AI Provider name")
    ai_model: Optional[str] = Field(description="AI Provider's model name", default=None)
    settings: Union[AILLMModelSettings, AIEmbeddingModelSettings] = Field(description="Model settings")
    metadata: Optional[dict] = Field(description="Model's last update date", default={})
    url: Optional[str] = Field(description="Model info", default="")
    system: Optional[str] = Field(description="Model system instructions", default="")
    prompt_template: Optional[str] = Field(description="Model info", default="{ MESSAGE }")

class AISettings(BaseModel):
    provider: Optional[str] = Field(default="") 
    api_url: Optional[str] = Field(default="")
    api_key: Optional[str] = Field(default="")
    model: Optional[str] = Field(default="")
    system: Optional[str] = Field(description="Model system instructions", default="")
    prompt_template: Optional[str] = Field(description="Model info", default="")
    context_length: Optional[int] = Field(default=0)
    temperature: Optional[float] = Field(default=0.8)
    vector_size: Optional[int] = Field(default=1536)
    chunk_size: Optional[int] = Field(default=8190)
    merge_messages: Optional[bool] = Field(default=False)
    model_type: AIModelType = Field(description="Model type", default=AIModelType.llm)
    url: Optional[str] = Field(description="Model info", default="")
    
OLLAMA_PROVIDER = AIProvider(name="llmfactory",
                            provider="llmfactory",
                            api_url=os.environ.get('CODX_JUNIOR_LLMFACTORY_URL'),
                            api_key=os.environ.get('CODX_JUNIOR_LLMFACTORY_KEY'))

OLLAMA_EMBEDDINGS_MODEL = AIModel(name="embeddings",
                                ai_model=EMBEDDINGS_MODEL, 
                                model_type=AIModelType.embeddings,
                                ai_provider="llmfactory",
                                settings=AIEmbeddingModelSettings(chunk_size=2048, vector_size=768),
                                url=f"https://llmfactory.com/library/{EMBEDDINGS_MODEL}")

OLLAMA_KNOWLEDGE_MODEL = AIModel(name="knowledge",
                            ai_model=KNOWLEDGE_MODEL,
                            model_type=AIModelType.llm,
                            ai_provider="llmfactory",
                            settings=AILLMModelSettings(),
                            url=f"https://llmfactory.com/library/{KNOWLEDGE_MODEL}")

class WorkspaceApp(BaseModel):
    id: str = Field(default="")
    name: str = Field(default="")
    description: str = Field(default="")
    icon: str = Field(default="")
    path: str = Field(default="")
    port: Optional[str] = Field(default="")
    is_vnc: Optional[bool] = Field(default=False)
    container_name: str = Field(default="")
    roles: List[str] = Field(default=[])

class Workspace(BaseModel):
    id: str = Field(default="")
    name: str = Field(default="")
    description: str = Field(default="")
    project_ids: List[str] = Field(default=[])
    apps: Optional[List[WorkspaceApp]] = Field(default=[])
    updated_at: Optional[str] = Field(default=None)
    file_path: str = Field(default="")

class AgentSettings(BaseModel):
    max_agent_iteractions: int = 4

class OAuthProvider(BaseModel):
    name: str = Field(default="")
    client_id: str = Field(default="")
    secret: str = Field(default="")
    token_url: str = Field(default="")


DEFAULT_WORKSPACE = Workspace(**{
    "name": "codx-junior",
    "description": "Default codx-junior workspace",
    "file_path": "codx-junior-workspace-default",
    "apps": [
        { 
        "icon": "fa-solid fa-code",
        "name": "Coder",
        "description": "Coder coding environment",
        "path": "/workspace-default/coder/",
        "roles": ["admin"]
        },
        { 
        "icon": "fa-solid fa-desktop",
        "name": "Desktop",
        "description": "Virtual desktop",
        "path": "/workspace-default/preview/index.html",
        "roles": ["admin"]
        },
        { 
        "icon": "https://framerusercontent.com/images/GtfMdzyrMj6FQY6lGLqI6bh2LYM.png",
        "name": "LiteLLM",
        "description": "LiteLLM Models manager",
        "path": "/litellm/ui",
        "roles": ["admin"]
        },
    ],
    "project_ids": ["*"]
})

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
            ```