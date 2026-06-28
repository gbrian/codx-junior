import logging
import json
import os
import time
import uuid

from datetime import datetime, date
from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam

from codx.junior.ai.ai_logger import AILogger
from codx.junior.ai.raw_logger import RawAILogger, STATUS_SUCCESS, STATUS_CANCELLED, STATUS_ERROR
from codx.junior.ai.cancellation import CancellationToken, CancelledError
from codx.junior.ai.wallet_check import check_user_wallet
from codx.junior.settings import CODXJuniorSettings
from langchain.messages import AIMessage, HumanMessage
from codx.junior.profiling.profiler import profile_function
from codx.junior.utils.utils import (
  clean_string, 
  asyncify,
  create_file_logger
)
from codx.junior.model.model import CodxUser
from codx.junior.analytics import Analytics        
from codx.junior.analytics.token_counter import count_tokens, count_messages_tokens

logger = logging.getLogger(__name__)

_analytics_instance = None

def _get_analytics():
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = Analytics()
    return _analytics_instance


def _new_request_id() -> str:
    """Generate a new unique request id."""
    return str(uuid.uuid4())


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

        # Raw request/response logger — enabled when a log path is configured
        self.raw_logger: RawAILogger = RawAILogger()

    # ── Raw logging helpers ────────────────────────────────────────────────────

    def _raw_log_ctx(self, session_id, tags_joined, request_id, parent_request_id):
        """Return the common kwargs shared by all raw-log calls."""
        return dict(
            provider=self.llm_settings.provider or "",
            model=self.model,
            base_url=self.base_url,
            username=self.user.username if self.user else "anonymous",
            project=self.settings.project_name or "",
            session_id=session_id,
            tags=tags_joined,
            request_id=request_id,
            parent_request_id=parent_request_id,
        )

    def _raw_log_request(
        self,
        openai_messages,
        kwargs,
        request_id: str,
        session_id=None,
        tags="",
        parent_request_id=None,
    ):
        if not self.raw_logger:
            return
        try:
            self.raw_logger.log_request(
                **self._raw_log_ctx(session_id, tags, request_id, parent_request_id),
                messages=openai_messages,
                kwargs=kwargs,
            )
        except Exception as ex:
            logger.warning("_raw_log_request failed (non-fatal): %s", ex)

    def _raw_log_response(
        self,
        content_parts,
        duration_seconds,
        request_id: str,
        session_id=None,
        tags="",
        finish_reason=None,
        tool_calls=None,
        parent_request_id=None,
        status=STATUS_SUCCESS,
    ):
        if not self.raw_logger:
            return
        try:
            self.raw_logger.log_response(
                **self._raw_log_ctx(session_id, tags, request_id, parent_request_id),
                content_parts=content_parts,
                finish_reason=finish_reason,
                tool_calls=tool_calls,
                duration_seconds=duration_seconds,
                status=status,
            )
        except Exception as ex:
            logger.warning("_raw_log_response failed (non-fatal): %s", ex)

    def _raw_log_error(
        self,
        error: Exception,
        duration_seconds: float,
        request_id: str,
        session_id=None,
        tags="",
        parent_request_id=None,
        status=STATUS_ERROR,
    ):
        if not self.raw_logger:
            return
        try:
            self.raw_logger.log_error(
                **self._raw_log_ctx(session_id, tags, request_id, parent_request_id),
                error=error,
                duration_seconds=duration_seconds,
                status=status,
            )
        except Exception as ex:
            logger.warning("_raw_log_error failed (non-fatal): %s", ex)

    # ── Existing helpers (unchanged) ───────────────────────────────────────────

    def _preflight_limit_check(self) -> None:
        """
        Run pre-flight wallet check before executing an AI request.
        Raises InsufficientFundsError when the user has exhausted their budget.
        """
        input_k_tokens_cxjcoins, output_k_tokens_cxjcoins = self._get_model_cost()

        # Check wallet if model has price
        if input_k_tokens_cxjcoins or output_k_tokens_cxjcoins:
            check_user_wallet(user=self.user)

    def _get_model_cost(self):
        input_k_tokens_cxjcoins: float = getattr(self.llm_settings, "input_k_tokens_cxjcoins", 0.0) or 0.0
        output_k_tokens_cxjcoins: float = getattr(self.llm_settings, "output_k_tokens_cxjcoins", 0.0) or 0.0
        return input_k_tokens_cxjcoins, output_k_tokens_cxjcoins

    def _record_usage(
        self,
        input_text: str,
        output_text: str,
        duration_seconds: float = 0.0,
        tags: str = "",
        session_id: str = None,
        request_id: str = None,
        usage_info=None,
    ) -> None:
        try:
            analytics = _get_analytics()
            
            input_tokens = 0
            output_tokens = 0
            tokens_from_provider = False

            if usage_info is not None:
                if hasattr(usage_info, "prompt_tokens"):
                    tokens_from_provider = True
                    input_tokens = getattr(usage_info, "prompt_tokens") or 0
                    
                elif isinstance(usage_info, dict) and "prompt_tokens" in usage_info:
                    tokens_from_provider = True
                    input_tokens = usage_info.get("prompt_tokens") or 0
                
                if hasattr(usage_info, "completion_tokens"):
                    output_tokens = getattr(usage_info, "completion_tokens") or 0
                elif isinstance(usage_info, dict):
                    output_tokens = usage_info.get("completion_tokens") or 0

            # Fallback to auto-calculated values if native values are unavailable or zero
            if not input_tokens:
                input_tokens = count_tokens(input_text, model=self.model)
            if not output_tokens:
                output_tokens = count_tokens(output_text, model=self.model)

            input_k_tokens_cxjcoins, output_k_tokens_cxjcoins = self._get_model_cost()

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
                input_k_tokens_cxjcoins=input_k_tokens_cxjcoins,
                output_k_tokens_cxjcoins=output_k_tokens_cxjcoins,
                request_id=request_id,
                tokens_from_provider=tokens_from_provider,
            )
        except Exception as ex:
            logger.warning("_record_usage failed (non-fatal): %s", ex)

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
        self._preflight_limit_check()

        # Each call gets a fresh unique request_id.
        # A parent_request_id is passed via config when this call was spawned
        # from a tool-call response in a_chat_completions.
        request_id: str = _new_request_id()
        parent_request_id: str = config.get("parent_request_id", None)

        kwargs = {
            "model": self.model,
            "stream": True,
            "stream_options": {"include_usage": True},
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

        request_headers = config.get("headers", {})
        tags_str = request_headers.get("tags", "")
        session_id = request_headers.get("session_id", None)

        request_start = time.monotonic()
        tags_joined = ""
        usage_info = None

        try:
            tags = tags_str.split(",") + [
                f"temperature:{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            if self.user:
                tags.append(f"user:{self.user.username}")
            request_headers["x-litellm-tags"] = ",".join(tags)

            tags_joined = ",".join(tags)

            # ── Raw-log the outgoing request ───────────────────────────────────
            self._raw_log_request(
                openai_messages=openai_messages,
                kwargs=kwargs,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
            )

            try:
                response_stream = self.client.chat.completions.create(
                    **kwargs,
                    messages=openai_messages,
                    extra_headers=request_headers
                )
            except Exception as ex:
                if "stream_options" in kwargs:
                    logger.warning("Failed to create chat completion with stream_options, retrying without: %s", ex)
                    kwargs.pop("stream_options", None)
                    response_stream = self.client.chat.completions.create(
                        **kwargs,
                        messages=openai_messages,
                        extra_headers=request_headers
                    )
                else:
                    raise

            callbacks = config.get("callbacks", None)
            content_parts = []
            last_finish_reason = None

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
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    usage_info = chunk.usage

                if cancellation_token and cancellation_token.is_cancelled:
                    logger.info("chat_completions: cancellation requested, closing stream")
                    try:
                        response_stream.close()
                    except Exception:
                        pass
                    send_callback("", flush=True)
                    raise CancelledError("Chat completion was cancelled by the caller.")

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                if choice.finish_reason:
                    last_finish_reason = choice.finish_reason
                chunk_content = choice.delta.content
                if not chunk_content:
                    continue
                chunk_content = clean_string(chunk_content)
                content_parts.append(chunk_content)
                send_callback(chunk_content)

            send_callback("", flush=True)

        except CancelledError as ex:
            duration_seconds = time.monotonic() - request_start
            self._raw_log_error(
                error=ex,
                duration_seconds=duration_seconds,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
                status=STATUS_CANCELLED,
            )
            raise

        except Exception as ex:
            duration_seconds = time.monotonic() - request_start
            logger.error("Error reading AI response: %s, %s, %s\n%s", self.base_url, self.api_key[0:5], self.llm_settings, ex)
            self._raw_log_error(
                error=ex,
                duration_seconds=duration_seconds,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
                status=STATUS_ERROR,
            )
            raise ex

        duration_seconds = time.monotonic() - request_start
        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

        # ── Raw-log the completed response ─────────────────────────────────────
        self._raw_log_response(
            content_parts=content_parts,
            duration_seconds=duration_seconds,
            request_id=request_id,
            session_id=session_id,
            tags=tags_joined,
            finish_reason=last_finish_reason,
            parent_request_id=parent_request_id,
            status=STATUS_SUCCESS,
        )

        input_text = "\n".join(m.get("content", "") for m in openai_messages)
        self._record_usage(
            input_text=input_text,
            output_text=response_content,
            duration_seconds=duration_seconds,
            tags=tags_joined,
            session_id=session_id,
            request_id=request_id,
            usage_info=usage_info,
        )

        messages.append(AIMessage(content=response_content))
        return messages

    @profile_function
    async def a_chat_completions(self, messages, config: dict = {}):
        self._preflight_limit_check()

        # Each top-level async call gets a fresh unique request_id.
        # A parent_request_id may be passed from an outer tool-call chain.
        request_id: str = _new_request_id()
        parent_request_id: str = config.get("parent_request_id", None)

        kwargs = {
            "model": self.model,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
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

        request_headers = config.get("headers", {})
        tags_str = request_headers.get("tags", "")
        session_id = request_headers.get("session_id", None)

        request_start = time.monotonic()
        tags_joined = ""
        usage_info = None

        try:
            tags = tags_str.split(",") + [
                f"temperature:{self.llm_settings.temperature}",
                self.settings.project_name
            ]
            if self.user:
                tags.append(f"user:{self.user.username}")
            request_headers["x-litellm-tags"] = ",".join(tags)

            tags_joined = ",".join(tags)

            request_params = {
                **kwargs,
                "messages": openai_messages,
                "extra_headers": request_headers
            }
            self.log(f"USER REQUEST:\n{json.dumps(request_params, indent=2)}")

            # ── Raw-log the outgoing request ───────────────────────────────────
            self._raw_log_request(
                openai_messages=openai_messages,
                kwargs=kwargs,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
            )
        
            try:
                response_stream = self.client.chat.completions.create(
                  **request_params
                )
            except Exception as ex:
                if "stream_options" in request_params:
                    logger.warning("Failed to create async chat completion with stream_options, retrying without: %s", ex)
                    request_params.pop("stream_options", None)
                    kwargs.pop("stream_options", None)
                    response_stream = self.client.chat.completions.create(
                        **request_params
                    )
                else:
                    raise

            callbacks = config.get("callbacks", None)
            content_parts = []
            last_finish_reason = None

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
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    usage_info = chunk.usage

                if cancellation_token and cancellation_token.is_cancelled:
                    logger.info("a_chat_completions: cancellation requested, closing stream")
                    try:
                        response_stream.close()
                    except Exception:
                        pass
                    send_callback("", flush=True)
                    raise CancelledError("Async chat completion was cancelled by the caller.")

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                if choice.finish_reason:
                    last_finish_reason = choice.finish_reason
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
                    # ── Raw-log the tool-call response before delegating ────────
                    duration_so_far = time.monotonic() - request_start
                    self._raw_log_response(
                        content_parts=content_parts,
                        duration_seconds=duration_so_far,
                        request_id=request_id,
                        session_id=session_id,
                        tags=tags_joined,
                        finish_reason="tool_calls",
                        tool_calls=all_tool_calls,
                        parent_request_id=parent_request_id,
                        status=STATUS_SUCCESS,
                    )

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

                    # ── Propagate current request_id as parent for the child call ──
                    child_config = {**config, "parent_request_id": request_id}
                    return self.chat_completions(messages=messages, config=child_config)
                
                chunk_content = choice.delta.content
                if not chunk_content:
                    continue
                chunk_content = clean_string(chunk_content)
                content_parts.append(chunk_content)
                send_callback(chunk_content)

            send_callback("", flush=True)

        except CancelledError as ex:
            duration_seconds = time.monotonic() - request_start
            self._raw_log_error(
                error=ex,
                duration_seconds=duration_seconds,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
                status=STATUS_CANCELLED,
            )
            raise

        except Exception as ex:
            duration_seconds = time.monotonic() - request_start
            logger.error("Error reading AI response: %s, %s, %s\n%s", self.base_url, self.api_key[0:5], self.llm_settings, ex)
            self._raw_log_error(
                error=ex,
                duration_seconds=duration_seconds,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
                status=STATUS_ERROR,
            )
            raise ex

        duration_seconds = time.monotonic() - request_start
        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

        # ── Raw-log the completed response ─────────────────────────────────────
        self._raw_log_response(
            content_parts=content_parts,
            duration_seconds=duration_seconds,
            request_id=request_id,
            session_id=session_id,
            tags=tags_joined,
            finish_reason=last_finish_reason,
            tool_calls=all_tool_calls if all_tool_calls else None,
            parent_request_id=parent_request_id,
            status=STATUS_SUCCESS,
        )

        input_text = "\n".join(m.get("content", "") for m in openai_messages
                               if isinstance(m.get("content"), str))
        self._record_usage(
            input_text=input_text,
            output_text=response_content,
            duration_seconds=duration_seconds,
            tags=tags_joined,
            session_id=session_id,
            request_id=request_id,
            usage_info=usage_info,
        )

        messages.append(AIMessage(content=response_content))
        return messages

    @profile_function
    async def process_tool_calls(self, tool_call_data):
        tool_response = None
        self.log(f"process_tool_calls: {tool_call_data}")
        func_name = tool_call_data["function"]
        params = json.loads(tool_call_data["arguments"])
        
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