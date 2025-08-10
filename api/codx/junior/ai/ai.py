
import json
import logging
import os
import hashlib

from typing import List, Optional, Union

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
from codx.junior.ai.mistral_ai import Mistral_AI
from codx.junior.ai.ai_logger import AILogger

from codx.junior.profiling.profiler import profile_function

# Type hint for a chat message
Message = Union[AIMessage, HumanMessage, SystemMessage]

# Set up logging
logger = logging.getLogger(__name__)

GLOBAL_CHAT_INSTRUCTIONS = """
<instructions info="General to follow when generating your response">
  <instruction>
    When creating file content add the file name after the code block extension like in "```js /file/path/file.js"
  </instruction>
</instructions>
"""


class LogginCallbackHandler(StreamingStdOutCallbackHandler):
    pass

class AI:
    def __init__(
        self, settings: CODXJuniorSettings,
        llm_model: str = None
    ):
        self.settings = settings
        self.llm_model = llm_model
        self.llm = self.create_chat_model(llm_model=llm_model)
        self.embeddings = self.create_embeddings_model()
        self.cache = False
        self.ai_logger = AILogger(settings=settings)

    @profile_function
    def image(self, prompt):
        return self.llm.generate_image(prompt)


    def log(self, message):
        if self.settings.get_log_ai():
            self.ai_logger.info(message)
    
    @profile_function
    def chat(
        self,
        messages: List[Message] = None,
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback = None
    ) -> List[Message]:
        if not messages:
            messages = []

        if prompt:
            messages.append(HumanMessage(content=prompt))

        response = None
        md5_key = messages_md5(messages) if self.cache else None
        if self.cache and md5_key in self.cache:
            response = AIMessage(content=json.loads(self.cache[md5_key])["content"])

        if not response:
            callbacks = []
            if callback:
                callbacks.append(callback)
            
            try:
                self.log(f"Creating a new chat completion. Messages: {len(messages)} words: {len(''.join([m.content for m in messages]))}")
                # Apply global instructions
                
                response = self.llm(messages=[HumanMessage(content=GLOBAL_CHAT_INSTRUCTIONS)]
                                               + messages, config={"callbacks": callbacks})
            except Exception as ex:
                logger.exception(f"Non-retryable error processing AI request: {ex} {self.llm_model} {self.settings}")
                raise RuntimeError("Failed to process AI request after retries.")

            if self.cache:
                self.cache[md5_key] = json.dumps(
                    {
                        "messages": serialize_messages(messages),
                        "content": response.content,
                    }
                )
        elif self.settings.get_log_ai():
            self.ai_logger.debug(f"Response from cache: {messages} {response}")

        messages.append(response)
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


    def create_chat_model(self, llm_model: str) -> BaseChatModel:
        return OpenAI_AI(settings=self.settings, llm_model=llm_model).chat_completions

    def get_openai_chat_client(self, llm_model: str = None):
        return OpenAI_AI(settings=self.settings, llm_model=llm_model).client

    def create_embeddings_model(self):
        return OpenAI_AI(settings=self.settings).embeddings()

def serialize_messages(messages: List[Message]) -> str:
    return AI.serialize_messages(messages)


def messages_md5(messages: List[Message]):
    messageaStr = "".join(map(lambda x: x.content, messages))
    return str(hashlib.md5(messageaStr.encode("utf-8")).hexdigest())
