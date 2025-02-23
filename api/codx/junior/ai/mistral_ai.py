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
