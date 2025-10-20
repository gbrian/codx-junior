import logging
import json

from datetime import datetime
from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from codx.junior.ai.ai_logger import AILogger
from codx.junior.settings import CODXJuniorSettings
from langchain.schema import AIMessage, HumanMessage, BaseMessage
from codx.junior.profiling.profiler import profile_function
from codx.junior.utils.utils import clean_string, asyncify
from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)

class OpenAI_AI:
    def __init__(self, settings: CODXJuniorSettings, llm_model: str = None, user: CodxUser = None):
        from codx.junior.tools import TOOLS
        self.tools = TOOLS
        
        self.settings = settings
        self.llm_settings = settings.get_llm_settings(llm_model=llm_model)
        self.model = self.llm_settings.model
        self.user = user
        self.api_key = self.user.api_key if self.user and self.user.api_key else self.llm_settings.api_key
        self.base_url = self.llm_settings.api_url

        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info("Creating OpenAI client. USER: %s, URL: %s, API: %s*****", 
                self.user.username if self.user else "NONE",
                self.base_url,
                self.api_key[0:15])
        except Exception as ex:
            logger.error("Error creating OpenAI client: %s, %s*****", self.base_url, self.api_key[0:15])
        self.ai_logger = AILogger(settings=settings)

    def log(self, msg):
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    def convert_message_to_openai(self, gpt_message: Union[AIMessage, HumanMessage, BaseMessage]):
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
        }

        if self.llm_settings.temperature >= 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(f"OpenAI_AI chat_completions {self.llm_settings.provider}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = [self.convert_message_to_openai(msg) for msg in messages]

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
                f"temperature:{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            if self.user:
                tags.append(f"user:{self.user.username}")
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
                choice = chunk.choices[0]
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

        messages.append(AIMessage(content=response_content))
        return messages

    @profile_function
    async def a_chat_completions(self, messages, config: dict = {}):
        kwargs = {
            "model": self.model,
            "stream": True,
            "tools": [tool["tool_json"] for tool in self.tools]
        }

        if self.llm_settings.temperature >= 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(f"OpenAI_AI chat_completions {self.llm_settings.provider}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = [self.convert_message_to_openai(msg) for msg in messages]
                            
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
                f"temperature:{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            if self.user:
                tags.append(f"user:{self.user.username}")
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
            all_tool_calls = {}
            last_tool_id = None

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
                tool_calls = choice.delta.tool_calls if hasattr(choice, 'delta') else None 
                
                if tool_calls:
                    tool_call = tool_calls[0] 
                    if tool_call.id and not all_tool_calls.get(tool_call.id):
                        last_tool_id = tool_call.id
                        all_tool_calls[last_tool_id] = {
                            "id": last_tool_id,
                            "function": "",
                            "arguments": ""
                        }
                    if tool_call.function.name:
                        all_tool_calls[last_tool_id]["function"] += tool_call.function.name
                        
                    all_tool_calls[last_tool_id]["arguments"] += tool_call.function.arguments
                
                if choice.finish_reason == 'tool_calls':
                    ai_tool_response = None
                    for tool_call_data in all_tool_calls.values():
                        func_name = tool_call_data["function"]                      
                        try:
                            tools_response = await self.process_tool_calls(tool_call_data)
                            tool_output = tools_response["output"] if "output" in tools_response else tools_response 
                            content = f"{func_name} returned:\n\n```\n{tool_output}\n```"
                            ai_tool_response = AIMessage(content=content)
                        except Exception as ex:
                            logger.exception("Error processing '%s': %s", func_name, tool_call_data)
                            error = f"Error processing {func_name}:\n{ex}"
                            ai_tool_response = AIMessage(content=error)

                        messages.append(ai_tool_response)

                    return self.chat_completions(messages=messages, config=config)
                
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

        messages.append(AIMessage(content=response_content))
        return messages

    @profile_function
    async def process_tool_calls(self, tool_call_data):
        tool_responses = []
        self.log(f"process_tool_calls: {tool_call_data}")
        func_name = tool_call_data["function"]
        params = json.loads(tool_call_data["arguments"])
        
        # Find the tool and execute the tool_call
        tool = next((t for t in self.tools if t["tool_json"]["function"]["name"] == func_name), None)
        if tool:
            settings = tool.get("settings", {
              "project_settings": False,
              "async": False
            })

            if settings.get("project_settings"):
                params["settings"] = self.settings
            
            content = tool["tool_call"](**params)
            if settings["async"]:
                content = await content
            
            tool_responses.append(content)

        # Format the tool response as specified
        tool_output = {
            "type": "function_call_output",
            "call_id": tool_call_data["id"],
            "output": json.dumps(tool_responses)
        }

        return tool_output
    
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
