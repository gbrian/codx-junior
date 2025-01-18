import logging
import json
from datetime import datetime

from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam

from codx.junior.settings import CODXJuniorSettings
from langchain.schema import (
    AIMessage,
    HumanMessage,
    BaseMessage
)

from codx.junior.profiling.profiler import profile_function

logger = logging.getLogger(__name__)

tools = [
  {
    "type": "function",
    "function": {
      "name": "read_file",
      "description": "use to read the full content of a file reference.",
      "parameters": {
        "type": "string",
        "properties": {
          "file_path": {
            "type": "string",
            "description": "Absolute file path",
          }
        },
        "required": ["file_path"],
      },
    }
  }
]

class OpenAI_AI:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        api_key=settings.get_ai_api_key()
        base_url=settings.get_ai_api_url()
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

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
        
        response_stream = self.client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=openai_messages,
            stream=True
        )
        callbacks = config.get("callbacks", None)
        content_parts = []
        if self.settings.get_log_ai():
            self.log(f"AI response: {response_stream}")
        for chunk in response_stream:
            # Check for tools
            #tool_calls = self.process_tool_calls(chunk.choices[0].message)
            #if tool_calls:
            #    messages.append(HumanMessage(content=tool_calls))
            #    return self.chat_completions(messages=messages)

            chunk_content = chunk.choices[0].delta.content
            if not chunk_content:
                continue

            content_parts.append(chunk_content)
            if callbacks:
                for cb in callbacks:
                    cb.on_llm_new_token(chunk_content)

        response_content = "".join(content_parts)
        if self.settings.get_log_ai():
            logger.debug("\n\n".join(
                [f"[{datetime.now().isoformat()}] model: {model}, temperature: {temperature}"] +
                [f"[{message.type}]\n{message.content}" for message in messages] +
                ["[AI]",response_content]
            ))
        return AIMessage(content=response_content)

    def process_tool_calls(self, message):
        tool_responses = []
        for tool_call in message.tool_calls or []:
            self.log(f"process_tool_calls: {tool_call}")
            func = json.loads(tool_call.function)
            name = func["name"]
            params = func["arguments"]

            if name == "read_file":
              file_path = params["file_path"]
              content = self.tool_read_file(file_path)
              tool_responses.append(f"Content for {file_path}:\n{content}")

        return "\n".join(tool_responses)

    def tool_read_file(self, file_path):
        with open(file_path, 'r') as f:
            return f.read()

    @profile_function        
    def generate_image(self, prompt):
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        return response.data[0].url

    @profile_function
    def embeddings(self, content: str):
        response = self.client.embeddings.create(
            input=content,
            model=self.settings.get_ai_embeddings_model()
        )
        embeddings = []
        for data in response.data:
            embeddings = embeddings + data.embedding
        return embeddings