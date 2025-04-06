import ollama
import logging

from ollama import Client

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai.ai_logger import AILogger
from codx.junior.model.model import AISettings

from codx.junior.profiling.profiler import profile_function

logger = logging.getLogger(__name__)

class OllamaAI:
    ai_settings: AISettings
    
    def __init__(self, ai_settings: AISettings):
        self.ai_settings = ai_settings
        self.host = self.ai_settings.api_url.replace("/v1", "")
        self.client = Client(
          host=self.host
        )

    def log(self, msg):
        logger.info(msg)

    def load_model(self):
        model_info = f"{self.host} : {self.ai_settings.model}"
        self.log(f"ollama pull model {model_info}")
        try:
            self.client.pull(self.ai_settings.model)
            self.log(f"ollama pull model {model_info} DONE!")
            return self.client.show(self.ai_settings.model).model_dump()
        except Exception as ex:
            logger.exception(f"Error loading model {model_info}: {ex} {self.ai_settings}")

    def prune_models(self, active_models:[str]):
        self.log(f"ollama prune model list: {active_models}")
        all_models = self.client.list().models
        for model_info in all_models:
            self.log(f"ollama check model: {model_info}")
            model_name = model_info.model.replace(":latest", "")
            if model_name not in active_models:
                self.log(f"ollama delete model: {model_info.model}")
                self.client.delete(model_info.model)
                 
