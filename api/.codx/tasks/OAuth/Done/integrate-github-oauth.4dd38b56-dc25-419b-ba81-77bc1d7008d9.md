# [[{"id": "4dd38b56-dc25-419b-ba81-77bc1d7008d9", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/model/model.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Integrate github oauth", "description": "The user provided a Python script that defines various models using Pydantic to manage configurations and data for a project. They specifically requested the addition of an OAuth provider list to the global settings, specifying the need for attributes like name, client_id, and secret. The script was updated accordingly to include an `OAuthProvider` model and a corresponding field in the `GlobalSettings` class. The modified script encapsulates various configurations, AI models, providers, user profiles, and other settings pertinent to the project's functionality. The response was formatted to adhere to the specified file and path guidelines provided by the user.", "created_at": "2025-08-30 14:15:50.876894", "updated_at": "2025-08-30T16:59:37.359481", "mode": "task", "kanban_id": "", "column_id": "", "board": "OAuth", "column": "Done", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/OAuth/ToDo/integrate-github-oauth.4dd38b56-dc25-419b-ba81-77bc1d7008d9.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "ecb41f24-97a4-4b83-bf77-722fe2520d32", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 14:15:50.874876", "updated_at": "2025-08-30 14:15:50.874912", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Add OAuth provider list to global settings with:
* name
* client_id
* secret
## [[{"doc_id": "cead20e1-00fe-47ad-9e0b-8b1ec0ed8604", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 14:15:50.874876", "updated_at": "2025-08-30 14:15:50.874912", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
Add OAuth provider list to global settings with:
* name
* client_id
* secret
                    Create new document based on user comments.
                    User comments:
                    Add OAuth provider list to global settings with:
* name
* client_id
* secret
                    Important: Always return the markdown document without any comments before or after, to keep it clean.
## [[{"doc_id": "ac8eceb4-7c92-4b4b-b704-c829016d8345", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-08-30 14:15:50.874876", "updated_at": "2025-08-30 14:15:50.874912", "images": [], "files": [], "meta_data": {"time_taken": 82.45687913894653, "first_chunk_time_taken": 0.00020766258239746094, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
```python /shared/codx-junior/api/codx/junior/model/model.py
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

class Board(BaseModel):
    name: str = Field(default='')
    description: str = Field(default='')
    remote_url: str = Field(default='')
    columns: List[Column] = Field(default=[])

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
    
class ProjectPermission(BaseModel):
    project_id: str
    permissions: str = Field(description="User permissions for the project", default=[])

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
    tools: Optional[List[Tool]] = Field(default=[])
    tags: Optional[List[str]] = Field(default=[])
    api_settings: Optional[ProfileApiSettings] = Field(description="Indicates if the profile is accessible through the LLM API", default=ProfileApiSettings())
    chat_mode: Optional[str] = Field(description="Affects on how conversation works. Like writing a document or chat messages", default=None)

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

class AIModel(BaseModel):
    name: str = Field(description="Model name")    
    model_type: AIModelType = Field(description="Model type", default=AIModelType.llm)
    ai_provider: str = Field(description="AI Provider name")
    ai_model: Optional[str] = Field(description="AI Provider's model name", default=None)
    settings: Union[AILLMModelSettings, AIEmbeddingModelSettings] = Field(description="Model settings")
    metadata: Optional[dict] = Field(description="Model's last update date", default={})
    url: Optional[str] = Field(description="Model info", default="")

class AISettings(BaseModel):
    provider: Optional[str] = Field(default="") 
    api_url: Optional[str] = Field(default="")
    api_key: Optional[str] = Field(default="")
    model: Optional[str] = Field(default="")
    context_length: Optional[int] = Field(default=0)
    temperature: Optional[float] = Field(default=0.8)
    vector_size: Optional[int] = Field(default=1536)
    chunk_size: Optional[int] = Field(default=8190)
    merge_messages: Optional[bool] = Field(default=False)
    model_type: AIModelType = Field(description="Model type", default=AIModelType.llm)
    url: Optional[str] = Field(description="Model info", default="")
    
OLLAMA_PROVIDER = AIProvider(name="llmfactory",
                            provider="llmfactory",
                            api_url=os.environ.get('CODX_JUNIOR_LLMFACTORY_API'),
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

class Workspace(BaseModel):
    id: str = Field(default="")
    name: str = Field(default="")
    description: str = Field(default="")
    project_ids: List[str] = Field(default=[])
    workspace_port: Optional[int] = Field(default=0)
    workspace_start_port: Optional[int] = Field(default=0)
    workspace_end_port: Optional[int] = Field(default=0)
    updated_at: Optional[str] = Field(default=None)    

class AgentSettings(BaseModel):
    max_agent_iteractions: int = 4

class OAuthProvider(BaseModel):
    name: str
    client_id: str
    secret: str

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
        Bookmark(name="Coder", title="code-server", port=os.environ["CODX_JUNIOR_CODER_PORT"]),
        Bookmark(name="Desktop", title="Desktop", port=os.environ["CODX_JUNIOR_NOVNC_PORT"])
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

    workspaces: Optional[List[Workspace]] = Field(default=[])
    workspace_start_port: Optional[int] = Field(default=16000)
    workspace_end_port: Optional[int] = Field(default=17000)
    workspace_docker_settings: Optional[dict] = Field(default={})

    oauth_providers: Optional[List[OAuthProvider]] = Field(default=[])
    
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