import logging
import json
import os
import time

from datetime import datetime
from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from codx.junior.ai.ai_logger import AILogger
from codx.junior.ai.cancellation import CancellationToken, CancelledError
from codx.junior.settings import CODXJuniorSettings
from langchain.messages import AIMessage, HumanMessage
from codx.junior.profiling.profiler import profile_function
from codx.junior.utils.utils import (
  clean_string, 
  asyncify,
  create_file_logger
)
from codx.junior.model.model import CodxUser
from codx.junior.analytics.token_counter import count_tokens, count_messages_tokens
from codx.junior.globals import ANALYTICS_DATA_PATH

logger = logging.getLogger(__name__)

# Lazily imported to avoid circular dependencies at module load time
_analytics_instance = None


def _get_analytics():
    """
    Return a shared Analytics instance backed by the global analytics path,
    creating it once per process.

    The path is sourced from ``ANALYTICS_DATA_PATH`` (globals.py) which reads
    the ``CODX_JUNIOR_API_ANALYTICS_DATA_PATH`` environment variable.

    Returns:
        Analytics instance.
    """
    global _analytics_instance
    if _analytics_instance is None:
        from codx.junior.analytics import Analytics
        _analytics_instance = Analytics(analytics_path=ANALYTICS_DATA_PATH)
    return _analytics_instance


class OpenAI_AI:
    def __init__(self, settings: CODXJuniorSettings, llm_model: str = None, user: CodxUser = None, system: str = None):
        from codx.junior.tools import TOOLS
        self.tools = TOOLS
        
        self.settings = settings
        self.llm_settings = settings.get_llm_settings(llm_model=llm_model)
        self.model = self.llm_settings.model
        self.user = user
        self.api_key = self.user.api_key if self.user and self.user.api_key else self.llm_settings.api_key
        self.base_url = self.llm_settings.api_url
        self.system = system

        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info("Creating OpenAI client. USER: %s, URL: %s, API: %s*****", 
                self.user.username if self.user else "NONE",
                self.base_url,
                self.api_key[0:15])
        except Exception as ex:
            logger.error("Error creating OpenAI client: %s, %s*****", self.base_url, self.api_key[0:15])
        self.ai_logger = AILogger(settings=settings)

    # ── Analytics helper ───────────────────────────────────────────────────────

    def _record_usage(
        self,
        input_text: str,
        output_text: str,
        duration_seconds: float = 0.0,
        tags: str = "",
        session_id: str = None,
    ) -> None:
        """
        Estimate token counts and persist a ``TokenUsageEvent`` to the global
        analytics store.

        Called after every successful chat completion (streaming or not).
        Failures are logged but never re-raised so they don't break the caller.

        Args:
            input_text:        Concatenated prompt text sent to the model.
            output_text:       Response text received from the model.
            duration_seconds:  Wall-clock seconds for the full request/response cycle.
            tags:              Comma-separated request tags.
            session_id:        Optional session identifier from request headers.
        """
        try:
            analytics = _get_analytics()
            input_tokens = count_tokens(input_text, model=self.model)
            output_tokens = count_tokens(output_text, model=self.model)

            analytics.record_token_usage(
                username=self.user.username if self.user else "anonymous",
                project_name=self.settings.project_name or "",
                project_id=getattr(self.settings, "project_id", "") or "",
                model=self.model,
                provider=self.llm_settings.provider or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_seconds=duration_seconds,
                session_id=session_id,
                tags=tags,
            )
        except Exception as ex:
            logger.warning("_record_usage failed (non-fatal): %s", ex)

    # ── Existing methods ───────────────────────────────────────────────────────

    def log(self, msg):
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    def convert_message_to_openai(self, gpt_message: Union[AIMessage, HumanMessage]):
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

    def preparer_messages_to_openai(self, messages):
        oai_messages = [self.convert_message_to_openai(msg) for msg in messages]
        system_content = "\n".join([self.llm_settings.system or "", self.system or ""]).strip()
        if system_content:
            oai_messages = [{
              "role": "system",
              "content": system_content
            }] + oai_messages
        return oai_messages

    @profile_function
    def chat_completions(self, messages, config: dict = {}):
        kwargs = {
            "model": self.model,
            "stream": True,
        }

        if self.llm_settings.temperature >= 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(f"OpenAI_AI chat_completions {self.llm_settings.provider}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = self.preparer_messages_to_openai(messages=messages) 

        if self.llm_settings.merge_messages:
            message = "\n".join([message['content'] for message in openai_messages])
            openai_messages = [{"role": "user", "content": message}]
        self.log(f"USER REQUEST:\n{json.dumps(openai_messages, indent=2)}")
        if self.settings.get_log_ai():
            self.log(f"\nReceived AI response, start reading stream\n{self.llm_settings}")

        cancellation_token: CancellationToken = config.get("cancellation_token", None)

        # Capture request metadata for analytics
        request_headers = config.get("headers", {})
        tags_str = request_headers.get("tags", "")
        session_id = request_headers.get("session_id", None)

        # Start wall-clock timer for the full request/response cycle
        request_start = time.monotonic()

        try:
            tags = tags_str.split(",") + [
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
                # Check for cancellation before processing each chunk
                if cancellation_token and cancellation_token.is_cancelled:
                    logger.info("chat_completions: cancellation requested, closing stream")
                    try:
                        response_stream.close()
                    except Exception:
                        pass
                    send_callback("", flush=True)
                    raise CancelledError("Chat completion was cancelled by the caller.")

                choice = chunk.choices[0]
                chunk_content = choice.delta.content
                if not chunk_content:
                    continue
                chunk_content = clean_string(chunk_content)
                content_parts.append(chunk_content)
                send_callback(chunk_content)

            # Last chunks...
            send_callback("", flush=True)
        except CancelledError:
            raise
        except Exception as ex:
            logger.error("Error reading AI response: %s, %s, %s\n%s", self.base_url, self.api_key[0:5], self.llm_settings, ex)
            raise ex

        duration_seconds = time.monotonic() - request_start
        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

        # ── Record token usage ────────────────────────────────────────────────
        input_text = "\n".join(m.get("content", "") for m in openai_messages)
        self._record_usage(
            input_text=input_text,
            output_text=response_content,
            duration_seconds=duration_seconds,
            tags=",".join(tags) if isinstance(tags, list) else tags_str,
            session_id=session_id,
        )

        messages.append(AIMessage(content=response_content))
        return messages

    @profile_function
    async def a_chat_completions(self, messages, config: dict = {}):
        kwargs = {
            "model": self.model,
            "stream": True,
        }
        # tools
        selected_tools = config.get("tools", [])
        chat_tools = [t for t in self.tools if t["tool_json"]["function"]["name"] in selected_tools]
        if chat_tools:
            kwargs["tools"] = chat_tools
        

        if self.llm_settings.temperature >= 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(f"OpenAI_AI chat_completions {self.llm_settings.provider}: {self.model} {self.base_url} {self.api_key[0:6]}...")

        openai_messages = self.preparer_messages_to_openai(messages=messages)
                            
        if self.llm_settings.merge_messages:
            message = "\n".join([message['content'] for message in openai_messages])
            openai_messages = [{"role": "user", "content": message}]

        cancellation_token: CancellationToken = config.get("cancellation_token", None)

        # Capture request metadata for analytics
        request_headers = config.get("headers", {})
        tags_str = request_headers.get("tags", "")
        session_id = request_headers.get("session_id", None)

        # Start wall-clock timer for the full request/response cycle
        request_start = time.monotonic()

        try:
            tags = tags_str.split(",") + [
                f"temperature:{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            if self.user:
                tags.append(f"user:{self.user.username}")
            request_headers["x-litellm-tags"] = ",".join(tags)

            request_params = {
                **kwargs,
                "messages": openai_messages,
                "extra_headers": request_headers
            }
            self.log(f"USER REQUEST:\n{json.dumps(request_params, indent=2)}")
        
            response_stream = self.client.chat.completions.create(
              **request_params
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

            if self.settings.get_log_ai():
                self.log(f"\nReceived AI response, start reading stream\n{self.llm_settings}")

            for chunk in response_stream:
                # Check for cancellation before processing each chunk
                if cancellation_token and cancellation_token.is_cancelled:
                    logger.info("a_chat_completions: cancellation requested, closing stream")
                    try:
                        response_stream.close()
                    except Exception:
                        pass
                    send_callback("", flush=True)
                    raise CancelledError("Async chat completion was cancelled by the caller.")

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
                            ai_tool_response = AIMessage(content=tool_output)
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
        except CancelledError:
            raise
        except Exception as ex:
            logger.error("Error reading AI response: %s, %s, %s\n%s", self.base_url, self.api_key[0:5], self.llm_settings, ex)
            raise ex

        duration_seconds = time.monotonic() - request_start
        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

        # ── Record token usage ────────────────────────────────────────────────
        input_text = "\n".join(m.get("content", "") for m in openai_messages
                               if isinstance(m.get("content"), str))
        self._record_usage(
            input_text=input_text,
            output_text=response_content,
            duration_seconds=duration_seconds,
            tags=",".join(tags) if isinstance(tags, list) else tags_str,
            session_id=session_id,
        )

        messages.append(AIMessage(content=response_content))
        return messages

    @profile_function
    async def process_tool_calls(self, tool_call_data):
        tool_response = None
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
            
            tool_response = content

        # Format the tool response as specified
        tool_output = {
            "type": "function_call_output",
            "call_id": tool_call_data["id"],
            "output": tool_response
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