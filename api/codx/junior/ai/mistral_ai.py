import logging
import json
from datetime import datetime

from typing import Union

from codx.junior.settings import CODXJuniorSettings
from langchain.schema import (
    AIMessage,
    HumanMessage,
    BaseMessage
)

from codx.junior.profiling.profiler import profile_function

from mistralai import Mistral

logger = logging.getLogger(__name__)


class Mistral_AI:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        api_key=settings.get_ai_api_key()
        base_url=settings.get_ai_api_url()
        self.client = Mistral(api_key=api_key, base_url=base_url)

    def log(self, msg):
        if self.settings.get_log_ai():
            logger.info(msg)

    def convert_message(self, gpt_message: Union[AIMessage, HumanMessage, BaseMessage]): 
        if gpt_message.type == "image":
            return { "content": json.loads(gpt_message.content), "role": "user" }
        return {
            "role": "assistant" if gpt_message.type == "ai" else "user",
            "content": gpt_message.content
        }

    @profile_function
    def chat_completions(self, messages, config: dict = {}):
        openai_messages = [self.convert_message(msg) for msg in messages]
        model = self.settings.get_ai_model()
        temperature = float(self.settings.temperature)
        
        chat_response = client.chat.complete(
            model = model,
            messages = [
                {
                    "role": "user",
                    "content": "What is the best French cheese?",
                },
            ]
        )

        callbacks = config.get("callbacks", None)
        response_content = chat_response.choices[0].message.content

        if self.settings.get_log_ai():
            logger.debug("\n\n".join(
                [f"[{datetime.now().isoformat()}] model: {model}, temperature: {temperature}"] +
                [f"[{message.type}]\n{message.content}" for message in messages] +
                ["[AI]",response_content]
            ))
        return AIMessage(content=response_content)
