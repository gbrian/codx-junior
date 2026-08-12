import os
from pydantic import BaseModel, Field
from enum import Enum
from typing import Union, Optional, List

class AIProvider(BaseModel):
    name: Optional[str] = Field(default="", description="Provider name") 
    provider: Optional[str] = Field(default="llmfactory", description="OpenAI compatible LLM protocols like: OpenAI, Ollama") 
    api_url: Optional[str] = Field(description="Optional url if provider is remote", default="http://0.0.0.0:11434/v1")
    api_key: Optional[str] = Field(description="Optional api key", default="sk-llmfactory")
    admin_url: Optional[str] = Field(description="Optional url if provider has an admin url", default="")
    pricing_url: Optional[str] = Field(description="Optional url to the provider's pricing page", default="")
    input_k_tokens_cxjcoins: Optional[float] = Field(
        description="Cost in cxjcoins per 1K tokens at provider level. Applies to all models unless overridden at model level.",
        default=None
    )
    output_k_tokens_cxjcoins: Optional[float] = Field(
        description="Cost in cxjcoins per 1K tokens at provider level. Applies to all models unless overridden at model level.",
        default=None
    )
    price_list: Optional[List["AIModelPrice"]] = Field(
        description="List of model prices fetched from the provider's pricing page.",
        default=[]
    )

class AIModelPrice(BaseModel):
    model_name: str = Field(description="Model name as listed by the provider")
    input_price_per_1k_tokens: float = Field(description="Cost per 1K input tokens in USD")
    output_price_per_1k_tokens: float = Field(description="Cost per 1K output tokens in USD")

# Rebuild AIProvider so that the forward reference to AIModelPrice is resolved
AIProvider.model_rebuild()

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
    model_file: Optional[str] = Field(description="Custom Modelfile", default=None)

class AISettings(BaseModel):
    provider: Optional[str] = Field(default="")
    provider_type: Optional[str] = Field(default="") 
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
    input_k_tokens_cxjcoins: Optional[float] = Field(
        description="Resolved cost in cxjcoins per 1K tokens (model-level takes precedence over provider-level).",
        default=None
    )
    output_k_tokens_cxjcoins: Optional[float] = Field(
        description="Resolved cost in cxjcoins per 1K tokens (model-level takes precedence over provider-level).",
        default=None
    )


KNOWLEDGE_MODEL = os.environ.get('CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL')
EMBEDDINGS_MODEL = os.environ.get('CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL')

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