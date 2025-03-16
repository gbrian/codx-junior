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
        except Exception as ex:
            logger.exception(f"Error loading model {model_info}: {ex}")
