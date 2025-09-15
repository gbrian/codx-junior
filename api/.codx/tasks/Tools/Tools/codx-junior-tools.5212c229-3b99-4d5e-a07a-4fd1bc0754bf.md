# [[{"id": "5212c229-3b99-4d5e-a07a-4fd1bc0754bf", "doc_id": null, "project_id": null, "parent_id": null, "message_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/tools/fetch_webpage.py", "/shared/codx-junior/api/codx/junior/ai/openai_ai.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "codx-junior tools", "description": "1. The user provided instructions for generating file content with specific naming conventions.\n2. A Python code snippet was shared for handling tool call data in a streaming environment, focusing on capturing and processing tool call arguments.\n3. The user shared the content of two Python files: one for fetching webpages and converting them to markdown, and another for an AI class handling chat completions and tool calls.\n4. The user requested that tool responses be formatted in a specific JSON structure, including a `call_id` and `output`.\n5. A solution was provided to modify the `process_tool_calls` method in the `OpenAI_AI` class to format the tool responses as specified.", "created_at": "2025-09-13 14:25:52.617041", "updated_at": "2025-09-15T05:05:52.230241", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Tools", "column": "Tools", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Tools/Tools/codx-junior-tools.5212c229-3b99-4d5e-a07a-4fd1bc0754bf.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": [], "chat_links": [], "pr_view": {}}]]
## [[{"doc_id": "ea0ffecc-49c4-46c1-8c97-121d3deb38c1", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-13 16:15:02.434195", "updated_at": "2025-09-13 16:15:02.434226", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
We want to expose tools to models in AI.
Import the tools and add to the "tools" section in the request.
Check if the model uses tools.
Capture tools flow and invoke the tools
## [[{"doc_id": "5fae2e78-a25d-4c5f-9eab-bfd774937ec7", "role": "assistant", "task_item": "analysis", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-13 16:15:02.434195", "updated_at": "2025-09-13 16:15:02.434226", "images": [], "files": [], "meta_data": {"time_taken": 60.57917785644531, "first_chunk_time_taken": 0.0002124309539794922, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To address the user comments and requirements, we need to import the `tools` from the appropriate module (if they are not already imported), add them to the `tools` section in the request, check if the model uses tools, and capture the tools flow to invoke the tools. Below is the updated code for `/shared/codx-junior/api/codx/junior/ai/openai_ai.py`:

```python /shared/codx-junior/api/codx/junior/ai/openai_ai.py
import logging
import json
from datetime import datetime

from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam

from codx.junior.ai.ai_logger import AILogger

from codx.junior.settings import CODXJuniorSettings
from langchain.schema import (
    AIMessage,
    HumanMessage,
    BaseMessage
)

from codx.junior.profiling.profiler import profile_function

from codx.junior.utils.utils import clean_string

# Import tools if not already imported
from codx.junior.tools import fetch_webpage

logger = logging.getLogger(__name__)

# Define tools
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
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "Fetch a webpage and convert it to markdown format.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the webpage to fetch"
                    },
                    "include_images": {
                        "type": "boolean",
                        "description": "Whether to include image references in the markdown"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum length of the output markdown"
                    },
                    "headers": {
                        "type": "object",
                        "description": "Optional HTTP headers for the request"
                    }
                },
                "required": ["url"]
            }
        }
    }
]

class OpenAI_AI:
    def __init__(self, settings: CODXJuniorSettings, llm_model: str = None):
        self.settings = settings
        self.llm_settings = settings.get_llm_settings(llm_model=llm_model)

        self.model = self.llm_settings.model
        self.api_key = self.llm_settings.api_key
        self.base_url = self.llm_settings.api_url

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as ex:
            logger.error("Error creating OpenAI client: %s, %s*****", self.base_url, self.api_key[0:5])
        self.ai_logger = AILogger(settings=settings)

    def log(self, msg):
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    def convert_message(self, gpt_message: Union[AIMessage, HumanMessage, BaseMessage]):
        if gpt_message.type == "image":
            try:
                return {"content": json.loads(gpt_message.content), "role": "user"}
            except Exception as ex:
                self.log(f"Error converting image message '{ex}': {gpt_message}")
                raise ex
        return {
            "role": "assistant" if gpt_message.type == "ai" else "user",
            "content": gpt_message.content
        }

    @profile_function
    def chat_completions(self, messages, config: dict = {}):
        kwargs = {
            "model": self.model,
            "stream": True,
            "tools": tools  # Add tools to the request
        }

        if self.llm_settings.temperature >= 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(f"OpenAI_AI chat_completions {self.llm_settings.provider}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = [self.convert_message(msg) for msg in messages]

        if self.llm_settings.merge_messages:
            message = "\n".join([message['content'] for message in openai_messages])
            openai_messages = [{"role": "user", "content": message}]
        self.log(f"USER REQUEST:\n{openai_messages}")
        if self.settings.get_log_ai():
            self.log(f"\nReceived AI response, start reading stream\n{self.llm_settings}")
        try:
            request_headers = config.get("headers", {})
            tags = request_headers.get("tags", "")
            tags = tags.split(",") + [
                f"temp-{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            request_headers["x-litellm-tags"] = ",".join(tags)

            response_stream = self.client.chat.completions.create(
                **kwargs,
                messages=openai_messages,
                extra_headers=request_headers
            )
            callbacks = config.get("callbacks", None)
            content_parts = []

            callback_data = {
                "buffer": [],
                "ts": datetime.now()
            }

            def send_callback(chunk_content, flush=False):
                if not callbacks:
                    return

                callback_data["buffer"].append(chunk_content or "")
                if flush or (datetime.now() - callback_data["ts"]).total_seconds() > 1:
                    callback_data["ts"] = datetime.now()
                    message = "".join(callback_data["buffer"]) if callback_data["buffer"] else ""
                    callback_data["buffer"] = []
                    for cb in callbacks:
                        try:
                            cb(message)
                        except Exception as ex:
                            logger.exception(f"ERROR IN CALLBACKS: {ex}")

            for chunk in response_stream:
                # Check for tools
                tool_calls = self.process_tool_calls(chunk.choices[0].message)
                if tool_calls:
                    messages.append(HumanMessage(content=tool_calls))
                    return self.chat_completions(messages=messages)
                chunk_content = chunk.choices[0].delta.content
                if not chunk_content:
                    continue
                chunk_content = clean_string(chunk_content)
                content_parts.append(chunk_content)
                send_callback(chunk_content)
            # Last chunks...
            send_callback("", flush=True)
        except Exception as ex:
            logger.error("Error reading AI response: %s, %s, %s\n%s", self.base_url, self.api_key[0:5], self.llm_settings, ex)
            raise ex

        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

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
            elif name == "fetch_webpage":
                url = params["url"]
                include_images = params.get("include_images", True)
                max_length = params.get("max_length")
                headers = params.get("headers")
                content = self.tool_fetch_webpage(url, include_images, max_length, headers)
                tool_responses.append(f"Markdown content for {url}:\n{content}")

        return "\n".join(tool_responses)

    def tool_read_file(self, file_path):
        with open(file_path, 'r') as f:
            return f.read()

    def tool_fetch_webpage(self, url, include_images=True, max_length=None, headers=None):
        return fetch_webpage(url, include_images, max_length, headers)

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
        embeddings_ai_settings = self.settings.get_embeddings_settings()
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
                logger.error(f"Error creating embeddings {self.settings.project_name} {embeddings_ai_settings}: {ex}")
                raise ex

        return embedding_func
```

In this updated code, I have:
- Imported the `fetch_webpage` function.
- Added `fetch_webpage` as a tool in the `tools` list.
- Updated the `chat_completions` method to include `tools` in the request.
- Implemented the `process_tool_calls` method to process tool calls and invoke the appropriate tool functions.
- Added a `tool_fetch_webpage` method to handle fetching webpage content.
## [[{"doc_id": "ce88cf6b-9b9e-4742-86aa-a3bd9d698433", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-13 16:23:44.127407", "updated_at": "2025-09-13 16:23:44.127429", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
move the tools array to tools/__init__.py with this fields:
 * tool_json: contains the tool descriptiont to be send to the ai model
 * settings: { "async": True } Se of settings, if tool is async AI will have to await for the response
 * tool_call: A lambda to invoke from the AI with kwargs from the AI model response.


In tools __init__ import all tools (like fetch_webpage) create the entry in the TOOLS array and create the lambda that will call the function

In openai_ai import the TOOLS from the tools/__init__.py 
## [[{"doc_id": "90c61e80-6b61-4d3a-90cf-a5033cb63ed4", "role": "assistant", "task_item": "analysis", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-13 16:23:44.127407", "updated_at": "2025-09-13 16:23:44.127429", "images": [], "files": [], "meta_data": {"time_taken": 70.15919280052185, "first_chunk_time_taken": 0.00023508071899414062, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
```python /shared/codx-junior/api/codx/junior/tools/__init__.py
import logging
from typing import Optional, Dict
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
import html2text

# Import tools
from .fetch_webpage import fetch_webpage

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define TOOLS
TOOLS = [
    {
        "tool_json": {
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
        },
        "settings": {"async": False},
        "tool_call": lambda kwargs: tool_read_file(kwargs["file_path"])
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "fetch_webpage",
                "description": "Fetch a webpage and convert it to markdown format.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL of the webpage to fetch"
                        },
                        "include_images": {
                            "type": "boolean",
                            "description": "Whether to include image references in the markdown"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum length of the output markdown"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP headers for the request"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        "settings": {"async": True},
        "tool_call": lambda kwargs: fetch_webpage(kwargs["url"], kwargs.get("include_images", True), kwargs.get("max_length"), kwargs.get("headers"))
    }
]

def tool_read_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()
```

```python /shared/codx-junior/api/codx/junior/ai/openai_ai.py
import logging
import json
from datetime import datetime

from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam

from codx.junior.ai.ai_logger import AILogger

from codx.junior.settings import CODXJuniorSettings
from langchain.schema import (
    AIMessage,
    HumanMessage,
    BaseMessage
)

from codx.junior.profiling.profiler import profile_function

from codx.junior.utils.utils import clean_string

# Import TOOLS from tools/__init__.py
from codx.junior.tools import TOOLS

logger = logging.getLogger(__name__)

class OpenAI_AI:
    def __init__(self, settings: CODXJuniorSettings, llm_model: str = None):
        self.settings = settings
        self.llm_settings = settings.get_llm_settings(llm_model=llm_model)

        self.model = self.llm_settings.model
        self.api_key = self.llm_settings.api_key
        self.base_url = self.llm_settings.api_url

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as ex:
            logger.error("Error creating OpenAI client: %s, %s*****", self.base_url, self.api_key[0:5])
        self.ai_logger = AILogger(settings=settings)

    def log(self, msg):
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    def convert_message(self, gpt_message: Union[AIMessage, HumanMessage, BaseMessage]):
        if gpt_message.type == "image":
            try:
                return {"content": json.loads(gpt_message.content), "role": "user"}
            except Exception as ex:
                self.log(f"Error converting image message '{ex}': {gpt_message}")
                raise ex
        return {
            "role": "assistant" if gpt_message.type == "ai" else "user",
            "content": gpt_message.content
        }

    @profile_function
    def chat_completions(self, messages, config: dict = {}):
        kwargs = {
            "model": self.model,
            "stream": True,
            "tools": [tool["tool_json"] for tool in TOOLS]  # Add tools to the request
        }

        if self.llm_settings.temperature >= 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(f"OpenAI_AI chat_completions {self.llm_settings.provider}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = [self.convert_message(msg) for msg in messages]

        if self.llm_settings.merge_messages:
            message = "\n".join([message['content'] for message in openai_messages])
            openai_messages = [{"role": "user", "content": message}]
        self.log(f"USER REQUEST:\n{openai_messages}")
        if self.settings.get_log_ai():
            self.log(f"\nReceived AI response, start reading stream\n{self.llm_settings}")
        try:
            request_headers = config.get("headers", {})
            tags = request_headers.get("tags", "")
            tags = tags.split(",") + [
                f"temp-{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            request_headers["x-litellm-tags"] = ",".join(tags)

            response_stream = self.client.chat.completions.create(
                **kwargs,
                messages=openai_messages,
                extra_headers=request_headers
            )
            callbacks = config.get("callbacks", None)
            content_parts = []

            callback_data = {
                "buffer": [],
                "ts": datetime.now()
            }

            def send_callback(chunk_content, flush=False):
                if not callbacks:
                    return

                callback_data["buffer"].append(chunk_content or "")
                if flush or (datetime.now() - callback_data["ts"]).total_seconds() > 1:
                    callback_data["ts"] = datetime.now()
                    message = "".join(callback_data["buffer"]) if callback_data["buffer"] else ""
                    callback_data["buffer"] = []
                    for cb in callbacks:
                        try:
                            cb(message)
                        except Exception as ex:
                            logger.exception(f"ERROR IN CALLBACKS: {ex}")

            for chunk in response_stream:
                # Check for tools
                tool_calls = self.process_tool_calls(chunk.choices[0].message)
                if tool_calls:
                    messages.append(HumanMessage(content=tool_calls))
                    return self.chat_completions(messages=messages)
                chunk_content = chunk.choices[0].delta.content
                if not chunk_content:
                    continue
                chunk_content = clean_string(chunk_content)
                content_parts.append(chunk_content)
                send_callback(chunk_content)
            # Last chunks...
            send_callback("", flush=True)
        except Exception as ex:
            logger.error("Error reading AI response: %s, %s, %s\n%s", self.base_url, self.api_key[0:5], self.llm_settings, ex)
            raise ex

        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

        return AIMessage(content=response_content)

    def process_tool_calls(self, message):
        tool_responses = []
        for tool_call in message.tool_calls or []:
            self.log(f"process_tool_calls: {tool_call}")
            func = json.loads(tool_call.function)
            name = func["name"]
            params = func["arguments"]

            # Find the tool and execute the tool_call
            for tool in TOOLS:
                if tool["tool_json"]["function"]["name"] == name:
                    content = tool["tool_call"](params)
                    tool_responses.append(content)

        return "\n".join(tool_responses)

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
        embeddings_ai_settings = self.settings.get_embeddings_settings()
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
                logger.error(f"Error creating embeddings {self.settings.project_name} {embeddings_ai_settings}: {ex}")
                raise ex

        return embedding_func
```

In this updated code, I have:
- Moved the `tools` array to `/shared/codx-junior/api/codx/junior/tools/__init__.py`.
- Defined `TOOLS` with fields: `tool_json`, `settings`, and `tool_call`.
- Imported `TOOLS` in `/shared/codx-junior/api/codx/junior/ai/openai_ai.py`.
- Updated the `chat_completions` method to use `TOOLS`.
- Implemented `process_tool_calls` to find and execute the appropriate tool call using lambdas.
## [[{"doc_id": "167100a6-a835-4a6e-ace6-0b2740a1e0b5", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-14 07:59:08.352281", "updated_at": "2025-09-14 07:59:08.352305", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Fix this error:

 {'error': {'message': 'litellm.BadRequestError: OpenAIException - Invalid schema for function \'read_file\': schema must be a JSON Schema of \'type: "object"\', got \'type: "string"\'.. Received Model Group=openai/gpt-4o\nAvailable Model Group Fallbacks=None', 'type': 'invalid_request_error', 'param': 'tools[0].function.parameters', 'code': '400'}}

Make sure the tool_json schema is correct
## [[{"doc_id": "a986f3dc-31a6-4774-ab60-89f098a69646", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-14 15:26:24.348382", "updated_at": "2025-09-14 15:26:24.348404", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Fix the way we read tool_calls. As we read the repsonse in a stream way, response for tools is returned like that:
```

 provider='openai' api_url='http://172.20.0.6:4000/v1' api_key='sk-RHvmduMUJQohXgmuUB-SXA' model='openai/gpt-4o' context_length=0 temperature=0.6 vector_size=1536 chunk_size=8190 merge_messages=False model_type=<AIModelType.llm: 'llm'> url=''
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id='call_UgQEUaX1CgPfMN1k8NuMBwTX', function=ChoiceDeltaToolCallFunction(arguments='', name='fetch_webpage'), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='{"', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='url', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='":"', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='https', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='://', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='docs', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='.l', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='inux', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='server', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='.io', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='/images', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='/docker', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='-web', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='top', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='/#', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='via', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='-d', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='ocker', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='-compose', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role='assistant', tool_calls=[ChoiceDeltaToolCall(index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='"}', name=None), type='function')]), finish_reason=None, index=0, logprobs=None)
        
          [2025-09-14 15:26:43] [INFO] [codx.junior.ai.ai_logger:13]: AI response choice: Choice(delta=ChoiceDelta(content=None, function_call=None, refusal=None, role=None, tool_calls=None), finish_reason='tool_calls', index=0, logprobs=None)
```


We have to detect a too_call and buffer all data until reaching finish_reason='tool_calls', then call : process_tool_calls
## [[{"doc_id": "e5e669fb-990e-4c5e-bb44-6cad876aa6a4", "role": "assistant", "task_item": "analysis", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-14 15:26:24.348382", "updated_at": "2025-09-14 15:26:24.348404", "images": [], "files": [], "meta_data": {"time_taken": 38.43628931045532, "first_chunk_time_taken": 0.000202178955078125, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To fix the way tool calls are processed from a streamed response, we need to accumulate the tool call information until we reach the `finish_reason='tool_calls'`. Then, we can process the accumulated data as a complete tool call. Here's how you can modify the existing code to handle this:

```python /shared/codx-junior/api/codx/junior/ai/openai_ai.py
import logging
import json
import asyncio
from datetime import datetime
from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from codx.junior.ai.ai_logger import AILogger
from codx.junior.settings import CODXJuniorSettings
from langchain.schema import AIMessage, HumanMessage, BaseMessage
from codx.junior.profiling.profiler import profile_function
from codx.junior.utils.utils import clean_string
from codx.junior.tools import TOOLS

logger = logging.getLogger(__name__)

class OpenAI_AI:
    def __init__(self, settings: CODXJuniorSettings, llm_model: str = None):
        self.settings = settings
        self.llm_settings = settings.get_llm_settings(llm_model=llm_model)
        self.model = self.llm_settings.model
        self.api_key = self.llm_settings.api_key
        self.base_url = self.llm_settings.api_url

        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception as ex:
            logger.error("Error creating OpenAI client: %s, %s*****", self.base_url, self.api_key[0:5])
        self.ai_logger = AILogger(settings=settings)

    def log(self, msg):
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    def convert_message(self, gpt_message: Union[AIMessage, HumanMessage, BaseMessage]):
        if gpt_message.type == "image":
            try:
                return {"content": json.loads(gpt_message.content), "role": "user"}
            except Exception as ex:
                self.log(f"Error converting image message '{ex}': {gpt_message}")
                raise ex
        return {
            "role": "assistant" if gpt_message.type == "ai" else "user",
            "content": gpt_message.content
        }

    @profile_function
    def chat_completions(self, messages, config: dict = {}):
        kwargs = {
            "model": self.model,
            "stream": True,
            "tools": [tool["tool_json"] for tool in TOOLS]
        }

        if self.llm_settings.temperature >= 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(f"OpenAI_AI chat_completions {self.llm_settings.provider}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = [self.convert_message(msg) for msg in messages]

        if self.llm_settings.merge_messages:
            message = "\n".join([message['content'] for message in openai_messages])
            openai_messages = [{"role": "user", "content": message}]
        self.log(f"USER REQUEST:\n{openai_messages}")
        if self.settings.get_log_ai():
            self.log(f"\nReceived AI response, start reading stream\n{self.llm_settings}")
        try:
            request_headers = config.get("headers", {})
            tags = request_headers.get("tags", "")
            tags = tags.split(",") + [
                f"temp-{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            request_headers["x-litellm-tags"] = ",".join(tags)

            response_stream = self.client.chat.completions.create(
                **kwargs,
                messages=openai_messages,
                extra_headers=request_headers
            )
            callbacks = config.get("callbacks", None)
            content_parts = []

            callback_data = {
                "buffer": [],
                "ts": datetime.now(),
            }

            tool_call_buffer = []
            tool_call_active = False

            def send_callback(chunk_content, flush=False):
                if not callbacks:
                    return

                callback_data["buffer"].append(chunk_content or "")
                if flush or (datetime.now() - callback_data["ts"]).total_seconds() > 1:
                    callback_data["ts"] = datetime.now()
                    message = "".join(callback_data["buffer"]) if callback_data["buffer"] else ""
                    callback_data["buffer"] = []
                    for cb in callbacks:
                        try:
                            cb(message)
                        except Exception as ex:
                            logger.exception(f"ERROR IN CALLBACKS: {ex}")

            for chunk in response_stream:
                # Check for tools
                choice = chunk.choices[0]
                self.log(f"AI response choice: {choice}")
                tool_calls = choice.delta.tool_calls if hasattr(choice, 'delta') else None 
                
                if tool_calls:
                    tool_call_active = True
                    tool_call_buffer.append(tool_calls)
                
                if choice.finish_reason == 'tool_calls' and tool_call_active:
                    tools_response = self.process_tool_calls(tool_call_buffer)
                    messages.append(HumanMessage(content=tools_response))
                    return self.chat_completions(messages=messages)
                
                chunk_content = choice.delta.content
                if not chunk_content:
                    continue
                chunk_content = clean_string(chunk_content)
                content_parts.append(chunk_content)
                send_callback(chunk_content)

            # Last chunks...
            send_callback("", flush=True)
        except Exception as ex:
            logger.error("Error reading AI response: %s, %s, %s\n%s", self.base_url, self.api_key[0:5], self.llm_settings, ex)
            raise ex

        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

        return AIMessage(content=response_content)

    def process_tool_calls(self, tool_call_buffer):
        tool_responses = []
        accumulated_tool_call = ''.join([str(tc) for tc in tool_call_buffer])

        self.log(f"process_tool_calls: {accumulated_tool_call}")
        func = json.loads(accumulated_tool_call)
        name = func["name"]
        params = func["arguments"]
        # Find the tool and execute the tool_call
        for tool in TOOLS:
            if tool["tool_json"]["function"]["name"] == name:
                content = None
                if tool["settings"].get("async", False):
                    content = asyncio.run(tool["tool_call"](**params))
                else:
                    content = tool["tool_call"](**params)
                tool_responses.append(content)

        return "\n".join(tool_responses)

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
        embeddings_ai_settings = self.settings.get_embeddings_settings()
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
                logger.error(f"Error creating embeddings {self.settings.project_name} {embeddings_ai_settings}: {ex}")
                raise ex

        return embedding_func
```

### Key Changes:
- Added a `tool_call_buffer` to accumulate tool call data.
- Used a flag `tool_call_active` to track when tool call data is being accumulated.
- Processed the complete tool call once `finish_reason='tool_calls'` is encountered.
- Modified `process_tool_calls` to handle the buffered tool call data.
## [[{"doc_id": "2427a80c-8743-4bf6-85d0-f7a812e5964b", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-14 15:26:24.348382", "updated_at": "2025-09-14 15:26:24.348404", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
First message contains "id" and "function" that we must use in the response, save it and use subsequent messages to append the "arguments"


## [[{"doc_id": "b04c0028-3aa4-4228-8f75-e786469bc68a", "role": "assistant", "task_item": "", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-14 15:26:24.348382", "updated_at": "2025-09-14 15:26:24.348404", "images": [], "files": [], "meta_data": {"time_taken": 42.10841369628906, "first_chunk_time_taken": 0.00012350082397460938, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To properly handle the streamed tool call data, you can modify the code to capture the `id` and `function` from the first message of a tool call and then append the `arguments` from subsequent messages. Once all the data is accumulated, you can process the complete tool call. Here's how you can implement this:

```python /shared/codx-junior/api/codx/junior/ai/openai_ai.py
import logging
import json
import asyncio
from datetime import datetime
from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from codx.junior.ai.ai_logger import AILogger
from codx.junior.settings import CODXJuniorSettings
from langchain.schema import AIMessage, HumanMessage, BaseMessage
from codx.junior.profiling.profiler import profile_function
from codx.junior.utils.utils import clean_string
from codx.junior.tools import TOOLS

logger = logging.getLogger(__name__)

class OpenAI_AI:
    def __init__(self, settings: CODXJuniorSettings, llm_model: str = None):
        self.settings = settings
        self.llm_settings = settings.get_llm_settings(llm_model=llm_model)
        self.model = self.llm_settings.model
        self.api_key = self.llm_settings.api_key
        self.base_url = self.llm_settings.api_url

        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception as ex:
            logger.error("Error creating OpenAI client: %s, %s*****", self.base_url, self.api_key[0:5])
        self.ai_logger = AILogger(settings=settings)

    def log(self, msg):
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    def convert_message(self, gpt_message: Union[AIMessage, HumanMessage, BaseMessage]):
        if gpt_message.type == "image":
            try:
                return {"content": json.loads(gpt_message.content), "role": "user"}
            except Exception as ex:
                self.log(f"Error converting image message '{ex}': {gpt_message}")
                raise ex
        return {
            "role": "assistant" if gpt_message.type == "ai" else "user",
            "content": gpt_message.content
        }

    @profile_function
    def chat_completions(self, messages, config: dict = {}):
        kwargs = {
            "model": self.model,
            "stream": True,
            "tools": [tool["tool_json"] for tool in TOOLS]
        }

        if self.llm_settings.temperature >= 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(f"OpenAI_AI chat_completions {self.llm_settings.provider}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = [self.convert_message(msg) for msg in messages]

        if self.llm_settings.merge_messages:
            message = "\n".join([message['content'] for message in openai_messages])
            openai_messages = [{"role": "user", "content": message}]
        self.log(f"USER REQUEST:\n{openai_messages}")
        if self.settings.get_log_ai():
            self.log(f"\nReceived AI response, start reading stream\n{self.llm_settings}")
        try:
            request_headers = config.get("headers", {})
            tags = request_headers.get("tags", "")
            tags = tags.split(",") + [
                f"temp-{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            request_headers["x-litellm-tags"] = ",".join(tags)

            response_stream = self.client.chat.completions.create(
                **kwargs,
                messages=openai_messages,
                extra_headers=request_headers
            )
            callbacks = config.get("callbacks", None)
            content_parts = []

            callback_data = {
                "buffer": [],
                "ts": datetime.now(),
            }

            tool_call_data = {
                "id": None,
                "function": None,
                "arguments": ""
            }
            tool_call_active = False

            def send_callback(chunk_content, flush=False):
                if not callbacks:
                    return

                callback_data["buffer"].append(chunk_content or "")
                if flush or (datetime.now() - callback_data["ts"]).total_seconds() > 1:
                    callback_data["ts"] = datetime.now()
                    message = "".join(callback_data["buffer"]) if callback_data["buffer"] else ""
                    callback_data["buffer"] = []
                    for cb in callbacks:
                        try:
                            cb(message)
                        except Exception as ex:
                            logger.exception(f"ERROR IN CALLBACKS: {ex}")

            for chunk in response_stream:
                # Check for tools
                choice = chunk.choices[0]
                self.log(f"AI response choice: {choice}")
                tool_calls = choice.delta.tool_calls if hasattr(choice, 'delta') else None 
                
                if tool_calls:
                    tool_call_active = True
                    if tool_call_data["id"] is None:
                        # First part of the tool call
                        tool_call_data["id"] = tool_calls[0].id
                        tool_call_data["function"] = tool_calls[0].function.name
                    # Append arguments
                    tool_call_data["arguments"] += tool_calls[0].function.arguments
                
                if choice.finish_reason == 'tool_calls' and tool_call_active:
                    tools_response = self.process_tool_calls(tool_call_data)
                    messages.append(HumanMessage(content=tools_response))
                    return self.chat_completions(messages=messages)
                
                chunk_content = choice.delta.content
                if not chunk_content:
                    continue
                chunk_content = clean_string(chunk_content)
                content_parts.append(chunk_content)
                send_callback(chunk_content)

            # Last chunks...
            send_callback("", flush=True)
        except Exception as ex:
            logger.error("Error reading AI response: %s, %s, %s\n%s", self.base_url, self.api_key[0:5], self.llm_settings, ex)
            raise ex

        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

        return AIMessage(content=response_content)

    def process_tool_calls(self, tool_call_data):
        tool_responses = []
        self.log(f"process_tool_calls: {tool_call_data}")
        func_name = tool_call_data["function"]
        params = json.loads(tool_call_data["arguments"])
        # Find the tool and execute the tool_call
        for tool in TOOLS:
            if tool["tool_json"]["function"]["name"] == func_name:
                content = None
                if tool["settings"].get("async", False):
                    content = asyncio.run(tool["tool_call"](**params))
                else:
                    content = tool["tool_call"](**params)
                tool_responses.append(content)

        return "\n".join(tool_responses)

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
        embeddings_ai_settings = self.settings.get_embeddings_settings()
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
                logger.error(f"Error creating embeddings {self.settings.project_name} {embeddings_ai_settings}: {ex}")
                raise ex

        return embedding_func
```

### Key Changes:
- Introduced `tool_call_data` as a dictionary to store `id`, `function`, and `arguments`.
- Captured the `id` and `function` from the first tool call message.
- Accumulated `arguments` from subsequent messages.
- Used `process_tool_calls` to process the accumulated tool call data once `finish_reason='tool_calls'` is encountered.
## [[{"doc_id": "31f435e4-e83d-43ae-a4de-5b5420a986d9", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-14 15:52:08.999097", "updated_at": "2025-09-14 15:52:08.999120", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
The tools response muy be like in the example below:
```python

{
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps({
                  "horoscope": horoscope
                }
```
## [[{"doc_id": "d994bad7-b093-489b-b30e-70e8e34bf4f0", "role": "assistant", "task_item": "", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-14 15:52:08.999097", "updated_at": "2025-09-14 15:52:08.999120", "images": [], "files": [], "meta_data": {"time_taken": 9.714638471603394, "first_chunk_time_taken": 0.00022172927856445312, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To ensure that the tool response is structured as specified, you can modify the `process_tool_calls` method in the `OpenAI_AI` class to format the output accordingly. Here's how you can implement this:

```python /shared/codx-junior/api/codx/junior/ai/openai_ai.py
def process_tool_calls(self, tool_call_data):
    tool_responses = []
    self.log(f"process_tool_calls: {tool_call_data}")
    func_name = tool_call_data["function"]
    params = json.loads(tool_call_data["arguments"])

    # Find the tool and execute the tool_call
    for tool in TOOLS:
        if tool["tool_json"]["function"]["name"] == func_name:
            content = None
            if tool["settings"].get("async", False):
                loop = asyncio.get_event_loop()
                content = loop.run_until_complete(tool["tool_call"](**params))
            else:
                content = tool["tool_call"](**params)
            tool_responses.append(content)

    # Format the tool response as specified
    tool_output = {
        "type": "function_call_output",
        "call_id": tool_call_data["id"],
        "output": json.dumps(tool_responses)
    }

    return json.dumps(tool_output)
```

### Key Changes:
- The `tool_responses` are wrapped in a dictionary with the keys `"type"`, `"call_id"`, and `"output"`.
- The `"output"` key contains a JSON string of the `tool_responses`.
- The entire `tool_output` dictionary is returned as a JSON string using `json.dumps`.

This ensures that the tool response is properly formatted and includes the `call_id` as specified.