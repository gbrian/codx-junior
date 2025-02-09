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
        self.model = self.settings.get_ai_model()
        self.api_key=settings.get_ai_api_key()
        self.base_url=settings.get_ai_api_url()

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
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

        self.log(f"OpenAI_AI chat_completions {self.settings.get_ai_provider()}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = [self.convert_message(msg) for msg in messages]
        temperature = float(self.settings.temperature)
        
        response_stream = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=openai_messages,
            stream=True
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
                chunk_content = chunk.choices[0].delta.content
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
            [f"[{datetime.now().isoformat()}] model: {self.model}, temperature: {temperature}"] +
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
    def embeddings(self):
        embeddings_ai_settings = self.settings.get_ai_embeddings_settings()
        client = OpenAI(
            api_key=embeddings_ai_settings.api_key,
            base_url=embeddings_ai_settings.api_url
        )
        def embedding_func(content: str):
            try:
              response = client.embeddings.create(
                  input=content,
                  model=embeddings_ai_settings.model
              )
              embeddings = []
              for data in response.data:
                  embeddings = embeddings + data.embedding
              return embeddings
            except Exception as ex:
              logger.exception(f"Error creating embeddings {ex} {self.settings.project_name} {embeddings_ai_settings}")
        return embedding_func