"""
SmolAgent — a small, async-only OpenAI chat agent.

Compared to :class:`codx.junior.ai.openai_ai.OpenAI_AI`, this implementation:
    * exposes a single async ``chat()`` method (no sync variant),
    * uses an **iterative** tool loop instead of recursion,
    * delegates loop protection to :class:`LoopGuard`,
    * delegates logging, event emission and cancellation to
      :class:`engine.agent_runtime.AgentRunContext`,
    * keeps streaming, callbacks, cancellation and analytics.
"""
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from openai import OpenAI
from langchain.messages import AIMessage, HumanMessage

from engine.agent_runtime import (
    AgentCancelled,
    AgentEventType,
    AgentRunContext,
)

from codx.junior.ai.cancellation import CancellationToken, CancelledError
from codx.junior.ai.wallet_check import check_user_wallet
from codx.junior.ai.smol.constants import CALLBACK_FLUSH_SECONDS
from codx.junior.ai.smol.loop_guard import LoopGuard
from codx.junior.ai.smol.messages import (
    ToolCallAccumulator,
    make_assistant_tool_calls_message,
    make_tool_message,
    to_openai_messages,
)
from codx.junior.analytics import Analytics
from codx.junior.analytics.token_counter import count_tokens
from codx.junior.model.model import CodxUser
from codx.junior.settings import CODXJuniorSettings
from codx.junior.utils.utils import clean_string

logger = logging.getLogger(__name__)

# Module-level analytics singleton
_analytics_instance: Optional[Analytics] = None

# Message used whenever the run is cancelled by the caller.
CANCELLED_MESSAGE: str = "Chat was cancelled by the caller."


def _get_analytics() -> Analytics:
    """Return (creating if necessary) the module-level Analytics singleton."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = Analytics()
    return _analytics_instance


class SmolAgent:
    """
    Async-only streaming chat agent with multi-step tool support.

    All logging, event fan-out, cancellation checkpoints and per-run
    analytics are delegated to :class:`AgentRunContext` (the unified
    agent runtime). Callers may pass their own context through
    ``config["run_context"]`` (e.g. to share a Socket.IO listener or a
    cancellation token) or plain listeners via ``config["event_listeners"]``.

    Conversation flow
    -----------------
    .. code-block:: mermaid

        flowchart TD
            A[chat] --> B[Resolve AgentRunContext]
            B --> C[run_context.run - RUN_START]
            C --> D[Build OpenAI messages]
            D --> E[Stream completion via guard_stream]
            E --> F{finish_reason?}
            F -->|tool_calls| G[LoopGuard.check]
            G -->|ok| H[Execute tools - TOOL_START/END/ERROR]
            H --> I[Append assistant + tool messages]
            I --> E
            G -->|stuck| J[Raise ToolLoopError - RUN_ERROR]
            F -->|stop / length| K[Record usage - RUN_END]
            E -->|cancelled| L[RUN_CANCELLED - raise CancelledError]
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        llm_model: Optional[str] = None,
        user: Optional[CodxUser] = None,
        system: Optional[str] = None,
    ) -> None:
        """
        Args:
            settings:  Project settings providing LLM configuration.
            llm_model: Optional model override.
            user:      Optional user (used for API key and analytics).
            system:    Optional extra system prompt content.
        """
        from codx.junior.tools import TOOLS
        self.tools: List[Dict[str, Any]] = TOOLS

        self.settings = settings
        self.llm_settings = settings.get_llm_settings(llm_model=llm_model)
        self.model: str = self.llm_settings.model
        self.user = user
        self.api_key: str = (
            user.api_key if user and user.api_key else self.llm_settings.api_key
        )
        self.base_url: str = self.llm_settings.api_url
        self.system: str = "\n".join(
            [self.llm_settings.system or "", system or ""]
        ).strip()

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(
            "SmolAgent created. USER: %s, MODEL: %s, URL: %s",
            user.username if user else "NONE",
            self.model,
            self.base_url,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def chat(
        self,
        messages: List[Union[AIMessage, HumanMessage]],
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Union[AIMessage, HumanMessage]]:
        """
        Run a streaming chat completion with iterative multi-step tool support.

        The whole run is wrapped in :meth:`AgentRunContext.run`, which emits
        ``RUN_START`` / ``RUN_END`` / ``RUN_ERROR`` / ``RUN_CANCELLED`` events
        with an analytics summary attached.

        Args:
            messages: Conversation history as LangChain message objects.
            config:   Optional dict with keys: ``tools``, ``chat_id``,
                      ``cancellation_token``, ``headers``, ``callbacks``,
                      ``run_context`` (an :class:`AgentRunContext`) and
                      ``event_listeners`` (list of event callables).

        Returns:
            Updated *messages* list with the assistant reply appended.

        Raises:
            ToolLoopError:  If max tool rounds or a stuck loop is detected.
            CancelledError: If the request is cancelled by the caller.
        """
        config = config or {}
        self._preflight_limit_check()

        run_context = self._resolve_run_context(config)
        result: Optional[List[Union[AIMessage, HumanMessage]]] = None

        # run_context.run() emits RUN_* lifecycle events. It swallows
        # AgentCancelled (emitting RUN_CANCELLED), so we translate the
        # cancelled state back to the legacy CancelledError afterwards.
        with run_context.run():
            result = await self._run_chat_loop(messages, config, run_context)

        if run_context.token.cancelled or result is None:
            raise CancelledError(CANCELLED_MESSAGE)
        return result

    # ── Chat loop ──────────────────────────────────────────────────────────────

    async def _run_chat_loop(
        self,
        messages: List[Union[AIMessage, HumanMessage]],
        config: Dict[str, Any],
        run_context: AgentRunContext,
    ) -> List[Union[AIMessage, HumanMessage]]:
        """
        Execute the iterative streaming/tool loop for one conversation.

        Args:
            messages:    Conversation history as LangChain message objects.
            config:      Chat configuration dict (see :meth:`chat`).
            run_context: Unified runtime context for this run.

        Returns:
            Updated *messages* list with the assistant reply appended.

        Raises:
            ToolLoopError:  If max tool rounds or a stuck loop is detected.
            AgentCancelled: If cancellation is requested mid-run.
        """
        chat_id: Optional[str] = config.get("chat_id")
        cancellation_token: Optional[CancellationToken] = config.get("cancellation_token")
        headers: Dict[str, str] = config.get("headers", {})
        session_id: Optional[str] = headers.get("session_id")
        tags: str = self._build_tags(headers)
        headers["x-litellm-tags"] = tags

        send_callback = self._make_callback_sender(config.get("callbacks"))
        kwargs = self._build_request_kwargs(config.get("tools", []))
        openai_messages = to_openai_messages(messages, system=self.system)

        loop_guard = LoopGuard()
        request_start = time.monotonic()

        # Iterative tool loop: keep streaming completions until the model
        # produces a final answer (no more tool_calls finish reason).
        while True:
            request_id = str(uuid.uuid4())
            content, tool_calls, usage_info = await self._stream_completion(
                kwargs=kwargs,
                openai_messages=openai_messages,
                headers=headers,
                cancellation_token=cancellation_token,
                send_callback=send_callback,
                run_context=run_context,
            )

            if not tool_calls:
                break

            # Guard against loops BEFORE executing any tool.
            loop_guard.check(tool_calls)

            logger.info(
                "SmolAgent: round %d — executing %d tool(s)",
                loop_guard.rounds,
                len(tool_calls),
            )
            openai_messages.append(
                make_assistant_tool_calls_message(tool_calls, content=content)
            )
            for tool_call in tool_calls.values():
                result = await self._execute_tool(
                    tool_call,
                    request_id=request_id,
                    chat_id=chat_id,
                    run_context=run_context,
                )
                openai_messages.append(
                    make_tool_message(tool_call_id=tool_call["id"], content=result)
                )

        duration_seconds = time.monotonic() - request_start
        self._record_usage(
            openai_messages=openai_messages,
            output_text=content,
            duration_seconds=duration_seconds,
            tags=tags,
            session_id=session_id,
            request_id=request_id,
            usage_info=usage_info,
            chat_id=chat_id,
        )

        messages.append(AIMessage(content=content))
        return messages

    # ── Runtime context ────────────────────────────────────────────────────────

    def _resolve_run_context(self, config: Dict[str, Any]) -> AgentRunContext:
        """
        Return the run context to use for this chat.

        Reuses ``config["run_context"]`` when provided (allowing callers to
        share cancellation tokens and event listeners); otherwise creates a
        fresh :class:`AgentRunContext` with optional ``event_listeners``.

        Args:
            config: Chat configuration dict.

        Returns:
            The :class:`AgentRunContext` for this run.
        """
        run_context: Optional[AgentRunContext] = config.get("run_context")
        if run_context is None:
            run_context = AgentRunContext(
                project_id=getattr(self.settings, "project_id", "") or "",
                listeners=config.get("event_listeners"),
            )
        return run_context

    # ── Streaming ──────────────────────────────────────────────────────────────

    async def _stream_completion(
        self,
        kwargs: Dict[str, Any],
        openai_messages: List[Dict[str, Any]],
        headers: Dict[str, str],
        cancellation_token: Optional[CancellationToken],
        send_callback: Callable[[str, bool], None],
        run_context: AgentRunContext,
    ) -> Tuple[str, Dict[str, Dict[str, Any]], Any]:
        """
        Stream one completion, collecting content, tool calls and usage.

        The stream is wrapped by :meth:`AgentRunContext.guard_stream`, which
        checks cancellation on every chunk and emits throttled ``LLM_CHUNK``
        events for live UI progress. Provider usage is emitted as
        ``LLM_USAGE`` so run analytics aggregate tokens automatically.

        Args:
            kwargs:             Base OpenAI request kwargs.
            openai_messages:    Current OpenAI-format conversation history.
            headers:            Extra request headers.
            cancellation_token: Optional legacy cancellation token (bridged
                                onto the run context token).
            send_callback:      Chunk callback sender.
            run_context:        Unified runtime context for this run.

        Returns:
            Tuple of ``(content, tool_calls, usage_info)``.

        Raises:
            AgentCancelled: If cancellation is requested mid-stream.
        """
        run_context.emit(
            AgentEventType.LLM_REQUEST,
            model=self.model,
            message_count=len(openai_messages),
        )
        response_stream = self.client.chat.completions.create(
            **kwargs,
            messages=openai_messages,
            extra_headers=headers,
        )

        content_parts: List[str] = []
        accumulator = ToolCallAccumulator()
        usage_info: Any = None

        try:
            for chunk in run_context.guard_stream(response_stream):
                # Bridge the legacy token onto the runtime token so both
                # cancellation paths converge on AgentCancelled.
                if cancellation_token and cancellation_token.is_cancelled:
                    run_context.cancel("user_requested")
                    run_context.checkpoint()

                if getattr(chunk, "usage", None) is not None:
                    usage_info = chunk.usage
                    run_context.emit(
                        AgentEventType.LLM_USAGE,
                        prompt_tokens=getattr(usage_info, "prompt_tokens", 0) or 0,
                        completion_tokens=getattr(
                            usage_info, "completion_tokens", 0
                        ) or 0,
                    )

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                if getattr(choice.delta, "tool_calls", None):
                    accumulator.add(choice.delta.tool_calls)
                if choice.delta.content:
                    cleaned = clean_string(choice.delta.content)
                    content_parts.append(cleaned)
                    send_callback(cleaned, False)
        except AgentCancelled:
            logger.info(
                "SmolAgent: cancellation requested, closing stream (run=%s)",
                run_context.run_id,
            )
            try:
                response_stream.close()
            except OSError:
                pass
            send_callback("", True)
            raise

        send_callback("", True)
        return "".join(content_parts), accumulator.tool_calls, usage_info

    # ── Tool execution ─────────────────────────────────────────────────────────

    async def _execute_tool(
        self,
        tool_call: Dict[str, Any],
        run_context: AgentRunContext,
        request_id: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> str:
        """
        Execute a single tool call and return its serialised output.

        Emits ``TOOL_START`` / ``TOOL_END`` / ``TOOL_ERROR`` events on the
        run context. Errors never propagate to the caller: they are returned
        as strings so the model can react to failed tool invocations (hence
        events are emitted manually instead of using ``run_context.tool``,
        which re-raises).

        Args:
            tool_call:   Dict with keys ``id``, ``function``, ``arguments``.
            run_context: Unified runtime context for this run.
            request_id:  Traceability link to the triggering LLM request.
            chat_id:     Chat identifier for analytics.

        Returns:
            The tool result as a string.

        Raises:
            AgentCancelled: If cancellation was requested before execution.
        """
        # Safe abort point before spending time on a tool.
        run_context.checkpoint()

        func_name: str = tool_call["function"]
        params = self._parse_tool_arguments(tool_call.get("arguments", "{}"), func_name)
        tool = next(
            (t for t in self.tools if t["tool_json"]["function"]["name"] == func_name),
            None,
        )

        success = True
        error_message: Optional[str] = None
        tool_start = time.monotonic()
        run_context.emit(
            AgentEventType.TOOL_START, tool=func_name, args=list(params.keys())
        )

        try:
            if tool is None:
                success = False
                error_message = f"Tool '{func_name}' not found"
                logger.warning("SmolAgent: %s", error_message)
                return error_message

            tool_settings: Dict[str, Any] = tool.get(
                "settings", {"project_settings": False, "async": False}
            )
            if tool_settings.get("project_settings"):
                params["settings"] = self.settings

            logger.info(
                "SmolAgent: executing tool '%s' with params %s",
                func_name,
                list(params.keys()),
            )
            result = tool["tool_call"](**params)
            if tool_settings.get("async"):
                result = await result
            return result if isinstance(result, str) else json.dumps(result)

        except (OSError, ValueError, TypeError, RuntimeError) as ex:
            success = False
            error_message = str(ex)
            logger.exception("SmolAgent: error executing tool '%s'", func_name)
            return f"Error executing tool '{func_name}': {ex}"

        finally:
            duration_ms = (time.monotonic() - tool_start) * 1000
            if success:
                run_context.emit(
                    AgentEventType.TOOL_END, tool=func_name, duration_ms=duration_ms
                )
            else:
                run_context.emit(
                    AgentEventType.TOOL_ERROR,
                    tool=func_name,
                    duration_ms=duration_ms,
                    error=error_message,
                )
            self._record_tool_usage(
                tool_name=func_name,
                time_taken=time.monotonic() - tool_start,
                success=success,
                error_message=error_message,
                chat_id=chat_id,
                request_id=request_id,
            )

    @staticmethod
    def _parse_tool_arguments(raw_arguments: Any, func_name: str) -> Dict[str, Any]:
        """
        Parse tool arguments that may arrive as a JSON string or a dict.

        Args:
            raw_arguments: The raw arguments payload.
            func_name:     Tool name (for logging).

        Returns:
            A dict of parsed arguments (empty on parse failure).
        """
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if isinstance(raw_arguments, str):
            try:
                return json.loads(raw_arguments)
            except json.JSONDecodeError as ex:
                logger.error(
                    "SmolAgent: cannot parse arguments for tool '%s': %s", func_name, ex
                )
        return {}

    # ── Request building helpers ───────────────────────────────────────────────

    def _build_request_kwargs(self, selected_tools: List[str]) -> Dict[str, Any]:
        """
        Build the base kwargs for the OpenAI completion request.

        Args:
            selected_tools: Names of tools enabled for this conversation.

        Returns:
            Dict of request kwargs (model, stream, tools, temperature).
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        chat_tools = [
            t["tool_json"]
            for t in self.tools
            if t["tool_json"]["function"]["name"] in selected_tools
        ]
        if chat_tools:
            kwargs["tools"] = chat_tools
        if self.llm_settings.temperature != 0:
            kwargs["temperature"] = float(self.llm_settings.temperature)
        return kwargs

    def _build_tags(self, headers: Dict[str, str]) -> str:
        """
        Build the comma-separated analytics tag string.

        Args:
            headers: Request headers possibly containing a ``tags`` entry.

        Returns:
            Comma-joined tag string.
        """
        tags = headers.get("tags", "").split(",") + [
            f"temperature:{self.llm_settings.temperature}",
            self.settings.project_name or "",
        ]
        if self.user:
            tags.append(f"user:{self.user.username}")
        return ",".join(tag for tag in tags if tag)

    @staticmethod
    def _make_callback_sender(
        callbacks: Optional[List[Callable[[str], None]]],
    ) -> Callable[[str, bool], None]:
        """
        Return a closure that batches and flushes streamed chunks to callbacks.

        Args:
            callbacks: Callables accepting a str chunk (may be ``None``).

        Returns:
            A ``send_callback(chunk, flush)`` function.
        """
        state: Dict[str, Any] = {"buffer": [], "ts": datetime.now()}

        def send_callback(chunk_content: str, flush: bool = False) -> None:
            """Buffer *chunk_content*; flush to callbacks periodically."""
            if not callbacks:
                return
            state["buffer"].append(chunk_content or "")
            elapsed = (datetime.now() - state["ts"]).total_seconds()
            if flush or elapsed > CALLBACK_FLUSH_SECONDS:
                state["ts"] = datetime.now()
                message = "".join(state["buffer"])
                state["buffer"] = []
                for callback in callbacks:
                    try:
                        callback(message)
                    except OSError as ex:
                        logger.exception("SmolAgent: error in callback: %s", ex)

        return send_callback

    # ── Analytics ──────────────────────────────────────────────────────────────

    def _preflight_limit_check(self) -> None:
        """
        Run the pre-flight wallet check before executing an AI request.

        Raises:
            InsufficientFundsError: When the user has exhausted their budget.
        """
        input_cost = getattr(self.llm_settings, "input_k_tokens_cxjcoins", 0.0) or 0.0
        output_cost = getattr(self.llm_settings, "output_k_tokens_cxjcoins", 0.0) or 0.0
        if input_cost or output_cost:
            check_user_wallet(user=self.user)

    def _record_usage(
        self,
        openai_messages: List[Dict[str, Any]],
        output_text: str,
        duration_seconds: float,
        tags: str,
        session_id: Optional[str],
        request_id: Optional[str],
        usage_info: Any,
        chat_id: Optional[str],
    ) -> None:
        """
        Record token usage to analytics (non-fatal on error).

        Args:
            openai_messages:  Full conversation sent to the model.
            output_text:      Final assistant response text.
            duration_seconds: Total wall-clock duration.
            tags:             Analytics tag string.
            session_id:       Session identifier.
            request_id:       Last request identifier.
            usage_info:       Provider-reported token usage (may be ``None``).
            chat_id:          Chat identifier.
        """
        try:
            input_tokens = getattr(usage_info, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage_info, "completion_tokens", 0) or 0
            tokens_from_provider = bool(input_tokens)

            if not input_tokens:
                input_text = "\n".join(
                    m.get("content", "")
                    for m in openai_messages
                    if isinstance(m.get("content"), str)
                )
                input_tokens = count_tokens(input_text, model=self.model)
            if not output_tokens:
                output_tokens = count_tokens(output_text, model=self.model)

            _get_analytics().record_token_usage(
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
                input_k_tokens_cxjcoins=getattr(
                    self.llm_settings, "input_k_tokens_cxjcoins", 0.0
                ) or 0.0,
                output_k_tokens_cxjcoins=getattr(
                    self.llm_settings, "output_k_tokens_cxjcoins", 0.0
                ) or 0.0,
                request_id=request_id,
                tokens_from_provider=tokens_from_provider,
                chat_id=chat_id,
            )
        except OSError as ex:
            logger.warning("SmolAgent: _record_usage failed (non-fatal): %s", ex)

    def _record_tool_usage(
        self,
        tool_name: str,
        time_taken: float,
        success: bool,
        error_message: Optional[str],
        chat_id: Optional[str],
        request_id: Optional[str],
    ) -> None:
        """
        Record a tool execution event to analytics (non-fatal on error).

        Args:
            tool_name:     Name of the executed tool.
            time_taken:    Execution duration in seconds.
            success:       Whether the tool executed successfully.
            error_message: Error details when execution failed.
            chat_id:       Parent chat identifier.
            request_id:    Triggering LLM request identifier.
        """
        try:
            _get_analytics().record_tool_usage(
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
            logger.warning("SmolAgent: _record_tool_usage failed (non-fatal): %s", ex)

# Made with ❤️ by codx-junior