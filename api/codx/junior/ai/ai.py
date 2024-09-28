"""
This module provides an interface to interact with AI models.
It leverages the OpenAI GPT models and allows for integration with Azure-based instances of the same.
The AI class encapsulates the chat functionalities, allowing to start, advance, and manage a conversation with the model.

Key Features:
- Integration with Azure-based OpenAI instances through the LangChain AzureChatOpenAI class.
- Token usage logging to monitor the number of tokens consumed during a conversation.
- Seamless fallback to default models in case the desired model is unavailable.
- Serialization and deserialization of chat messages for easier transmission and storage.

Classes:
- AI: Main class providing chat functionalities.

Dependencies:
- langchain: For chat models and message schemas.
- openai: For the core GPT models interaction.
- backoff: For handling rate limits and retries.
- typing: For type hints.

For more specific details, refer to the docstrings within each class and function.
"""

from __future__ import annotations

import json
import logging
import os

from typing import List, Optional, Union

import backoff
import openai

import hashlib


from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from langchain_community.chat_models import ChatOpenAI
from langchain.chat_models.base import BaseChatModel
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    messages_from_dict,
    messages_to_dict,
)

from codx.junior.settings import GPTEngineerSettings
from codx.junior.ai.openai_ai import OpenAI_AI

# Type hint for a chat message
Message = Union[AIMessage, HumanMessage, SystemMessage]

# Set up logging
logger = logging.getLogger(__name__)


class LogginCallbackHandler(StreamingStdOutCallbackHandler):
    pass

class AI:
    def __init__(
        self, settings: GPTEngineerSettings
    ):
        self.settings = settings
        self.llm = self.create_chat_model()
        self.cache = False

    
    def chat(
        self,
        messages: List[Message],
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback = None
    ) -> List[Message]:
        if prompt:
            messages.append(HumanMessage(content=prompt))

        # logger.debug(f"Creating a new chat completion: {messages}")

        response = None
        md5Key = messages_md5(messages) if self.cache else None
        if self.cache and md5Key in self.cache:
            response = AIMessage(content=json.loads(self.cache[md5Key])["content"])

        if not response:
            callbacks = [LogginCallbackHandler()] if self.settings.log_ai else []
            if callback:
                callbacks.append(callback)
            response = self.llm(messages=messages, config={ "callbacks": callbacks })
            if self.cache:
                self.cache[md5Key] = json.dumps(
                    {
                        "messages": serialize_messages(messages),
                        "content": response.content,
                    }
                )
        else:
            logger.debug(f"Response from cache: {messages} {response}")

        messages.append(response)
        if self.settings.log_ai:
            logger.debug(f"Chat completion finished: {messages}")

        return messages

    @staticmethod
    def serialize_messages(messages: List[Message]) -> str:
        try:
            return json.dumps(messages_to_dict(messages))
        except Exception as ex:
            logger.error(f"serialize_messages error: {messages} {ex}")
            raise ex

    @staticmethod
    def deserialize_messages(jsondictstr: str) -> List[Message]:
        data = json.loads(jsondictstr)
        # Modify implicit is_chunk property to ALWAYS false
        # since Langchain's Message schema is stricter
        prevalidated_data = [
            {**item, "data": {**item["data"], "is_chunk": False}} for item in data
        ]
        return list(messages_from_dict(prevalidated_data))  # type: ignore


    def create_chat_model(self) -> BaseChatModel:
        return OpenAI_AI(settings=self.settings).chat_completions


def serialize_messages(messages: List[Message]) -> str:
    return AI.serialize_messages(messages)


def messages_md5(messages: List[Message]):
    messageaStr = "".join(map(lambda x: x.content, messages))
    return str(hashlib.md5(messageaStr.encode("utf-8")).hexdigest())
