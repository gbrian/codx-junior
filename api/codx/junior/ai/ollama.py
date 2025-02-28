import ollama
import logging 

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai.ai_logger import AILogger
from codx.junior.model import AISettings

from codx.junior.profiling.profiler import profile_function

logger = logging.getLogger(__name__)

class OllamaAI:
    ai_settings: AISettings
    
    def __init__(self, ai_settings: AISettings):
        self.ai_settings = ai_settings

    def log(self, msg):
        logger.info(msg)


    def load_model(self):
        self.log(f"ollama pull model {self.ai_settings.model}")
        ollama.pull(self.ai_settings.model)
