import logging
import json
import os
import time
import uuid
import hashlib

from datetime import datetime, date
from typing import Union, Optional, Any, Dict, List, Set, Tuple
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

# ── Constants ──────────────────────────────────────────────────────────────────
# Maximum number of sequential tool-call *rounds* (each round may contain
# multiple parallel tool calls). Raised from 5 to allow legitimate multi-step
# reasoning chains (e.g. reading many files sequentially).
MAX_TOOL_RECURSION_DEPTH: int = 20

# Number of consecutive rounds that must produce the *exact same* tool-call
# fingerprint before we declare an infinite loop and abort.
MAX_IDENTICAL_ROUNDS: int = 3

TOOL_RECURSION_ERROR_MSG: str = (
    "Maximum tool recursion depth ({depth}) exceeded. "
    "The model is repeatedly requesting the same tools without making progress."
)

TOOL_LOOP_DETECTED_MSG: str = (
    "Infinite tool-call loop detected: the model has requested the identical "
    "set of tools with the same arguments {count} times in a row."
)

# ── Singleton analytics instance ───────────────────────────────────────────────
_analytics_instance = None


def _get_analytics() -> Analytics:
    """Return (creating if necessary) the module-level Analytics singleton."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = Analytics()
    return _analytics_instance


def _new_request_id() -> str:
    """Generate a new unique request id."""
    return str(uuid.uuid4())


def _fingerprint_tool_calls(all_tool_calls: Dict[str, Dict[str, Any]]) -> str:
    """
    Produce a stable hash that identifies a *set* of tool calls by their
    function names and arguments.

    This is used to detect when the model is stuck in a loop — i.e. it keeps
    requesting the same tools with the same arguments without making progress.

    The hash is order-independent: two rounds that call the same tools in a
    different order produce the same fingerprint.

    Args:
        all_tool_calls: Mapping of tool_call_id → {id, function, arguments}.

    Returns:
        A hex digest string uniquely representing the tool-call set.
    """
    # Build a sorted list of (function_name, canonical_arguments) tuples so
    # that ordering differences don't produce false negatives.
    entries: List[Tuple[str, str]] = []
    for tc in all_tool_calls.values():
        func_name: str = tc.get("function", "")
        raw_args = tc.get("arguments", "")
        # Normalise arguments: parse then re-serialise with sorted keys so
        # that whitespace / key-order differences are ignored.
        try:
            normalised_args: str = json.dumps(
                json.loads(raw_args) if isinstance(raw_args, str) else raw_args,
                sort_keys=True,
            )
        except (json.JSONDecodeError, TypeError):
            normalised_args = str(raw_args)
        entries.append((func_name, normalised_args))

    entries.sort()  # order-independent
    payload: str = json.dumps(entries)
    return hashlib.sha256(payload.encode()).hexdigest()


# ── Helper: build an OpenAI-compatible tool-result message ────────────────────

def _make_tool_message(tool_call_id: str, content: str) -> Dict[str, Any]:
    """
    Build an OpenAI ``role=tool`` message dict.

    The OpenAI Chat Completions API requires that every tool invocation
    listed in the assistant's ``tool_calls`` array is answered by a
    corresponding message with ``role="tool"`` and the matching
    ``tool_call_id``.  Without this the next completion request will be
    rejected with a 400 error.

    Args:
        tool_call_id: The ``id`` from the assistant's tool_call entry.
        content:      Serialised (string) result returned by the tool.

    Returns:
        A dict ready to be appended to the OpenAI messages list.
    """
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content if isinstance(content, str) else json.dumps(content),
    }


def _make_assistant_tool_calls_message(
    all_tool_calls: Dict[str, Dict[str, Any]],
    content: str = "",
) -> Dict[str, Any]:
    """
    Build the assistant message that records *which* tools were requested.

    The OpenAI API requires that the assistant turn immediately preceding
    the tool-result messages contains the full ``tool_calls`` array.
    Without this the conversation history is malformed and the model will
    refuse the next request.

    Args:
        all_tool_calls: Mapping of tool_call_id → {id, function, arguments}.
        content:        Any partial text content generated before the tool call.

    Returns:
        A dict with ``role="assistant"`` and a ``tool_calls`` list.
    """
    tool_calls_payload = []
    for tc in all_tool_calls.values():
        arguments = tc.get("arguments", "")
        # Ensure arguments is a JSON string (the API requires a string).
        if isinstance(arguments, dict):
            arguments = json.dumps(arguments)
        tool_calls_payload.append({
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["function"],
                "arguments": arguments,
            },
        })
    return {
        "role": "assistant",
        "content": content or "",
        "tool_calls": tool_calls_payload,
    }


class OpenAI_AI:
    """
    Thin wrapper around the OpenAI Python SDK that adds:

    * streaming chat completions (sync & async)
    * multi-step tool/function calling with correct message history
    * raw request/response logging via :class:`RawAILogger`
    * token-usage & tool-usage analytics via :class:`Analytics`
    * per-request cancellation via :class:`CancellationToken`
    * tool recursion depth limiting to prevent infinite loops
    * fingerprint-based loop detection to catch stuck tool-call patterns

    Tool-call flow
    --------------
    .. code-block:: mermaid

        flowchart TD
            A[a_chat_completions] --> B[LLM stream]
            B --> C{finish_reason?}
            C -->|tool_calls| D[Check recursion depth]
            D --> E{depth > MAX?}
            E -->|yes| F[Raise RuntimeError]
            E -->|no| G[Fingerprint tool calls]
            G --> H{Same fingerprint\nMAX_IDENTICAL_ROUNDS times?}
            H -->|yes| I[Raise RuntimeError - loop]
            H -->|no| J[Execute tools]
            J --> K[Append results to history]
            K --> L[Recurse depth+1]
            L --> A
            C -->|stop/length| M[Return final response]
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        llm_model: str = None,
        user: CodxUser = None,
        system: str = None,
    ) -> None:
        from codx.junior.tools import TOOLS
        self.tools = TOOLS

        self.settings = settings
        self.llm_settings = settings.get_llm_settings(llm_model=llm_model)
        self.model = self.llm_settings.model
        self.user = user
        self.api_key = (
            self.user.api_key
            if self.user and self.user.api_key
            else self.llm_settings.api_key
        )
        self.base_url = self.llm_settings.api_url
        self.system = system

        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(
                "Creating OpenAI client. USER: %s, URL: %s, API: %s*****",
                self.user.username if self.user else "NONE",
                self.base_url,
                self.api_key[0:15],
            )
        except OSError as ex:
            logger.error(
                "Error creating OpenAI client: %s, %s*****",
                self.base_url,
                self.api_key[0:15],
                exc_info=ex,
            )
        self.ai_logger = AILogger(settings=settings)

        # Raw request/response logger — enabled when a log path is configured
        self.raw_logger: RawAILogger = RawAILogger()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _raw_log_ctx(
        self,
        session_id: Optional[str],
        tags_joined: str,
        request_id: str,
        parent_request_id: Optional[str],
    ) -> Dict[str, Any]:
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
        openai_messages: List[Dict[str, Any]],
        kwargs: Dict[str, Any],
        request_id: str,
        session_id: Optional[str] = None,
        tags: str = "",
        parent_request_id: Optional[str] = None,
    ) -> None:
        """Log an outgoing LLM request (non-fatal on error)."""
        if not self.raw_logger:
            return
        try:
            self.raw_logger.log_request(
                **self._raw_log_ctx(session_id, tags, request_id, parent_request_id),
                messages=openai_messages,
                kwargs=kwargs,
            )
        except OSError as ex:
            logger.warning("_raw_log_request failed (non-fatal): %s", ex)

    def _raw_log_response(
        self,
        content_parts: List[str],
        duration_seconds: float,
        request_id: str,
        session_id: Optional[str] = None,
        tags: str = "",
        finish_reason: Optional[str] = None,
        tool_calls: Optional[Dict[str, Any]] = None,
        parent_request_id: Optional[str] = None,
        status: str = STATUS_SUCCESS,
    ) -> None:
        """Log a completed LLM response (non-fatal on error)."""
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
        except OSError as ex:
            logger.warning("_raw_log_response failed (non-fatal): %s", ex)

    def _raw_log_error(
        self,
        error: Exception,
        duration_seconds: float,
        request_id: str,
        session_id: Optional[str] = None,
        tags: str = "",
        parent_request_id: Optional[str] = None,
        status: str = STATUS_ERROR,
    ) -> None:
        """Log an LLM error (non-fatal on error)."""
        if not self.raw_logger:
            return
        try:
            self.raw_logger.log_error(
                **self._raw_log_ctx(session_id, tags, request_id, parent_request_id),
                error=error,
                duration_seconds=duration_seconds,
                status=status,
            )
        except OSError as ex:
            logger.warning("_raw_log_error failed (non-fatal): %s", ex)

    def _preflight_limit_check(self) -> None:
        """
        Run pre-flight wallet check before executing an AI request.

        Raises:
            InsufficientFundsError: When the user has exhausted their budget.
        """
        input_k_tokens_cxjcoins, output_k_tokens_cxjcoins = self._get_model_cost()
        if input_k_tokens_cxjcoins or output_k_tokens_cxjcoins:
            check_user_wallet(user=self.user)

    def _get_model_cost(self) -> tuple:
        """Return ``(input_cost, output_cost)`` for the current model."""
        input_k_tokens_cxjcoins: float = (
            getattr(self.llm_settings, "input_k_tokens_cxjcoins", 0.0) or 0.0
        )
        output_k_tokens_cxjcoins: float = (
            getattr(self.llm_settings, "output_k_tokens_cxjcoins", 0.0) or 0.0
        )
        return input_k_tokens_cxjcoins, output_k_tokens_cxjcoins

    def _record_usage(
        self,
        input_text: str,
        output_text: str,
        duration_seconds: float = 0.0,
        tags: str = "",
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        usage_info: Any = None,
        chat_id: Optional[str] = None,
    ) -> None:
        """
        Record token usage and costs to analytics.

        Args:
            input_text:       The prompt/input text sent to the model.
            output_text:      The completion/response text from the model.
            duration_seconds: Wall-clock seconds for the request-response cycle.
            tags:             Comma-separated analytics tags.
            session_id:       Session identifier for grouping requests.
            request_id:       Unique request identifier for traceability.
            usage_info:       Token counts from provider (may include
                              ``prompt_tokens``, ``completion_tokens``).
            chat_id:          Chat identifier for linking to chat sessions.
        """
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

            # Fallback to local token counter when provider values are missing
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
                chat_id=chat_id,
            )
        except OSError as ex:
            logger.warning("_record_usage failed (non-fatal): %s", ex)

    def _record_tool_usage(
        self,
        tool_name: str,
        time_taken: float,
        success: bool,
        error_message: Optional[str] = None,
        chat_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Record a tool execution event to analytics.

        Args:
            tool_name:     Name of the tool that was executed.
            time_taken:    Execution duration in seconds.
            success:       Whether the tool executed successfully.
            error_message: Error details if execution failed.
            chat_id:       Reference to the parent chat/conversation session.
            request_id:    Traceability link to the LLM request that triggered the tool.
        """
        try:
            analytics = _get_analytics()
            analytics.record_tool_usage(
                name=tool_name,
                username=self.user.username if self.user else "anonymous",
                project_name=self.settings.project_name or "",
                project_id=getattr(self.settings, "project_id", "") or "",
                time_taken=time_taken,
                success=success,
                error_message=error_message,
                chat_id=chat_id,
                request_id=request_id,
            )
        except OSError as ex:
            logger.warning("_record_tool_usage failed (non-fatal): %s", ex)

    # ── Loop-detection helper ──────────────────────────────────────────────────

    @staticmethod
    def _check_tool_call_loop(
        all_tool_calls: Dict[str, Dict[str, Any]],
        previous_fingerprints: List[str],
    ) -> Tuple[bool, str]:
        """
        Detect whether the current round of tool calls is a stuck loop.

        A loop is detected when the last ``MAX_IDENTICAL_ROUNDS`` entries in
        *previous_fingerprints* are all identical to the current round's
        fingerprint.

        Args:
            all_tool_calls:         Current round's tool calls.
            previous_fingerprints:  Ordered history of fingerprints from prior
                                    rounds (oldest first, newest last).

        Returns:
            A ``(is_loop, fingerprint)`` tuple.  *is_loop* is ``True`` when a
            stuck loop is detected.  *fingerprint* is always the fingerprint of
            the current round.
        """
        current_fingerprint = _fingerprint_tool_calls(all_tool_calls)

        if len(previous_fingerprints) >= MAX_IDENTICAL_ROUNDS:
            # Check the most-recent MAX_IDENTICAL_ROUNDS entries
            recent = previous_fingerprints[-MAX_IDENTICAL_ROUNDS:]
            if all(fp == current_fingerprint for fp in recent):
                return True, current_fingerprint

        return False, current_fingerprint

    # ── Logging helpers ────────────────────────────────────────────────────────

    def log(self, msg: str) -> None:
        """Write *msg* to the AI activity log when AI logging is enabled."""
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    # ── Message conversion ─────────────────────────────────────────────────────

    def convert_message_to_openai(
        self, gpt_message: Union[AIMessage, HumanMessage]
    ) -> Dict[str, Any]:
        """
        Convert a LangChain message object to an OpenAI message dict.

        Args:
            gpt_message: A LangChain :class:`AIMessage` or :class:`HumanMessage`.

        Returns:
            A dict with ``role`` and ``content`` keys suitable for the OpenAI API.

        Raises:
            json.JSONDecodeError: If an image message has invalid JSON content.
        """
        if gpt_message.type == "image":
            try:
                return {"content": json.loads(gpt_message.content), "role": "user"}
            except (json.JSONDecodeError, TypeError) as ex:
                self.log(f"Error converting image message '{ex}': {gpt_message}")
                raise
        return {
            "role": "assistant" if gpt_message.type == "ai" else "user",
            "content": gpt_message.content,
        }

    def preparer_messages_to_openai(
        self, messages: List[Union[AIMessage, HumanMessage]], config: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Convert a list of LangChain messages to the OpenAI messages format,
        prepending the system prompt when configured.

        When ``_openai_messages_override`` is present in config (set by recursive
        tool-call invocations), returns that pre-built message list directly to
        preserve the complete conversation history including tool-call exchanges.

        Args:
            messages: Sequence of LangChain message objects.
            config:   Optional config dict that may contain
                      ``_openai_messages_override``.

        Returns:
            List of OpenAI-compatible message dicts.
        """
        # Use override if provided (for recursive tool calls)
        if config and config.get("_openai_messages_override"):
            return config["_openai_messages_override"]

        oai_messages = [self.convert_message_to_openai(msg) for msg in messages]
        system_content = "\n".join(
            [self.llm_settings.system or "", self.system or ""]
        ).strip()
        if system_content:
            oai_messages = [{"role": "system", "content": system_content}] + oai_messages
        return oai_messages

    # ── Callback helper ────────────────────────────────────────────────────────

    @staticmethod
    def _make_callback_sender(callbacks, callback_data: Dict[str, Any]):
        """
        Return a closure that batches and flushes streamed content to callbacks.

        Chunks are buffered for up to 1 second before being flushed; calling
        with ``flush=True`` forces an immediate flush.

        Args:
            callbacks:     List of callables that accept a ``str`` chunk.
            callback_data: Mutable state dict with ``buffer`` (list) and
                           ``ts`` (datetime) keys.

        Returns:
            A ``send_callback(chunk_content, flush=False)`` function.
        """
        def send_callback(chunk_content: str, flush: bool = False) -> None:
            if not callbacks:
                return
            callback_data["buffer"].append(chunk_content or "")
            elapsed = (datetime.now() - callback_data["ts"]).total_seconds()
            if flush or elapsed > 1:
                callback_data["ts"] = datetime.now()
                message = "".join(callback_data["buffer"])
                callback_data["buffer"] = []
                for cb in callbacks:
                    try:
                        cb(message)
                    except OSError as ex:
                        logger.exception("ERROR IN CALLBACKS: %s", ex)

        return send_callback

    # ── Public: sync completion ────────────────────────────────────────────────

    @profile_function
    def chat_completions(
        self, messages: List[Union[AIMessage, HumanMessage]], config: Dict[str, Any] = None
    ) -> List[Union[AIMessage, HumanMessage]]:
        """
        Synchronous streaming chat completion (no tool support).

        Args:
            messages: Conversation history as LangChain message objects.
            config:   Optional dict with keys:
                      ``parent_request_id``, ``chat_id``, ``cancellation_token``,
                      ``headers``, ``callbacks``.

        Returns:
            Updated *messages* list with the assistant reply appended.
        """
        if config is None:
            config = {}

        self._preflight_limit_check()

        request_id: str = _new_request_id()
        parent_request_id: Optional[str] = config.get("parent_request_id", None)
        chat_id: Optional[str] = config.get("chat_id", None)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if self.llm_settings.temperature != 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(
            f"OpenAI_AI chat_completions {self.llm_settings.provider}: "
            f"{self.model} {self.base_url} {self.api_key[0:6]}..."
        )

        openai_messages = self.preparer_messages_to_openai(messages=messages, config=config)

        if self.llm_settings.merge_messages:
            merged = "\n".join(m["content"] for m in openai_messages)
            openai_messages = [{"role": "user", "content": merged}]

        self.log(f"USER REQUEST:\n{json.dumps(openai_messages, indent=2)}")

        cancellation_token: Optional[CancellationToken] = config.get(
            "cancellation_token", None
        )
        request_headers: Dict[str, str] = config.get("headers", {})
        tags_str: str = request_headers.get("tags", "")
        session_id: Optional[str] = request_headers.get("session_id", None)

        request_start = time.monotonic()
        tags_joined = ""
        usage_info = None

        try:
            tags = tags_str.split(",") + [
                f"temperature:{self.llm_settings.temperature}",
                self.settings.project_name,
            ]
            if self.user:
                tags.append(f"user:{self.user.username}")
            request_headers["x-litellm-tags"] = ",".join(tags)
            tags_joined = ",".join(tags)

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
                    extra_headers=request_headers,
                )
            except OSError as ex:
                if "stream_options" in kwargs:
                    logger.warning(
                        "Failed to create chat completion with stream_options, "
                        "retrying without: %s",
                        ex,
                    )
                    kwargs.pop("stream_options", None)
                    response_stream = self.client.chat.completions.create(
                        **kwargs,
                        messages=openai_messages,
                        extra_headers=request_headers,
                    )
                else:
                    raise

            callbacks = config.get("callbacks", None)
            callback_data = {"buffer": [], "ts": datetime.now()}
            send_callback = self._make_callback_sender(callbacks, callback_data)

            content_parts: List[str] = []
            last_finish_reason: Optional[str] = None

            for chunk in response_stream:
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    usage_info = chunk.usage

                if cancellation_token and cancellation_token.is_cancelled:
                    logger.info("chat_completions: cancellation requested, closing stream")
                    try:
                        response_stream.close()
                    except OSError:
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

        except CancelledError:
            duration_seconds = time.monotonic() - request_start
            self._raw_log_error(
                error=CancelledError("cancelled"),
                duration_seconds=duration_seconds,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
                status=STATUS_CANCELLED,
            )
            raise

        except OSError as ex:
            duration_seconds = time.monotonic() - request_start
            logger.error(
                "Error reading AI response: %s, %s, %s\n%s",
                self.base_url,
                self.api_key[0:5],
                self.llm_settings,
                ex,
            )
            self._raw_log_error(
                error=ex,
                duration_seconds=duration_seconds,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
                status=STATUS_ERROR,
            )
            raise

        duration_seconds = time.monotonic() - request_start
        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

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

        input_text = "\n".join(
            m.get("content", "") for m in openai_messages
            if isinstance(m.get("content"), str)
        )
        self._record_usage(
            input_text=input_text,
            output_text=response_content,
            duration_seconds=duration_seconds,
            tags=tags_joined,
            session_id=session_id,
            request_id=request_id,
            usage_info=usage_info,
            chat_id=chat_id,
        )

        messages.append(AIMessage(content=response_content))
        return messages

    # ── Public: async completion (with tool support) ───────────────────────────

    @profile_function
    async def a_chat_completions(
        self,
        messages: List[Union[AIMessage, HumanMessage]],
        config: Dict[str, Any] = None,
    ) -> List[Union[AIMessage, HumanMessage]]:
        """
        Async streaming chat completion with full multi-step tool support.

        Guards against two distinct failure modes:

        1. **Depth guard** — ``_tool_recursion_depth`` is incremented once per
           *round* (one LLM response that requests tools).  A single round may
           contain many parallel tool calls; those do **not** count as
           additional rounds.  The limit is ``MAX_TOOL_RECURSION_DEPTH`` (20),
           which is intentionally generous to support long reasoning chains
           (e.g. reading many files) while still providing an upper bound.

        2. **Loop guard** — a SHA-256 fingerprint of each round's
           ``(function, arguments)`` set is appended to
           ``_tool_fingerprint_history``.  If the last ``MAX_IDENTICAL_ROUNDS``
           (3) fingerprints are all identical the model is considered stuck and
           a ``RuntimeError`` is raised immediately, before any new API call is
           made.

        .. code-block:: text

            Round 0: read_file(A), read_file(B)  → fingerprint X   [ok]
            Round 1: read_file(C)                → fingerprint Y   [ok]
            Round 2: write_file(D)               → fingerprint Z   [ok]
            Round 3: search(Q)  → fingerprint W  [ok]
            ...up to 20 rounds...

            # Stuck-loop example:
            Round N:   read_file(A) → fingerprint X
            Round N+1: read_file(A) → fingerprint X
            Round N+2: read_file(A) → fingerprint X  ← loop detected ✗

        Args:
            messages: Conversation history as LangChain message objects.
            config:   Optional dict with keys:
                      ``tools``, ``parent_request_id``, ``chat_id``,
                      ``cancellation_token``, ``headers``, ``callbacks``,
                      ``_tool_recursion_depth``, ``_tool_fingerprint_history``,
                      ``_openai_messages_override``.

        Returns:
            Updated *messages* list with the final assistant reply appended.

        Raises:
            RuntimeError: If maximum tool recursion depth is exceeded.
            RuntimeError: If an infinite tool-call loop is detected.
        """
        if config is None:
            config = {}

        self._preflight_limit_check()

        # ── Depth guard ────────────────────────────────────────────────────────
        # Each *round* (one LLM response requesting tools) increments depth by 1.
        # Multiple parallel tool calls within a single round count as ONE depth
        # increment, not N.
        tool_recursion_depth: int = config.get("_tool_recursion_depth", 0)
        if tool_recursion_depth > MAX_TOOL_RECURSION_DEPTH:
            logger.error(
                "a_chat_completions: maximum tool recursion depth (%d) exceeded "
                "after %d rounds",
                MAX_TOOL_RECURSION_DEPTH,
                tool_recursion_depth,
            )
            raise RuntimeError(
                TOOL_RECURSION_ERROR_MSG.format(depth=MAX_TOOL_RECURSION_DEPTH)
            )

        # Fingerprint history is a list of hashes, one per completed tool-call
        # round. It is passed down through config so it accumulates across all
        # recursive invocations of this method.
        tool_fingerprint_history: List[str] = list(
            config.get("_tool_fingerprint_history", [])
        )

        request_id: str = _new_request_id()
        parent_request_id: Optional[str] = config.get("parent_request_id", None)
        chat_id: Optional[str] = config.get("chat_id", None)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        # ── Tool injection ─────────────────────────────────────────────────────
        selected_tools: List[str] = config.get("tools", [])
        chat_tools = [
            t["tool_json"]
            for t in self.tools
            if t["tool_json"]["function"]["name"] in selected_tools
        ]
        if chat_tools:
            kwargs["tools"] = chat_tools
            logger.debug(
                "a_chat_completions: injecting %d tool(s): %s",
                len(chat_tools),
                [t["function"]["name"] for t in chat_tools],
            )

        if self.llm_settings.temperature != 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)

        self.log(
            f"OpenAI_AI a_chat_completions {self.llm_settings.provider}: "
            f"{self.model} {self.base_url} {self.api_key[0:6]}..."
        )

        openai_messages = self.preparer_messages_to_openai(messages=messages, config=config)

        if self.llm_settings.merge_messages:
            merged = "\n".join(m["content"] for m in openai_messages)
            openai_messages = [{"role": "user", "content": merged}]

        cancellation_token: Optional[CancellationToken] = config.get(
            "cancellation_token", None
        )
        request_headers: Dict[str, str] = config.get("headers", {})
        tags_str: str = request_headers.get("tags", "")
        session_id: Optional[str] = request_headers.get("session_id", None)

        request_start = time.monotonic()
        tags_joined = ""
        usage_info = None

        try:
            tags = tags_str.split(",") + [
                f"temperature:{self.llm_settings.temperature}",
                self.settings.project_name,
            ]
            if self.user:
                tags.append(f"user:{self.user.username}")
            request_headers["x-litellm-tags"] = ",".join(tags)
            tags_joined = ",".join(tags)

            request_params: Dict[str, Any] = {
                **kwargs,
                "messages": openai_messages,
                "extra_headers": request_headers,
            }
            self.log(f"USER REQUEST:\n{json.dumps(request_params, indent=2)}")

            self._raw_log_request(
                openai_messages=openai_messages,
                kwargs=kwargs,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
            )

            try:
                response_stream = self.client.chat.completions.create(**request_params)
            except OSError as ex:
                if "stream_options" in request_params:
                    logger.warning(
                        "Failed to create async chat completion with stream_options, "
                        "retrying without: %s",
                        ex,
                    )
                    request_params.pop("stream_options", None)
                    kwargs.pop("stream_options", None)
                    response_stream = self.client.chat.completions.create(**request_params)
                else:
                    raise

            callbacks = config.get("callbacks", None)
            callback_data = {"buffer": [], "ts": datetime.now()}
            send_callback = self._make_callback_sender(callbacks, callback_data)

            content_parts: List[str] = []
            last_finish_reason: Optional[str] = None

            # Accumulate streaming tool-call fragments keyed by tool_call_id
            all_tool_calls: Dict[str, Dict[str, Any]] = {}
            last_tool_id: Optional[str] = None

            if self.settings.get_log_ai():
                self.log(
                    f"\nReceived AI response, start reading stream "
                    f"(recursion depth: {tool_recursion_depth})\n{self.llm_settings}"
                )

            for chunk in response_stream:
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    usage_info = chunk.usage

                if cancellation_token and cancellation_token.is_cancelled:
                    logger.info(
                        "a_chat_completions: cancellation requested, closing stream"
                    )
                    try:
                        response_stream.close()
                    except OSError:
                        pass
                    send_callback("", flush=True)
                    raise CancelledError(
                        "Async chat completion was cancelled by the caller."
                    )

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                if choice.finish_reason:
                    last_finish_reason = choice.finish_reason

                # ── Accumulate tool-call fragments ─────────────────────────────
                tool_calls_delta = (
                    choice.delta.tool_calls
                    if hasattr(choice.delta, "tool_calls")
                    else None
                )
                if tool_calls_delta:
                    self._accumulate_tool_call_delta(
                        tool_calls_delta, all_tool_calls, last_tool_id
                    )
                    # Update last_tool_id if a new tool was started
                    for tc_delta in tool_calls_delta:
                        if tc_delta.id:
                            last_tool_id = tc_delta.id

                # ── Handle tool_calls finish ───────────────────────────────────
                if choice.finish_reason == "tool_calls":
                    duration_so_far = time.monotonic() - request_start
                    partial_content = "".join(content_parts)

                    logger.info(
                        "a_chat_completions: tool_calls finish detected "
                        "(round/depth: %d, parallel tools in this round: %d)",
                        tool_recursion_depth,
                        len(all_tool_calls),
                    )

                    # ── Loop guard ─────────────────────────────────────────────
                    # Check *before* executing tools so we don't waste resources
                    # running tools we know will loop.
                    is_loop, current_fingerprint = self._check_tool_call_loop(
                        all_tool_calls, tool_fingerprint_history
                    )
                    if is_loop:
                        loop_error_msg = TOOL_LOOP_DETECTED_MSG.format(
                            count=MAX_IDENTICAL_ROUNDS
                        )
                        logger.error(
                            "a_chat_completions: %s (fingerprint=%s, depth=%d)",
                            loop_error_msg,
                            current_fingerprint[:12],
                            tool_recursion_depth,
                        )
                        raise RuntimeError(loop_error_msg)

                    # Record this round's fingerprint in the history
                    tool_fingerprint_history.append(current_fingerprint)
                    logger.debug(
                        "a_chat_completions: round %d fingerprint=%s "
                        "(history length=%d)",
                        tool_recursion_depth,
                        current_fingerprint[:12],
                        len(tool_fingerprint_history),
                    )

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

                    # 1. Append assistant message that contains tool_calls array
                    #    (required by the OpenAI API to maintain valid history)
                    assistant_msg = _make_assistant_tool_calls_message(
                        all_tool_calls, content=partial_content
                    )
                    openai_messages.append(assistant_msg)
                    logger.info(
                        "a_chat_completions: executing %d tool(s) in parallel "
                        "(round %d)",
                        len(all_tool_calls),
                        tool_recursion_depth,
                    )

                    # 2. Execute each tool and collect role=tool messages
                    tool_result_messages: List[Dict[str, Any]] = []
                    for tc in all_tool_calls.values():
                        func_name = tc["function"]
                        try:
                            tool_output = await self.process_tool_calls(
                                tool_call_data=tc,
                                request_id=request_id,
                                chat_id=chat_id,
                            )
                            result_content = (
                                tool_output["output"]
                                if isinstance(tool_output, dict) and "output" in tool_output
                                else tool_output
                            )
                            logger.info(
                                "Tool '%s' returned successfully (call_id=%s)",
                                func_name,
                                tc["id"],
                            )
                        except (OSError, ValueError, RuntimeError) as ex:
                            logger.exception(
                                "Error executing tool '%s': %s", func_name, ex
                            )
                            result_content = f"Error executing tool '{func_name}': {ex}"

                        tool_result_messages.append(
                            _make_tool_message(
                                tool_call_id=tc["id"],
                                content=result_content
                                if isinstance(result_content, str)
                                else json.dumps(result_content),
                            )
                        )

                    # 3. Append all tool result messages to the raw OpenAI message list
                    openai_messages.extend(tool_result_messages)

                    # 4. Recurse asynchronously with updated depth and fingerprint
                    #    history.  Both guards are propagated so they accumulate
                    #    across the full conversation.
                    child_config = {
                        **config,
                        "parent_request_id": request_id,
                        "chat_id": chat_id,
                        "_openai_messages_override": openai_messages,
                        "_tool_recursion_depth": tool_recursion_depth + 1,
                        "_tool_fingerprint_history": tool_fingerprint_history,
                    }
                    logger.debug(
                        "a_chat_completions: recursing — new depth=%d, "
                        "fingerprint history length=%d",
                        tool_recursion_depth + 1,
                        len(tool_fingerprint_history),
                    )
                    return await self.a_chat_completions(
                        messages=messages, config=child_config
                    )

                # ── Regular content chunk ──────────────────────────────────────
                chunk_content = choice.delta.content
                if not chunk_content:
                    continue

                chunk_content_cleaned = clean_string(chunk_content)
                content_parts.append(chunk_content_cleaned)
                send_callback(chunk_content)

            send_callback("", flush=True)

        except CancelledError:
            duration_seconds = time.monotonic() - request_start
            self._raw_log_error(
                error=CancelledError("cancelled"),
                duration_seconds=duration_seconds,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
                status=STATUS_CANCELLED,
            )
            raise

        except OSError as ex:
            duration_seconds = time.monotonic() - request_start
            logger.error(
                "Error reading AI response: %s, %s, %s\n%s",
                self.base_url,
                self.api_key[0:5],
                self.llm_settings,
                ex,
            )
            self._raw_log_error(
                error=ex,
                duration_seconds=duration_seconds,
                request_id=request_id,
                session_id=session_id,
                tags=tags_joined,
                parent_request_id=parent_request_id,
                status=STATUS_ERROR,
            )
            raise

        duration_seconds = time.monotonic() - request_start
        response_content = "".join(content_parts)
        self.log(f"AI RESPONSE:\n{response_content}")

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

        input_text = "\n".join(
            m.get("content", "") for m in openai_messages
            if isinstance(m.get("content"), str)
        )
        self._record_usage(
            input_text=input_text,
            output_text=response_content,
            duration_seconds=duration_seconds,
            tags=tags_joined,
            session_id=session_id,
            request_id=request_id,
            usage_info=usage_info,
            chat_id=chat_id,
        )

        messages.append(AIMessage(content=response_content))
        return messages

    # ── Tool-call helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _accumulate_tool_call_delta(
        tool_calls_delta: List[Any],
        all_tool_calls: Dict[str, Dict[str, Any]],
        last_tool_id: Optional[str],
    ) -> None:
        """
        Merge a list of streaming tool-call delta objects into *all_tool_calls*.

        The OpenAI streaming API sends tool call data fragmented across many
        chunks.  The first chunk for a given tool provides the ``id`` and
        ``function.name``; subsequent chunks provide more ``function.arguments``
        characters.  This method stitches those fragments together.

        Args:
            tool_calls_delta: List of delta tool-call objects from the chunk.
            all_tool_calls:   Mutable accumulator dict (tool_call_id → data).
            last_tool_id:     The most-recently-seen tool_call_id (may be None).
        """
        for tc_delta in tool_calls_delta:
            # A new tool_call_id signals the start of a new tool invocation
            if tc_delta.id and tc_delta.id not in all_tool_calls:
                all_tool_calls[tc_delta.id] = {
                    "id": tc_delta.id,
                    "function": "",
                    "arguments": "",
                }

            # Determine which tool entry to update
            active_id = tc_delta.id if tc_delta.id else last_tool_id
            if not active_id or active_id not in all_tool_calls:
                logger.warning(
                    "_accumulate_tool_call_delta: cannot resolve active tool id, "
                    "skipping delta"
                )
                continue

            if tc_delta.function and tc_delta.function.name:
                all_tool_calls[active_id]["function"] += tc_delta.function.name
            if tc_delta.function and tc_delta.function.arguments:
                all_tool_calls[active_id]["arguments"] += tc_delta.function.arguments

    @profile_function
    async def process_tool_calls(
        self,
        tool_call_data: Dict[str, Any],
        request_id: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single tool call and return its output.

        Looks up the tool by ``function`` name, injects ``settings`` when the
        tool requires project context, executes the callable (awaiting it when
        declared as async), and records the result to analytics.

        Args:
            tool_call_data: Dict with keys ``id``, ``function``, ``arguments``.
            request_id:     Traceability link to the LLM request that triggered
                            this tool.
            chat_id:        Chat/session identifier for analytics.

        Returns:
            Dict with keys ``type``, ``call_id``, ``output``.
        """
        self.log(f"process_tool_calls: {tool_call_data}")

        func_name: str = tool_call_data["function"]
        raw_arguments = tool_call_data.get("arguments", "{}")

        # Parse arguments — may arrive as a JSON string or already as a dict
        if isinstance(raw_arguments, str):
            try:
                params: Dict[str, Any] = json.loads(raw_arguments)
            except json.JSONDecodeError as ex:
                logger.error(
                    "process_tool_calls: cannot parse arguments for tool '%s': %s",
                    func_name,
                    ex,
                )
                params = {}
        elif isinstance(raw_arguments, dict):
            params = raw_arguments
        else:
            params = {}

        tool = next(
            (t for t in self.tools if t["tool_json"]["function"]["name"] == func_name),
            None,
        )

        success = True
        error_message: Optional[str] = None
        tool_response: Any = None
        tool_start = time.monotonic()

        try:
            if tool is None:
                success = False
                error_message = f"Tool '{func_name}' not found"
                tool_response = error_message
                logger.warning("process_tool_calls: %s", error_message)
            else:
                tool_settings: Dict[str, Any] = tool.get(
                    "settings",
                    {"project_settings": False, "async": False},
                )
                if tool_settings.get("project_settings"):
                    params["settings"] = self.settings

                logger.info(
                    "process_tool_calls: executing tool '%s' with params %s",
                    func_name,
                    list(params.keys()),
                )
                result = tool["tool_call"](**params)
                if tool_settings.get("async"):
                    result = await result
                tool_response = result

        except Exception as ex:
            success = False
            error_message = str(ex)
            tool_response = f"Error executing tool '{func_name}': {ex}"
            logger.exception(
                "Exception in process_tool_calls for tool '%s'", func_name
            )

        finally:
            time_taken = time.monotonic() - tool_start
            self._record_tool_usage(
                tool_name=func_name,
                time_taken=time_taken,
                success=success,
                error_message=error_message,
                chat_id=chat_id,
                request_id=request_id,
            )

        return {
            "type": "function_call_output",
            "call_id": tool_call_data.get("id", ""),
            "output": tool_response,
        }

    # ── Image generation ───────────────────────────────────────────────────────

    @profile_function
    def generate_image(self, prompt: str) -> str:
        """
        Generate an image using DALL-E 3 and return its URL.

        Args:
            prompt: Text description of the image to generate.

        Returns:
            URL string of the generated image.
        """
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url

    # ── Embeddings ─────────────────────────────────────────────────────────────

    @profile_function
    def embeddings(self):
        """
        Return a callable that computes embeddings for a given text string.

        The callable uses the embeddings model configured in settings and
        concatenates all embedding vectors returned by the provider.

        Returns:
            A function ``embedding_func(content: str) -> list[float]``.
        """
        embeddings_ai_settings = self.settings.get_embeddings_settings()
        client = OpenAI(
            api_key=embeddings_ai_settings.api_key,
            base_url=embeddings_ai_settings.api_url,
        )

        def embedding_func(content: str) -> List[float]:
            """Compute and return a flat embedding vector for *content*."""
            try:
                response = client.embeddings.create(
                    input=content,
                    model=embeddings_ai_settings.model,
                )
                embeddings: List[float] = []
                for data in response.data:
                    embeddings += data.embedding
                return embeddings
            except OSError as ex:
                logger.error(
                    "Error creating embeddings %s %s: %s",
                    self.settings.project_name,
                    embeddings_ai_settings,
                    ex,
                )
                raise

        return embedding_func


# Made with ❤️ by codx-junior