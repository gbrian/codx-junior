# AI Model Documentation

## Overview

This module defines the data models and configuration for AI providers and models used in the codx-api project. It provides Pydantic-based models for managing LLM providers, embeddings models, image models, and their associated settings and pricing information.

## Core Models

### AIProvider

Represents an AI service provider configuration.

**Fields:**
- `name` - Provider name (default: "")
- `provider` - Provider type using OpenAI-compatible LLM protocols such as OpenAI or Ollama (default: "llmfactory")
- `api_url` - Optional remote provider URL (default: "http://0.0.0.0:11434/v1")
- `api_key` - Optional API key for authentication (default: "sk-llmfactory")
- `admin_url` - Optional admin panel URL
- `pricing_url` - Optional URL to provider's pricing page
- `input_k_tokens_cxjcoins` - Cost in cxjcoins per 1K input tokens at provider level
- `output_k_tokens_cxjcoins` - Cost in cxjcoins per 1K output tokens at provider level
- `price_list` - List of AIModelPrice objects fetched from provider's pricing page
- `max_tool_calls` - Maximum number of tool calls allowed per request (provider level)
- `max_iterations` - Maximum number of iterative tool loops allowed per request (provider level)

### AIModelPrice

Represents pricing information for a specific model from a provider.

**Fields:**
- `model_name` - Model name as listed by the provider
- `input_price_per_1k_tokens` - Cost per 1K input tokens in USD
- `output_price_per_1k_tokens` - Cost per 1K output tokens in USD

### AIModel

Represents an AI model configuration linked to a provider.

**Fields:**
- `name` - Model name
- `model_type` - Type of model (llm, embeddings, or image)
- `ai_provider` - Associated provider name
- `ai_model` - Provider's model name
- `settings` - Model settings (AILLMModelSettings or AIEmbeddingModelSettings)
- `metadata` - Additional metadata dictionary
- `url` - Model information URL
- `system` - System instructions for the model (default: "")
- `prompt_template` - Prompt template format (default: "{ MESSAGE }")
- `model_file` - Optional custom Modelfile
- `max_tool_calls` - Maximum tool calls (model level, overrides provider)
- `max_iterations` - Maximum iterative loops (model level, overrides provider)

## Settings Models

### AILLMModelSettings

Configuration for language model behavior.

**Fields:**
- `temperature` - Model temperature controlling randomness (default: 1)
- `context_length` - Maximum context length (default: 0)
- `merge_messages` - Whether to flatten conversation into single message before sending (default: false)

### AIEmbeddingModelSettings

Configuration for embedding models.

**Fields:**
- `vector_size` - Dimensionality of output vectors (default: 1536)
- `chunk_size` - Size of text chunks for embedding (default: 8190)

### AISettings

Resolved settings combining provider and model configurations.

**Fields:**
- `provider` - Provider name
- `provider_type` - Provider type
- `api_url` - Provider API URL
- `api_key` - Provider API key
- `model` - Model name
- `system` - System instructions
- `prompt_template` - Prompt template
- `context_length` - Context length
- `temperature` - Temperature setting
- `vector_size` - Vector size for embeddings
- `chunk_size` - Chunk size
- `merge_messages` - Message merging flag
- `model_type` - Type of model
- `url` - Model URL
- `input_k_tokens_cxjcoins` - Resolved input token cost (model-level takes precedence)
- `output_k_tokens_cxjcoins` - Resolved output token cost (model-level takes precedence)
- `max_tool_calls` - Resolved maximum tool calls (model-level takes precedence)
- `max_iterations` - Resolved maximum iterations (model-level takes precedence)

## Model Types

### AIModelType

Enum defining supported model types:
- `llm` - Large Language Model
- `embeddings` - Embedding/vector model
- `image` - Image generation model

## Priority System

The module implements a priority system for configuration resolution:
1. **Model level** - Highest priority
2. **Provider level** - Secondary priority
3. **Fallback** - Default values

This applies to: `max_tool_calls`, `max_iterations`, `input_k_tokens_cxjcoins`, and `output_k_tokens_cxjcoins`.

## Pre-configured Models

### OLLAMA_PROVIDER

Default LLM Factory provider configured with environment variables:
- `CODX_JUNIOR_LLMFACTORY_URL` - Provider API URL
- `CODX_JUNIOR_LLMFACTORY_KEY` - Provider API key

### OLLAMA_EMBEDDINGS_MODEL

Pre-configured embedding model with:
- Vector size: 768
- Chunk size: 2048
- Environment variable: `CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL`

### OLLAMA_KNOWLEDGE_MODEL

Pre-configured LLM for knowledge operations:
- Environment variable: `CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL`

## Environment Variables

- `CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL` - Knowledge model identifier
- `CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL` - Embeddings model identifier
- `CODX_JUNIOR_LLMFACTORY_URL` - LLM Factory API URL
- `CODX_JUNIOR_LLMFACTORY_KEY` - LLM Factory API key

## Dependencies
**Imported by:** codx/junior/ai/__init__.py, codx/junior/api/analytics.py, codx/junior/model/model.py