
import json
import logging
import os

from typing import List, Optional, Union

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

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai.openai_ai import OpenAI_AI
from codx.junior.ai.anthropic import Anthropic_AI

from codx.junior.profiling.profiler import profile_function

# Type hint for a chat message
Message = Union[AIMessage, HumanMessage, SystemMessage]

# Set up logging
logger = logging.getLogger(__name__)


class LogginCallbackHandler(StreamingStdOutCallbackHandler):
    pass

class AI:
    def __init__(
        self, settings: CODXJuniorSettings
    ):
        self.settings = settings
        self.llm = self.create_chat_model()
        self.embeddings = self.create_embeddings_model()
        self.cache = False

    @profile_function
    def image(self, prompt):
        return self.llm.generate_image(prompt)
    
    @profile_function
    def chat(
        self,
        messages: List[Message] = [],
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback = None
    ) -> List[Message]:
        if prompt:
            messages.append(HumanMessage(content=prompt))

        logger.debug(f"Creating a new chat completion: {messages}")

        response = None
        md5Key = messages_md5(messages) if self.cache else None
        if self.cache and md5Key in self.cache:
            response = AIMessage(content=json.loads(self.cache[md5Key])["content"])

        if not response:
            callbacks = []
            if callback:
                callbacks.append(callback)
            try:
                response = self.llm(messages=messages, config={ "callbacks": callbacks })
            except Exception as ex:
                logger.exception(f"Error processing AI request: {ex}")
                raise ex

            if self.cache:
                self.cache[md5Key] = json.dumps(
                    {
                        "messages": serialize_messages(messages),
                        "content": response.content,
                    }
                )
        elif self.settings.get_log_ai():
            logger.debug(f"Response from cache: {messages} {response}")

        messages.append(response)
        if self.settings.get_log_ai():
            def format_messages():
              return "\n".join([f"""############################################
              ### ROLE: {msg.type}
              ############################################

              {msg.content}
              """
              for msg in messages])
            logger.debug(f"Chat completion finished: {format_messages()}")
            logger.info(f"[AI] chat messages {len(messages)}")

        return messages

    @profile_function
    def embeddings(self, content: str):
        return self.embeddings(content=content)

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
        if self.settings.ai_provider == "anthropic":
            return Anthropic_AI(settings=self.settings).chat_completions    
        return OpenAI_AI(settings=self.settings).chat_completions

    def create_embeddings_model(self):
        return OpenAI_AI(settings=self.settings).embeddings


def serialize_messages(messages: List[Message]) -> str:
    return AI.serialize_messages(messages)


def messages_md5(messages: List[Message]):
    messageaStr = "".join(map(lambda x: x.content, messages))
    return str(hashlib.md5(messageaStr.encode("utf-8")).hexdigest())
