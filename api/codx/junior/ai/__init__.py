import logging

from codx.junior.ai.ai import AI
from codx.junior.model.model import AISettings, AIModel
from codx.junior.settings import get_model_settings, get_provider_settings

from codx.junior.ai.ollama import OllamaAI

AI = AI
logger = logging.getLogger(__name__)

class AIManager:

    def reload_models(self, global_settings):
        active_models = [ai_model for ai_model \
                            in global_settings.ai_models if ai_model.ai_provider == 'ollama'] 
        for ai_model in active_models:
            info = self.load_model(model=ai_model.name, global_settings=global_settings)
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

    def prune_models(self, active_models: [AIModel], global_settings):
        ollama = OllamaAI(ai_settings=get_provider_settings('ollama', global_settings=global_settings))
        ollama.prune_models([m.ai_model or m.name for m in active_models])

    def load_model(self, model: str, global_settings):
        ai_settings = get_model_settings(llm_model=model,global_settings=global_settings)
        if ai_settings.provider == 'ollama':
            return OllamaAI(ai_settings=ai_settings).load_model()
        return None
