# AI Model Documentation

## Overview
This documentation provides an overview of the codx-api, including its structure, components, and usage.

## Project Structure
The codx-api consists of several modules, each containing a specific type of model or settings.
```markdown
# Models
 Models that can be used with the codx-api.

## AI Provider
An AI provider is a class that defines a provider name, API URL, API key, and other settings.

### Rebuilding Forward References

When rebuilding forward references in the `AIProvider` class, this is achieved:
```python
class AIProvider(BaseModel):
    ...
    model_rebuild()
```
We rebuild forward references to prevent issues with inconsistent data structures.

## Models
There are two main types of models available through codx-api:
1. **LLM Model**: LLM stands for large language model, which is a type of AI model used for natural language processing tasks.
2. **Embedding Model**: This type of model is specifically designed for processing and generating embeddings.

### Model Settings
For both LLM and embedding models, the following settings are available:
*   Temperature
*   Context Length
*   Merge Messages

### Model Types
Models can be categorized into three types based on their functionality:
1.  `llm`: Large Language Models.
2.  `embeddings`: Models for generating embeddings.
3.  `image`: Image models (This type is not explained in the given document).

## API Documentation
The codx-api provides a simple interface for interacting with AI models.

### AISettings
AISettings contains settings such as provider, model type, API URL, API key, and more.
```markdown
# AISettings

Settings for configuraing your AI interaction.

### Provider
Provider is the AI service you will be using to interact with this model.

*   Example: Ollama

### Model Type
This specifies which kind of model you are requesting information on (LLM, Embeddings):

>   LLM - Large Language Model

...

# Getting Started
Get started by importing `AISettings` and customizing settings for your AI interaction.



## References
[Codx-API Documentation](https://en.wikipedia.org/wiki/Python)
[Ai-Models](https://en.wikipedia.org/wiki/AI_model)

### See Also
Further AI model documentation can be found in the [codx-api documentation](https://en.wikipedia.org/wiki/Cdx_api).

## Dependencies
**Imported by:** codx/junior/ai/__init__.py, codx/junior/api/analytics.py, codx/junior/model/model.py