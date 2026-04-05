import json
import logging
import hashlib
from typing import List, Optional, Union, Dict, Any, Callable

from langchain.chat_models.base import BaseChatModel
from langchain.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai.openai_ai import OpenAI_AI
# from codx.junior.ai.vllm_cpu_ai import VllmCPUAI
from codx.junior.ai.ai_logger import AILogger

from codx.junior.profiling.profiler import profile_function
from codx.junior.model.model import CodxUser

# Type hint for a chat message
Message = Union[AIMessage, HumanMessage, SystemMessage]

# Set up logging
logger = logging.getLogger(__name__)

class AI:
    """
    Main class for managing AI interactions and routing.
    
    Mermaid Diagram:
    classDiagram
        AI --> OpenAI_AI : provider == "openai"
        AI --> VllmCPUAI : provider == "vllm"
        AI --> AILogger : Logging operations
    """
    def __init__(
        self, 
        settings: CODXJuniorSettings,
        llm_model: Optional[str] = None,
        user: Optional[CodxUser] = None,
        system: Optional[str] = None,
    ):
        """
        Initialize the AI class.

        :param settings: Configuration settings.
        :param llm_model: The specific model to be used.
        :param user: The user interacting with the AI.
        :param system: System level parameters.
        """
        self.system: Optional[str] = system
        self.user: Optional[CodxUser] = user
        self.settings: CODXJuniorSettings = settings
        self.llm_model: Optional[str] = llm_model
        self.llm_settings: Any = settings.get_llm_settings(llm_model=llm_model)
        self.cache: Union[bool, Dict[str, str]] = False
        self.ai_logger: AILogger = AILogger(settings=settings)

        self.llm: Callable = self.create_chat_model(llm_model=llm_model)
        self.a_llm: Callable = self.create_a_chat_model(llm_model=llm_model)
        self.embeddings: Callable = self.create_embeddings_model()

    @profile_function
    def image(self, prompt: str) -> str:
        """
        Generate an image based on the provided prompt.

        :param prompt: The description of the image.
        :return: Generated image URL or data.
        """
        return self.llm.generate_image(prompt)

    def log(self, message: str, *args: Any) -> None:
        """
        Logs a message using the AI Logger if enabled.

        :param message: The message string.
        :param args: Optional arguments for lazy string formatting.
        """
        if self.settings.get_log_ai():
            self.ai_logger.info(message, *args)
    
    @profile_function
    def chat(
        self,
        messages: Optional[List[Message]] = None,
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback: Optional[Callable] = None,
        tools: Optional[List[str]] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """
        Synchronous chat functionality that processes user inputs and returns AI responses.

        :param messages: History of messages.
        :param prompt: Prompt to append as a human message.
        :param max_response_length: The max tokens limit.
        :param callback: An optional callback function.
        :param tools: A list of tools for function calling.
        :param headers: Custom headers dict for the LLM request.
        :return: A list of processed messages including the AI reply.
        """
        if messages is None:
            messages = []
        if tools is None:
            tools = []
        if headers is None:
            headers = {}

        if prompt:
            messages.append(HumanMessage(content=prompt))

        response_messages: List[Message] = []
        md5_key = messages_md5(messages) if self.cache else None
        
        if self.cache and isinstance(self.cache, dict) and md5_key in self.cache:
            cache_data = json.loads(self.cache[md5_key])
            response_messages.append(
                AIMessage(content=cache_data["content"])
            )
            if self.settings.get_log_ai():
                self.ai_logger.debug("Response from cache: %s %s", messages, cache_data["content"])

        else:
            callbacks = []
            if callback:
                callbacks.append(callback)
            
            try:
                self.log(
                    "Creating a new chat completion. Messages: %d words: %d",
                    len(messages), 
                    len("".join([str(m.content) for m in messages]))
                )
                
                # Apply global instructions
                response_messages = self.llm(
                    messages=messages, 
                    config={"callbacks": callbacks, "headers": headers, "tools": tools}
                )
            except Exception as exc:
                logger.exception("Failed to process AI. Non-retryable error processing AI request: %s %s", exc, self.llm_model)
                raise RuntimeError(f"Failed to process AI request after retries. {exc}") from exc

            if self.cache and isinstance(self.cache, dict):
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
        messages: Optional[List[Message]] = None,
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback: Optional[Callable] = None,
        tools: Optional[List[str]] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """
        Asynchronous chat functionality that processes user inputs and returns AI responses.

        :param messages: History of messages.
        :param prompt: Prompt to append as a human message.
        :param max_response_length: The max tokens limit.
        :param callback: An optional callback function.
        :param tools: A list of tools for function calling.
        :param headers: Custom headers dict for the LLM request.
        :return: A list of processed messages including the AI reply.
        """
        if messages is None:
            messages = []
        if tools is None:
            tools = []
        if headers is None:
            headers = {}

        if prompt:
            messages.append(HumanMessage(content=prompt))

        response_messages: List[Message] = []
        md5_key = messages_md5(messages) if self.cache else None
        
        if self.cache and isinstance(self.cache, dict) and md5_key in self.cache:
            cache_data = json.loads(self.cache[md5_key])
            response_messages.append(
                AIMessage(content=cache_data["content"])
            )
            if self.settings.get_log_ai():
                self.ai_logger.debug("Response from cache: %s %s", messages, cache_data["content"])

        else:
            callbacks = []
            if callback:
                callbacks.append(callback)
            
            try:
                self.log(
                    "Creating a new a_chat completion. Messages: %d words: %d",
                    len(messages), 
                    len("".join([str(m.content) for m in messages]))
                )
                
                # Apply global instructions
                response_messages = await self.a_llm(
                    messages=messages, 
                    config={"callbacks": callbacks, "headers": headers, "tools": tools}
                )
            except Exception as exc:
                logger.exception("Failed to process AI. Non-retryable error processing AI request: %s %s", exc, self.llm_model)
                raise RuntimeError(f"Failed to process AI request after retries. {exc}") from exc

            if self.cache and isinstance(self.cache, dict):
                self.cache[md5_key] = json.dumps(
                    {
                        "messages": serialize_messages(messages),
                        "content": response_messages[-1].content,
                    }
                )
      
        return response_messages

    @profile_function
    def embeddings(self, content: str) -> Any:
        """
        Returns embeddings for a specific content string.
        """
        return self.embeddings(content=content)
        
    def _get_provider(self) -> str:
        """
        Helper method to retrieve the LLM provider safely.

        :return: The string representing the designated AI provider.
        """
        if hasattr(self.llm_settings, "provider"):
            return getattr(self.llm_settings, "provider", "")
        if isinstance(self.llm_settings, dict):
            return self.llm_settings.get("provider", "")
        return ""

    def create_chat_model(self, llm_model: Optional[str]) -> Callable:
        """
        Initialize the correct synchronous chat completions target based on configuration.
        """
        provider = self._get_provider()
        #if provider == "vllm":
        #    return VllmCPUAI(
        #        settings=self.settings, 
        #        llm_model=llm_model, 
        #        user=self.user, 
        #        system=self.system
        #    ).chat_completions
            
        return OpenAI_AI(
            settings=self.settings, 
            llm_model=llm_model, 
            user=self.user, 
            system=self.system
        ).chat_completions

    def create_a_chat_model(self, llm_model: Optional[str]) -> Callable:
        """
        Initialize the correct asynchronous chat completions target based on configuration.
        """
        provider = self._get_provider()
        #if provider == "vllm":
        #    return VllmCPUAI(
        #        settings=self.settings, 
        #        llm_model=llm_model, 
        #        user=self.user, 
        #        system=self.system
        #    ).a_chat_completions
            
        return OpenAI_AI(
            settings=self.settings, 
            llm_model=llm_model, 
            user=self.user, 
            system=self.system
        ).a_chat_completions

    def get_openai_chat_client(self, llm_model: Optional[str] = None) -> Any:
        return OpenAI_AI(
            settings=self.settings, 
            llm_model=llm_model, 
            user=self.user, 
            system=self.system
        ).client

    def create_embeddings_model(self) -> Any:
        return OpenAI_AI(
            settings=self.settings, 
            user=self.user, 
            system=self.system
        ).embeddings()

def messages_md5(messages: List[Message]) -> str:
    """
    Creates an MD5 hash representing the conversation string array.
    """
    messages_str = "".join([str(msg.content) for msg in messages])
    return str(hashlib.md5(messages_str.encode("utf-8")).hexdigest())

# Made with ❤️ by codx-junior