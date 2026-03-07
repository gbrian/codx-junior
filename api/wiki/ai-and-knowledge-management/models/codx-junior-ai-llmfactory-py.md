This document describes the `OllamaAI` class, designed to interact with the Ollama AI model serving system.

### OllamaAI Class

The `OllamaAI` class provides methods for loading and managing AI models using the Ollama API.

#### Initialization

The class is initialized with an `AISettings` object, which contains configuration details for the AI model, including the API URL and the model name.

```python
class OllamaAI:
    ai_settings: AISettings
    
    def __init__(self, ai_settings: AISettings):
        self.ai_settings = ai_settings
        self.host = self.ai_settings.api_url.replace("/v1", "")
        # self.client = Client(
        #   host=self.host
        # )
```

#### Logging

A helper method `log` is provided for logging information related to Ollama operations.

```python
    def log(self, msg):
        logger.info(msg)
```

#### Loading Models

The `load_model` method is responsible for pulling a specified model from Ollama and returning its details. It logs the process and handles potential exceptions.

```python
    def load_model(self):
        model_info = f"{self.host} : {self.ai_settings.model}"
        self.log(f"ollama pull model {model_info}")
        try:
            self.client.pull(self.ai_settings.model)
            self.log(f"ollama pull model {model_info} DONE!")
            return self.client.show(self.ai_settings.model).model_dump()
        except Exception as ex:
            logger.exception(f"Error loading model {model_info}: {ex} {self.ai_settings}")
            return { "error": str(ex) }
```

#### Pruning Models

The `prune_models` method allows for the removal of unused models from Ollama. It takes a list of active model names and deletes any models not present in this list.

```python
    def prune_models(self, active_models:[str]):
        self.log(f"ollama prune model list: {active_models}")
        all_models = self.client.list().models
        for model_info in all_models:
            self.log(f"ollama check model: {model_info}")
            model_name = model_info.model.replace(":latest", "")
            if model_name not in active_models:
                self.log(f"ollama delete model: {model_info.model}")
                self.client.delete(model_info.model)
```