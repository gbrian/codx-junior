## Mistral AI Integration

This document describes the `Mistral_AI` class, which integrates with the Mistral AI API for chat completions.

### Class: Mistral_AI

The `Mistral_AI` class provides an interface to interact with the Mistral AI models.

#### Initialization (`__init__`)

-   **Parameters**:
    -   `settings` (`CODXJuniorSettings`): An object containing the application settings, including API keys and model configurations.
-   **Functionality**:
    -   Initializes the `Mistral_AI` client using the API key retrieved from `settings`.

#### Logging (`log`)

-   **Parameters**:
    -   `msg` (`str`): The message to be logged.
-   **Functionality**:
    -   Logs the provided message if AI logging is enabled in the `settings`.

#### Message Conversion (`convert_message`)

-   **Parameters**:
    -   `gpt_message` (`Union[AIMessage, HumanMessage, BaseMessage]`): A message object from the Langchain library.
-   **Returns**:
    -   `dict`: A dictionary representing the message in a format suitable for the Mistral AI API, with "role" (assistant or user) and "content" keys.

#### Chat Completions (`chat_completions`)

-   **Parameters**:
    -   `messages` (`list`): A list of Langchain message objects representing the conversation history.
    -   `config` (`dict`, optional): A dictionary for configuration options. Currently supports "callbacks".
-   **Returns**:
    -   `AIMessage`: An `AIMessage` object containing the AI's response.
-   **Functionality**:
    -   Converts the input Langchain messages to the format expected by the Mistral AI API.
    -   Retrieves the AI model name and temperature from `settings`.
    -   Initiates a streaming chat completion request to the Mistral AI API.
    -   Processes the streamed response chunk by chunk.
    -   If callbacks are provided in `config`, it executes each callback with the received chunk content.
    -   Appends the content of each chunk to build the complete response.
    -   Logs the conversation history and the final AI response.

```python /codx/junior/ai/mistral_ai.py.disabled
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
        self.client = Mistral(api_key=api_key)

    def log(self, msg):
        if self.settings.get_log_ai():
            logger.info(msg)

    def convert_message(self, gpt_message: Union[AIMessage, HumanMessage, BaseMessage]): 
        return {
            "role": "assistant" if gpt_message.type == "ai" else "user",
            "content": gpt_message.content
        }

    @profile_function
    def chat_completions(self, messages, config: dict = {}):
        openai_messages = [self.convert_message(msg) for msg in messages if msg.content]
        self.log(f"chat_completions messages: {messages}")
        model = self.settings.get_ai_model()
        temperature = float(self.settings.temperature)
        callbacks = config.get("callbacks", None)
        
        response_stream = self.client.chat.stream(
            model = model,
            messages = openai_messages
        )
        callbacks = config.get("callbacks", None)
        content_parts = []
        if self.settings.get_log_ai():
            self.log(f"Received AI response, start reading stream")
        try:
            for chunk in response_stream:
                # Check for tools
                #tool_calls = self.process_tool_calls(chunk.choices[0].message)
                #if tool_calls:
                #    messages.append(HumanMessage(content=tool_calls))
                #    return self.chat_completions(messages=messages)
                chunk_content = chunk.data.choices[0].delta.content
                if chunk_content:
                    content_parts.append(chunk_content)
                    
                if callbacks:
                    for cb in callbacks:
                        try:
                            cb(chunk_content)
                        except Exception as ex:
                            logger.error(f"ERROR IN CALLBACKS: {ex}")
        except Exception as ex:
            logger.exception(f"Error reading AI response {ex}")
        
        self.log(f"AI response done {len(content_parts)} chunks")
        response_content = "".join(content_parts)
        self.log("\n\n".join(
            [f"[{datetime.now().isoformat()}] model: {model}, temperature: {temperature}"] +
            [f"[{message.type}]\n{message.content}" for message in messages] +
            ["[AI]",response_content]
        ))
        return AIMessage(content=response_content)

```