
import json
import logging
import os
import hashlib

from typing import List, Optional, Union

from langchain_community.chat_models import ChatOpenAI
from langchain.chat_models.base import BaseChatModel
from langchain.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai.openai_ai import OpenAI_AI
from codx.junior.ai.ai_logger import AILogger

from codx.junior.profiling.profiler import profile_function

from codx.junior.model.model import CodxUser

# Type hint for a chat message
Message = Union[AIMessage, HumanMessage, SystemMessage]

# Set up logging
logger = logging.getLogger(__name__)

GLOBAL_CHAT_INSTRUCTIONS = """
<instructions info="General to follow when generating your response">
  <instruction>
    - IMPORTANT: Always add the file name after the code block language like in this example: "```js /absolute/file/path/file.js"
    - Use tools to convert relative project's file path to absolute.
    - Read file's content if not present in the comversation.
    - Use project search to find context if not clear on the conversation.
  </instruction>
</instructions>
"""

class AI:
    def __init__(
        self, settings: CODXJuniorSettings,
        llm_model: str = None,
        user: CodxUser = None
    ):
        self.user = user
        self.settings = settings
        self.llm_model = llm_model
        self.llm = self.create_chat_model(llm_model=llm_model)
        self.a_llm = self.create_a_chat_model(llm_model=llm_model)
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
        callback = None,
        headers = {}
    ) -> List[Message]:
        if not messages:
            messages = []

        if prompt:
            messages.append(HumanMessage(content=prompt))

        response_messages = None
        md5_key = messages_md5(messages) if self.cache else None
        if self.cache and md5_key in self.cache:
            response_messages.append(
                AIMessage(content=json.loads(self.cache[md5_key])["content"])
            )
            if self.settings.get_log_ai():
                self.ai_logger.debug(f"Response from cache: {messages} {response}")

        else:

            callbacks = []
            if callback:
                callbacks.append(callback)
            
            try:
                self.log(f"Creating a new chat completion. Messages: {len(messages)} words: {len(''.join([m.content for m in messages]))}")
                # Apply global instructions
                
                response_messages = self.llm(messages=[HumanMessage(content=GLOBAL_CHAT_INSTRUCTIONS)]
                                               + messages, 
                                               config={"callbacks": callbacks, "headers": headers})
            except Exception as ex:
                logger.exception(f"Non-retryable error processing AI request: {ex} {self.llm_model}")
                raise RuntimeError("Failed to process AI request after retries.")

            if self.cache:
                self.cache[md5_key] = json.dumps(
                    {
                        "messages": serialize_messages(messages),
                        "content": response_messages[-1].content,
                    }
                )
      
        return response_messages


    @profile_function
    async def a_chat(
        self,
        messages: List[Message] = None,
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback = None,
        headers = {}
    ) -> List[Message]:
        if not messages:
            messages = []

        if prompt:
            messages.append(HumanMessage(content=prompt))

        response_messages = None
        md5_key = messages_md5(messages) if self.cache else None
        if self.cache and md5_key in self.cache:
            response_messages.append(
                AIMessage(content=json.loads(self.cache[md5_key])["content"])
            )
            if self.settings.get_log_ai():
                self.ai_logger.debug(f"Response from cache: {messages} {response}")

        else:

            callbacks = []
            if callback:
                callbacks.append(callback)
            
            try:
                self.log(f"Creating a new chat completion. Messages: {len(messages)} words: {len(''.join([m.content for m in messages]))}")
                # Apply global instructions
                
                response_messages = await self.a_llm(messages=[HumanMessage(content=GLOBAL_CHAT_INSTRUCTIONS)]
                                               + messages, 
                                               config={"callbacks": callbacks, "headers": headers})
            except Exception as ex:
                logger.exception(f"Non-retryable error processing AI request: {ex} {self.llm_model}")
                raise RuntimeError("Failed to process AI request after retries.")

            if self.cache:
                self.cache[md5_key] = json.dumps(
                    {
                        "messages": serialize_messages(messages),
                        "content": response_messages[-1].content,
                    }
                )
      
        return response_messages

    @profile_function
    def embeddings(self, content: str):
        return self.embeddings(content=content)

    def create_chat_model(self, llm_model: str) -> BaseChatModel:
        return OpenAI_AI(settings=self.settings, llm_model=llm_model, user=self.user).chat_completions

    def create_a_chat_model(self, llm_model: str) -> BaseChatModel:
        return OpenAI_AI(settings=self.settings, llm_model=llm_model, user=self.user).a_chat_completions

    def get_openai_chat_client(self, llm_model: str = None):
        return OpenAI_AI(settings=self.settings, llm_model=llm_model, user=self.user).client

    def create_embeddings_model(self):
        return OpenAI_AI(settings=self.settings, user=self.user).embeddings()

def messages_md5(messages: List[Message]):
    messageaStr = "".join(map(lambda x: x.content, messages))
    return str(hashlib.md5(messageaStr.encode("utf-8")).hexdigest())
