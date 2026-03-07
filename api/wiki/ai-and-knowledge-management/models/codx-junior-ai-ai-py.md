# AI Module

This module provides a class `AI` for interacting with AI models, specifically designed for use within the `codx-api` project. It leverages `langchain-community` for AI model interactions and integrates with custom settings and logging mechanisms.

## Class: AI

The `AI` class is the main interface for AI functionalities.

### Initialization (`__init__`)

The constructor initializes the AI object with necessary components:

-   `settings`: An instance of `CODXJuniorSettings` to configure AI behavior.
-   `llm_model` (optional): Specifies the language model to use (e.g., 'gpt-4', 'gpt-3.5-turbo'). If not provided, a default might be used based on `OpenAI_AI`'s configuration.
-   `user` (optional): An instance of `CodxUser` representing the current user, which can be used for user-specific AI configurations or logging.

It sets up:
-   `self.llm`: The synchronous chat model instance.
-   `self.a_llm`: The asynchronous chat model instance.
-   `self.embeddings`: The embeddings model instance.
-   `self.cache`: A boolean flag to enable/disable caching of AI responses.
-   `self.ai_logger`: An instance of `AILogger` for logging AI interactions.

### Methods

#### `image(self, prompt)`

-   **Description:** Generates an image based on the provided text prompt.
-   **Parameters:**
    -   `prompt` (str): The text description for the image to be generated.
-   **Returns:** The generated image data.
-   **Profiling:** This function is decorated with `@profile_function` for performance monitoring.

#### `log(self, message)`

-   **Description:** Logs an AI-related message if AI logging is enabled in the settings.
-   **Parameters:**
    -   `message` (str): The message to be logged.

#### `chat(self, messages, prompt, max_response_length, callback, tools, headers)`

-   **Description:** Handles synchronous chat completions. It can take a list of messages or a single prompt, optionally using callbacks, tools, and custom headers. It also supports caching of responses.
-   **Parameters:**
    -   `messages` (List[Message], optional): A list of previous messages in the conversation. Defaults to an empty list.
    -   `prompt` (str, optional): A new prompt message to be added to the conversation.
    -   `max_response_length` (int, optional): Maximum length of the response.
    -   `callback` (callable, optional): A callback function to be executed during the AI's response generation.
    -   `tools` (List[str], optional): A list of tools the AI can use.
    -   `headers` (dict, optional): Custom headers for the API request.
-   **Returns:** A list of `Message` objects representing the AI's response.
-   **Error Handling:** Catches exceptions during AI processing and raises a `RuntimeError`.
-   **Caching:** If `self.cache` is enabled, it checks the cache first and stores responses if a cache miss occurs.
-   **Profiling:** This function is decorated with `@profile_function` for performance monitoring.

#### `a_chat(self, messages, prompt, max_response_length, callback, tools, headers)`

-   **Description:** Handles asynchronous chat completions, similar to `chat` but designed for non-blocking operations.
-   **Parameters:**
    -   `messages` (List[Message], optional): A list of previous messages in the conversation. Defaults to an empty list.
    -   `prompt` (str, optional): A new prompt message to be added to the conversation.
    -   `max_response_length` (int, optional): Maximum length of the response.
    -   `callback` (callable, optional): A callback function to be executed during the AI's response generation.
    -   `tools` (List[str], optional): A list of tools the AI can use.
    -   `headers` (dict, optional): Custom headers for the API request.
-   **Returns:** A list of `Message` objects representing the AI's response.
-   **Error Handling:** Catches exceptions during AI processing and raises a `RuntimeError`.
-   **Caching:** Supports caching similar to the `chat` method.
-   **Profiling:** This function is decorated with `@profile_function` for performance monitoring.

#### `embeddings(self, content)`

-   **Description:** Generates embeddings for the given content.
-   **Parameters:**
    -   `content` (str): The text content for which to generate embeddings.
-   **Returns:** The embeddings for the content.
-   **Profiling:** This function is decorated with `@profile_function` for performance monitoring.

#### `create_chat_model(self, llm_model)`

-   **Description:** Factory method to create a synchronous chat model instance using `OpenAI_AI`.
-   **Parameters:**
    -   `llm_model` (str): The name of the language model to use.
-   **Returns:** An instance of `BaseChatModel`.

#### `create_a_chat_model(self, llm_model)`

-   **Description:** Factory method to create an asynchronous chat model instance using `OpenAI_AI`.
-   **Parameters:**
    -   `llm_model` (str): The name of the language model to use.
-   **Returns:** An instance of `BaseChatModel`.

#### `get_openai_chat_client(self, llm_model)`

-   **Description:** Returns the underlying OpenAI client instance.
-   **Parameters:**
    -   `llm_model` (str, optional): The name of the language model to use.
-   **Returns:** The OpenAI client object.

#### `create_embeddings_model(self)`

-   **Description:** Factory method to create an embeddings model instance using `OpenAI_AI`.
-   **Returns:** The embeddings model instance.

## Helper Functions

#### `messages_md5(messages)`

-   **Description:** Generates an MD5 hash for a list of messages to be used as a cache key.
-   **Parameters:**
    -   `messages` (List[Message]): A list of message objects.
-   **Returns:** A string representing the MD5 hash of the concatenated message content.

```python /codx/junior/ai/ai.py
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
        tools: List[str] = [],
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
                
                response_messages = self.llm(messages=messages, 
                                               config={"callbacks": callbacks, "headers": headers, "tools": tools })
            except Exception as ex:
                logger.exception(f"Failed to process AI. Non-retryable error processing AI request: {ex} {self.llm_model}")
                raise RuntimeError(f"Failed to process AI request after retries. {ex}")

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
        tools: List[str] = [],
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
                
                response_messages = await self.a_llm(messages=messages, 
                                               config={"callbacks": callbacks, "headers": headers})
            except Exception as ex:
                logger.exception(f"Failed to process AI. Non-retryable error processing AI request: {ex} {self.llm_model}")
                raise RuntimeError(f"Failed to process AI request after retries. {ex}")

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

```