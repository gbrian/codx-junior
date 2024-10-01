import logging
import json
from datetime import datetime

from typing import Union

from codx.junior.settings import GPTEngineerSettings
from langchain.schema import (
    AIMessage,
    HumanMessage,
    BaseMessage
)

logger = logging.getLogger(__name__)


import anthropic


class Anthropic_AI:
    def __init__(self, settings: GPTEngineerSettings):
        self.settings = settings
        self.client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
        )


    def log(self, msg):
        if self.settings.log_ai:
            logger.info(msg)

    def convert_message(self, gpt_message: Union[AIMessage, HumanMessage, BaseMessage]): 
        if gpt_message.type == "image":
            return { "content": json.loads(gpt_message.content), "role": "user" }
        return {
            "role": "assistant" if gpt_message.type == "ai" else "user",
            "content": gpt_message.content
        }

    def chat_completions(self, messages, config: dict = {}):
        anthropic_messages = [self.convert_message(msg) for msg in messages]
        messages = [anthropic_messages[0]]
        for m in anthropic_messages[1:]:
            if messages[-1]["role"] == m["role"]:
                messages[-1]["content"] = f"{messages[-1]['content']}\n{m['content']}"
            else:
                messages.append(m)

        model = self.settings.anthropic_model
        # temperature = float(self.settings.temperature)
        
        self.log(f"anthropic_messages: {anthropic_messages}")
        response = self.client.messages.create(
            model=model,
            max_tokens=1024,
            messages=messages
        )
        self.log(f"ANTHROPIC RESPONSE: {response}")

        response_text = ""
        for content in response.content:
            response_text = response_text + content.text
        return AIMessage(content=response_text)
    

