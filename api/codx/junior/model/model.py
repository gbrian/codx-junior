import os

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

from typing import List, Dict, Union, Optional


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
    knowledge:Tool = Tool(name="knowledge", description="Project's knowledge search")
    
class CodxUser(BaseModel):
    name: str = Field(default="")
    avatar: str = Field(default="")
    personality: str = Field(default="")

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

class Bookmark(BaseModel):
    name: str
    icon: Optional[str] = Field(default="")
    title: Optional[str] = Field(default="")
    url: Optional[str] = Field(default="")
    port: Optional[int] = Field(default=None)

class AIProvider(BaseModel):
    name: Optional[str] = Field(default="", description="Provider name") 
    provider: Optional[str] = Field(default="ollama", description="OpenAI compatible LLM protocols like: OpenAI, Ollama") 
    api_url: Optional[str] = Field(description="Optional url if provider is remote", default="http://0.0.0.0:11434/v1")
    api_key: Optional[str] = Field(description="Optional api key", default="sk-ollama")

class AILLMModelSettings(BaseModel):
    temperature: Optional[float] = Field(default=1, description="Model temperature")
    context_length: Optional[int] = Field(default=0)
    
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
    model_type: AIModelType = Field(description="Model type", default=AIModelType.llm)
    url: Optional[str] = Field(description="Model info", default="")

    
OPENAI_PROVIDER = AIProvider(name="openai", provider="openai")
OPENAI_MODEL = AIModel(name="gpt-4o", ai_provider="openai", model_type=AIModelType.llm, settings=AILLMModelSettings())

OLLAMA_PROVIDER = AIProvider(name="ollama", provider="ollama")
OLLAMA_EMBEDDINGS_MODEL = AIModel(name="nomic-embed-text", 
                                model_type=AIModelType.embeddings,
                                ai_provider="ollama",
                                settings=AIEmbeddingModelSettings(chunk_size=2048, vector_size=768),
                                url="https://ollama.com/library/nomic-embed-text")

OLLAMA_WIKI_MODEL = AIModel(name="deepseek-r1", 
                                model_type=AIModelType.llm,
                                ai_provider="ollama",
                                settings=AILLMModelSettings(),
                                url="https://ollama.com/library/deepseek-r1")


class AgentSettings(BaseModel):
    max_agent_iteractions: int = 4

class GlobalSettings(BaseModel):
    log_ai: bool = Field(default=False)
    
    embeddings_model:  str = Field(default="nomic-embed-text")
    llm_model: str = Field(default="codellama")
    rag_model: str = Field(default="codellama")
    wiki_model: str = Field(default="deepseek-r1")

    git: GitSettings = Field(default=GitSettings())

    agent_settings: AgentSettings = Field(description="Agent settings", default=AgentSettings())

    projects_root_path: str = Field(default='/projects')
    
    log_ignore: List[str] = Field(default=[])

    codx_junior_avatar: str = Field(default="https://img.daisyui.com/images/stock/photo-1534528741775-53994a69daeb.webp")

    enable_file_manager: bool = Field(default=False)

    project_scripts: Optional[List[ProjectScript]] = Field(default=[])

    bookmarks: List[Bookmark] = Field(default=[
        Bookmark(name="Coder", title="code-server", port=os.environ["CODX_JUNIOR_CODER_PORT"]),
        Bookmark(name="Desktop", title="Desktop", port=os.environ["CODX_JUNIOR_NOVNC_PORT"])
    ])

    ai_providers: List[AIProvider] = [
        OPENAI_PROVIDER,
        OLLAMA_PROVIDER
    ]

    ai_models: List[AIModel] = [
      OPENAI_MODEL,
      OLLAMA_WIKI_MODEL,
      OLLAMA_EMBEDDINGS_MODEL
    ]

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
