Here's a high-quality, readable, and well-documented code snippet based on the provided XML data:


```python
import os
import regex

from pydantic import BaseModel, Field, constr, validator
from enum import Enum
from datetime import datetime

from typing import List, Dict, Union, Optional

# Cunningham AI models, these are imported from codx.junior.model.ai_model
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

# Cunningham Profile models, these are imported from codx.junior.model.profile
from codx.junior.model.profile import (
    Profile,
    ProfileApiSettings,
)


class ImageUrl(BaseModel):
    url: str = Field(default="")

@(constr(regex=r'^https?://(www\.)?.{1,100}(?:\.(jpg|png|.gif)$){{2}}(/.*)?$'))
def validate_image_link(link: str):
    raise ValueError("image-link is required")

class Content(BaseModel):
    type: str = Field(default='text')
    text: str = Field(default=None)
    image_url: ImageUrl = Field(default=None)

# Cunningham chat message models, these are imported from codx.junior.model.workspace
from codx.junior.model.workspace import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)

class ChatMessage(BaseModel):
    role: str = Field(default='')
    content: List[Content] = Field(default=[])

# Cunningham column and board models, these are imported from codx.junior.model.model
from codx.junior.model.model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)

class Board(BaseModel):
    name: str = Field(default='')
    description: str = Field(default='')
    remote_url: str = Field(default='')
    bookmark: Optional[bool] = Field(default=False)
    columns: List[Column] = Field(default=[])
    project_id: str = Field(default='')

class Column(BaseModel):
    name: str = Field(default='')
    chat_ids: List[str] = Field(default=[])
    project_id: str = Field(default='')

# Cunningham logger models, these are imported from codx.junior.model.model
from codx.junior.model.model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)

class Logprobs(BaseModel):
    tokens: List[str]
    token_logprobs: List[float]
    top_logprobs: List[Dict[str, float]]
    text_offset: List[int]

# Cunningham KnowledgeReloadPath model
class KnowledgeReloadPath(BaseModel):
    path: str

# Cunningham KnowledgeDeleteSources model
class KnowledgeDeleteSources(BaseModel):
    sources: List[str]

# Cunningham KnowledgeSearch model
from pydantic import BaseModel
from typing import Union

class KnowledgeSearch(BaseModel):
    search_term: str
    search_type: str = Field(default=None)
    document_search_type: str = Field(default=None)
    document_count: int = Field(default=None)
    document_cutoff_score: float = Field(default=None)
    document_cutoff_rag: float = Field(default=None)

# Cunningham tool models, these are imported from codx.junior.model.model
from codx.junior.model.model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)


class Tool(BaseModel):
    name: str = Field(default="")
    description: str = Field(default="")

class CodxJuniorBaseTools(BaseModel):
    knowledge: Tool = Tool(name="knowledge", description="Project's knowledge search")

# Cunningham CommandTool model
from codx.junior.model.model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)

class CommandTool(Tool):
    command: Optional[str] = Field(description="Command", default=None)

# Cunningham PRView model
from codx.junior.model.model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)


class PRView(BaseModel):
    from_branch: Optional[str] = Field(default="")
    to_branch: Optional[str] = Field(default="")

# Cunningham Document model
from codx.junior.model.model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)

class Document(BaseModel):
    id: int = Field(default=None)
    page_content: str
    metadata: dict

# Cunningham LiveEdit model
from codx.junior.model=model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)


class LiveEdit(BaseModel):
    chat_name: str
    html: str
    url: str
    message: str

# Cunningham OpenAISettings model 
class OpenAISettings(BaseModel):
    openai_api_url: Optional[str] = Field(default="")
    openai_api_key: Optional[str] = Field(default="")
    openai_model: Optional[str] = Field(default="gpt-4o")





class AnthropicAISettings(BaseModel):
    anthropic_api_url: Optional[str] = Field(default="")
    anthropic_api_key: Optional[str] = Field(default="")
    anthropic_model: Optional[str] = Field(default="claude-3-5-sonnet-20240620")



# Cunningham MistralAISettings model
class MistralAISettings(BaseModel):
    mistral_api_url: Optional[str] = Field(default="")
    mistral_api_key: Optional[str] = Field(default="")
    mistral_model: Optional[str] = Field(default="codestral-latest")


# Cunningham GitSettings model, these are imported from codx.junior.model.workspace
from codx.junior.model.workspace import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)

class GitSettings(BaseModel):
    username: Optional[str] = Field(default="")
    email: Optional[str] = Field(default="")


# Cunningham ProjectScript model, these are imported from codx.junior.model.model
from codx.junior.model.model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)

class ProjectScript(BaseModel):
    name: str = Field(description="Script name")
    description: str = Field(description="Script name", default="")
    script: str = Field(description="Bash script", default="")
    status: str = Field(description="Script status: running, stopped, error", default="stopped")
    background: bool = Field(description="Script runs in background", default=False)
    restart: bool = Field(description="Script must be restarted if stopped", default=False)
    pid_file_path: str = Field(default="")
    engine: str = Field(default="bash")


# Cunningham Bookmark model
from codx.junior.model.profile import (
    Profile,
    ProfileApiSettings,
)


class Bookmark(BaseModel):
    name: str
    icon: Optional[str] = Field(default="")
    title: Optional[str] = Field(default="")
    url: Optional[str] = Field(default="")
    port: Optional[int] = Field(default=None)

# Cunningham Agent settings model, these are imported from codx.junior.model Ai_model
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
)

class AgentSettings(BaseModel):
    max_agent_iteractions: int = 4


# Cunningham OAuth provider model, these are imported from codx.junior.model.workspace
from codx.junior.model.workspace import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)


class OAuthProvider(BaseModel):
    name: str = Field(default="")
    client_id: str = Field(default="")
    secret: str = Field(default="")
    token_url: str = Field(default="")


# Cunningham PluginArgument model
from pydantic import BaseModel

class PluginArgument(BaseModel):
    name: str
    description: str
    default_value: str


# Cunningham PluginBase model
# Cunningham models from the modules will be imported below, so that they can be referenced by a simple string literal.
from codx.junior.model.plugin import (
    PluginArgumentArgMeta,
    BasePluginModel  # pylint: disable=no-absolute-import
)

class Plugin(BaseModel):
    plugin_id: str
    name: str = Field(default="", alias="name_id")
    description: str = Field("", alias="description_ids")
    module_path: str 
    plugin_path: str
    method: str 
    arguments: List[PluginArgument] = []
    roles: List[str]
    extends: List[str]
    image: Optional[str] = Field(default=None, aligns=True)
    async_: bool = Field(True)

# Cunningham Global model
from pydantic import BaseModel

class GlobalSettings(BaseModel):
    log_ai: bool = False 
    embeddings_model = KNOWLEDGE_MODEL 
    llm_model = KNOWLEDGE_MODEl 
   
    default: dict[str, str] | None)  ## not in codx

    git: GitSettings
    agent_settings: AgentSettings
    projects_root_path: Optional[str]
    log_ignore: List[str] 
=>

    codx_junior_avatar: Optional[str]
    enable_file_manager: bool
    project_scripts: List[ProjectScript]
    bookmarks: List[Bookmark]
    ai_providers:
        OLLAMA_PROVIDER
    agents_provisions: AgentSettings = AgentSettings()
    
    users: List[CodxUser] 
    user_logins:: CodxUserLogin = None   
    secret_key: Optional[str]  # Use alias for encryption key
 
    workspaces: List[Workspace] ## already included in default  
    workspace_start_port: int
    workspace_end_port: int 
    workspace_docker_settings: Any 
    oauth_providers: List[OAuthProvider]

# Cunningham Screen model, these are imported from codx.junior.model.model
from codx.junior.model.model import (
    WorkspaceApp,
    DEFAULT_WORKSPACE,
)


class Screen(BaseModel):
    resolution: str = Field(default='')
    resolutions: List[str] = Field("1920x1080", default=[
        "1024x768",
        "800x600",
        "640x480",
        
        "1366x768",
        ])



```

## Dependencies
**Imports from:** codx/junior/model/user.py, codx/junior/model/ai_model.py, codx/junior/model/profile.py
**Imported by:** codx/junior/ai/__init__.py, codx/junior/ai/ai.py, codx/junior/ai/llmfactory.py, codx/junior/ai/openai_ai.py, codx/junior/ai/vllm_cpu_ai.py, codx/junior/ai/wallet_check.py, codx/junior/api/__init__.py, codx/junior/api/analytics.py, codx/junior/api/github.py, codx/junior/api/global_settings.py, codx/junior/api/knowledge.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/api/users.py, codx/junior/api/views.py, codx/junior/api/wiki.py, codx/junior/api/workspaces.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/context.py, codx/junior/db.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/global_settings.py, codx/junior/knowledge/knowledge_ai_search.py, codx/junior/knowledge/knowledge_db.py, codx/junior/knowledge/knowledge_milvus.py, codx/junior/mentions/mention_manager.py, codx/junior/plugins/plugin_manager.py, codx/junior/profiles/profile_manager.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/settings.py, codx/junior/tools/project_tools.py, codx/junior/utils/chat_utils.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_manager.py, codx/junior/workspace/workspace_manager.py