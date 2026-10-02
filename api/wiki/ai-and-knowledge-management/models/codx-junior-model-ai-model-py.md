# AI Model Configuration

This module defines the data models and configuration for AI providers and models used in the Codx Junior system. It handles LLM (Large Language Models), embeddings, and image models with support for multiple providers.

## Core Models

### AIProvider

Represents an AI service provider with connection details and pricing information.

**Key Fields:**
- `name` - Provider name identifier
- `provider` - Protocol type (e.g., "llmfactory", "OpenAI", "Ollama")
- `api_url` - Endpoint URL for the provider (default: `http://0.0.0.0:11434/v1`)
- `api_key` - Authentication key for API access
- `admin_url` - Optional admin dashboard URL
- `pricing_url` - Optional link to provider's pricing page
- `input_k_tokens_cxjcoins` - Cost per 1K input tokens in cxjcoins
- `output_k_tokens_cxjcoins` - Cost per 1K output tokens in cxjcoins
- `price_list` - List of model pricing information from the provider
- `max_tool_calls` - Maximum tool calls allowed per request at provider level
- `max_iterations` - Maximum iterative tool loops allowed per request at provider level

### AIModel

Represents a specific AI model with its configuration and settings.

**Key Fields:**
- `name` - Model identifier
- `model_type` - Type of model: `llm`, `embeddings`, or `image`
- `ai_provider` - Name of the provider
- `ai_model` - Provider's internal model name
- `settings` - Model-specific settings (LLM or Embedding)
- `metadata` - Additional metadata dictionary
- `url` - Model information URL
- `system` - System instructions for the model
- `prompt_template` - Template for message formatting (default: `{ MESSAGE }`)
- `model_file` - Optional custom Modelfile
- `max_tool_calls` - Model-level override for maximum tool calls
- `max_iterations` - Model-level override for maximum iterations

### AISettings

Aggregated settings resolved from provider and model configurations with precedence rules.

**Key Fields:**
- `provider`, `provider_type`, `api_url`, `api_key` - Connection details
- `model` - Model name
- `system`, `prompt_template`, `context_length`, `temperature` - Model configuration
- `vector_size`, `chunk_size` - Embedding-specific settings
- `merge_messages` - Whether to flatten conversation into single message
- `model_type` - Type of model
- `input_k_tokens_cxjcoins`, `output_k_tokens_cxjcoins` - Resolved pricing
- `max_tool_calls`, `max_iterations` - Resolved tool call limits

## Supporting Models

### AILLMModelSettings

Configuration for Large Language Models.

**Fields:**
- `temperature` - Model temperature for output randomness (default: 1)
- `context_length` - Maximum context length in tokens (default: 0)
- `merge_messages` - Whether to flatten conversation before sending to model (default: False)

### AIEmbeddingModelSettings

Configuration for embedding models.

**Fields:**
- `vector_size` - Dimension of embedding vectors (default: 1536)
- `chunk_size` - Size of text chunks for embedding (default: 8190)

### AIModelPrice

Pricing information for individual models.

**Fields:**
- `model_name` - Model name as listed by provider
- `input_price_per_1k_tokens` - Cost per 1K input tokens in USD
- `output_price_per_1k_tokens` - Cost per 1K output tokens in USD

### AIModelType

Enumeration of supported model types:
- `llm` - Language models
- `embeddings` - Embedding models
- `image` - Image generation models

## Priority and Defaults

The module implements a priority system for certain settings:

**Priority Order: Model Level > Provider Level > Fallback**

This applies to:
- `max_tool_calls` - Maximum tool calls per request
- `max_iterations` - Maximum iterative tool loops
- Pricing (`input_k_tokens_cxjcoins`, `output_k_tokens_cxjcoins`)

## Default Provider and Models

The module provides preconfigured instances:

### OLLAMA_PROVIDER

Default LLMFactory provider configured with environment variables:
- `CODX_JUNIOR_LLMFACTORY_URL` - Provider API URL
- `CODX_JUNIOR_LLMFACTORY_KEY` - Provider API key

### OLLAMA_EMBEDDINGS_MODEL

Default embeddings model configured with:
- Vector size: 768
- Chunk size: 2048
- Loaded from `CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL` environment variable

### OLLAMA_KNOWLEDGE_MODEL

Default knowledge/chat model configured with:
- Standard LLM settings
- Loaded from `CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL` environment variable

## Dependencies
**Imported by:** codx/junior/ai/__init__.py, codx/junior/api/analytics.py, codx/junior/model/model.py