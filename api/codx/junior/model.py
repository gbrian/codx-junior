import os

from pydantic import BaseModel, Field
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

class Profile(BaseModel):
    name: str = Field(default="")
    url: str = Field(default="")
    description: str = Field(default="")
    category: str = Field(default="", description="Profile category: global, file, coding, ...")
    file_match: str = Field(default="",
        description="Optional regex to apply profiles based on file absolute path.")
    content: Optional[str] = Field(default=None)
    path: str = Field(default="")
    content_path: str = Field(default="")

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

class AISettings(BaseModel):
    provider: Optional[str] = Field(default="") 
    api_url: Optional[str] = Field(default="")
    api_key: Optional[str] = Field(default="")
    model: Optional[str] = Field(default="")
    context_length: Optional[int] = Field(default=0)
    temperature: Optional[float] = Field(default=0.8)

class EmbeddingAISettings(AISettings):
    vector_size: Optional[int] = Field(default=1536)

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

class GlobalSettings(BaseModel):
    openai: OpenAISettings = Field(default=OpenAISettings())
    anthropic_ai: AnthropicAISettings = Field(default=AnthropicAISettings())
    mistral_ai: MistralAISettings = Field(default=MistralAISettings())
    embeddings_ai_settings: EmbeddingAISettings = Field(default=EmbeddingAISettings(provider="openai"))
    git: GitSettings = Field(default=GitSettings())

    log_ai: bool = Field(default=False)
    projects_root_path: str = Field(default='/projects')
    ai_temperature: str = Field(default="0.8")
    ai_provider: str = Field(default="mistral")
    ai_model: str = Field(default="codestral-latest")

    log_ignore: List[str] = Field(default=[])

    codx_junior_avatar: str = Field(default="https://img.daisyui.com/images/stock/photo-1534528741775-53994a69daeb.webp")

    enable_file_manager: bool = Field(default=False)

    project_scripts: Optional[List[ProjectScript]] = Field(default=[])

    bookmarks: List[Bookmark] = Field(default=[
        Bookmark(name="Coder", title="code-server", port=os.environ["CODX_JUNIOR_CODER_PORT"]),
        Bookmark(name="Desktop", title="Desktop", port=os.environ["CODX_JUNIOR_NOVNC_PORT"])
    ])

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
