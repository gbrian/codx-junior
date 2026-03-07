This document describes the `AIManager` class in the `codx.junior.ai` module, which is responsible for managing AI models.

## `AIManager`

The `AIManager` class provides functionalities to load, reload, and prune AI models.

### Methods

#### `reload_models(self, global_settings)`

This method reloads all active AI models that use the 'llmfactory' provider. It iterates through the `ai_models` in `global_settings`, loads each model using `load_model`, and updates its settings such as `context_length`, `chunk_size`, and `vector_size` based on information retrieved from the model. It also calls `prune_models` to clean up unused models.

#### `prune_models(self, active_models: [AIModel], global_settings)`

This method prunes (removes) AI models that are no longer active. It initializes an `OllamaAI` instance and calls its `prune_models` method, passing a list of active model names or identifiers.

#### `reload_model(self, model: AIModel)`

This method reloads a single AI model. It first reads the global settings and then calls `load_model` to reload the specified model.

#### `load_model(self, model: str, global_settings)`

This method loads a specific AI model. It retrieves the settings for the given `model` using `get_model_settings` and then uses `OllamaAI` to load the model with those settings.

```python
# /codx/junior/ai/__init__.py
import logging

from codx.junior.ai.ai import AI
from codx.junior.model.model import AISettings, AIModel
from codx.junior.settings import (
  get_model_settings,
  get_provider_settings,
  read_global_settings,
  get_model,
  save_model
)

from codx.junior.ai.llmfactory import OllamaAI

AI = AI
logger = logging.getLogger(__name__)

class AIManager:

    def reload_models(self, global_settings):
        active_models = [ai_model for ai_model \
                            in global_settings.ai_models if ai_model.ai_provider == 'llmfactory']
        for ai_model in active_models:
            try:
                info = self.load_model(model=ai_model.name, global_settings=global_settings)
                if not info:
                    logger.error(f"Error reloading model {ai_model}")
                    continue
                model_info = info['modelinfo']

                context_length_keys = [k for k in model_info.keys() if "context_length" in k]
                if context_length_keys:
                    context_length = model_info[context_length_keys[0]]
                    # logger.info(f"Set model context length {ai_model.name}: {context_length}")
                    if hasattr(ai_model.settings, "context_length"):
                        ai_model.settings.context_length = context_length
                    if hasattr(ai_model.settings, "chunk_size"):
                        ai_model.settings.chunk_size = context_length

                embedding_length_keys = [k for k in model_info.keys() if "embedding_length" in k]
                if embedding_length_keys and hasattr(ai_model.settings, "vector_size"):
                    embedding_length = model_info[embedding_length_keys[0]]
                    # logger.info(f"Set embedding length {ai_model.name}: {embedding_length}")
                    ai_model.settings.vector_size = embedding_length

                # logger.info(f"Load model {ai_model.name}: {model_info} {ai_model}")
                self.prune_models(active_models=active_models, global_settings=global_settings)
            except Exception as ex:
                logger.error("Error '%s' reloading model: %s", str(ex), ai_model.name)

    def prune_models(self, active_models: [AIModel], global_settings):
        llmfactory = OllamaAI(ai_settings=get_provider_settings('llmfactory', global_settings=global_settings))
        llmfactory.prune_models([m.ai_model or m.name for m in active_models])

    def reload_model(self, model: AIModel):
        global_settings = read_global_settings()
        return self.load_model(model=model.name, global_settings=global_settings)

    def load_model(self, model: str, global_settings):
        ai_settings = get_model_settings(llm_model=model, global_settings=global_settings)
        return OllamaAI(ai_settings=ai_settings).load_model()
```