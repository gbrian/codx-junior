import logging

from codx.junior.ai.ai import AI
from codx.junior.model.model import AISettings
from codx.junior.settings import get_model_settings

from codx.junior.ai.ollama import OllamaAI

AI = AI
logger = logging.getLogger(__name__)

class AIManager:

    def reload_models(self, global_settings):
        for ai_model in global_settings.ai_models:
            self.load_model(model=ai_model.name)


    def load_model(self, model: str):
        ai_settings = get_model_settings(llm_model=model)
        if ai_settings.provider == 'ollama':
            OllamaAI(ai_settings=ai_settings).load_model()

