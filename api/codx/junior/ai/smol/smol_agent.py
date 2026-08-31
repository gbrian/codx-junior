"""
SmolAgent: a small, async-only OpenAI chat agent.

Compared to :class:`codx.junior.ai.openai_ai.OpenAI_AI`, this implementation:
    * exposes a single async ``chat()`` method (no sync variant),
    * uses an **iterative** tool loop instead of recursion,
    * delegates loop protection to :class:`LoopGuard`,
    * delegates logging, event emission and cancellation to
      :class:`engine.agent_runtime.AgentRunContext`,
    * keeps streaming, callbacks, cancellation and analytics.

Tool events (``TOOL_START`` / ``TOOL_END`` / ``TOOL_ERROR``) carry the
``tool_call_id``, the parsed JSON request args and a truncated result preview
so listeners (e.g. the ChatEventBridge) can surface tool executions as chat
messages in real time.

CHANGED: accumulated streaming callbacks:
    Streaming callbacks now receive the FULL response accumulated so far on
    every flush (not just the delta since the last flush). Downstream
    consumers assign the callback payload directly to the response message
    content and may persist it mid-stream (crash-safety), so sending only
    deltas caused partial persists to contain just the last fragment of the
    response. Accumulation guarantees no information is lost mid-run.

CHANGED: tool scope support:
    Tools can now be classified by scope (global, chat, profile). Global scope
    tools are always included in conversations, while chat scope tools are
    selectively included based on the request configuration.

CHANGED: dual-response tools:
    Tools can now return a ToolResponse object with both user-facing content
    (displayed to the user) and lightweight LLM feedback (for model context).
    This allows tools like code_block_generator to generate formatted output
    while keeping the LLM loop lightweight.

CHANGED: global chat instructions:
    chat_global_instructions are loaded from GlobalSettings on every chat
    (not cached) and prepended to the system message. Extra system instructions
    passed to SmolAgent are appended after the global instructions.

CHANGED: session context injection:
    SmolAgent now injects session context into settings for tools that need
    access to the current chat or session state (e.g., generate_tasks_tool).
    This allows tools to interact with the broader execution context beyond
    just their direct parameters.

CHANGED: full response accumulation across tool loops:
    Assistant responses generated during tool-calling loops are now accumulated
    across iterations. Previously, only the final response (after all tool calls)
    was returned to the client, losing all intermediate assistant text. Now all
    streamed content is preserved and merged into the final message, ensuring
    no information is lost when the model generates explanatory text before,
    during, or after tool executions.

CHANGED: tool call and iteration limits:
    max_tool_calls and max_iterations are now resolved from AISettings with
    priority: Model > Provider > Fallback. These limits are passed to LoopGuard
    to enforce per-round breadth and overall depth limits on tool execution.

CHANGED: robust tool result handling:
    Tool results are now normalised before being sent back to the model.
    None results are converted to a meaningful sentinel string, non-string/
    non-dict results are JSON-serialised, and ALL exceptions (not just the
    original four types: OSError/ValueError/TypeError/RuntimeError) are caught
    and returned as error strings. This prevents the model from re-issuing
    identical tool calls due to empty/missing/None tool messages.
"""
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Set

from openai import OpenAI
from langchain.messages import AIMessage, HumanMessage

from engine.agent_runtime import (
    AgentCancelled,
    AgentEventType,
    AgentRunContext,
)

from codx.junior.ai.cancellation import CancellationToken, CancelledError
from codx.junior.ai.wallet_check import check_user_wallet
from codx.junior.ai.smol.constants import (
    CALLBACK_FLUSH_SECONDS,
    TOOL_RESULT_PREVIEW_MAX_CHARS,
)
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
from codx.junior.tools import ToolResponse
from codx.junior.utils.utils import clean_string

logger = logging.getLogger(__name__)

# Module-level analytics singleton
_analytics_instance: Optional[Analytics] = None

# Message used whenever the run is cancelled by the caller.
CANCELLED_MESSAGE: str = "Chat was cancelled by the caller."

# Tool scope constants
TOOL_SCOPE_GLOBAL: str = "global"
TOOL_SCOPE_CHAT: str = "chat"

# Sentinel returned to the model when a tool produces no output.
# An empty or None tool message causes the model to re-issue the same call.
_TOOL_NO_OUTPUT: str = "(tool returned no output)"


HARDCODED_SYSTEM_RULES = "\n".join([
    "## Working with files",
    "When working with files always use a 'code blocks' and add the file name after the code block language.",
    "See an example:",
    "```js folder/file_name.js",
    "  import dummy from 'module'",
    "```"
    "### Observe this rules when working with files",
    "* Use valid file path (absolute or relative) based on the project and conversation context.",
    "* New file changes must follow original file formating and identation.",
    "* Avoid unnecessary changes, format changes, or cleanup unless explicitely been asked for it.",
    "* Keep changes simple and easy to review by the user."
])


def _get_analytics() -> Analytics:
    """Return (creating if necessary) the module-level Analytics singleton."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = Analytics()
    return _analytics_instance


def _load_chat_global_instructions() -> str:
    """
    Load chat_global_instructions from GlobalSettings.

    This is called on every chat (not cached) to ensure instructions
    are always up-to-date.

    Returns:
        The chat_global_instructions string from GlobalSettings, or empty
        string if not available.
    """
    try:
        from codx.junior.global_settings import read_global_settings
        global_settings = read_global_settings()
        return "\n".join([
            (global_settings.chat_global_instructions or "").strip(),
            HARDCODED_SYSTEM_RULES
        ])
    except Exception as ex:
        logger.warning(
            "SmolAgent: failed to load chat_global_instructions: %s", ex
        )
        return ""


def _normalise_tool_result(result: Any, func_name: str) -> str:
    """
    Convert any tool return value into a non-empty string suitable for an
    OpenAI tool-result message.

    The model MUST always receive a non-empty tool message. An empty, None,
    or missing content causes it to re-issue the exact same tool call,
    producing an infinite loop that only terminates via LoopGuard.

    Conversion rules (in priority order):
        1. ``None``        → sentinel ``_TOOL_NO_OUTPUT``
        2. ``str``         → returned as-is (empty str → sentinel)
        3. ``dict``/``list`` → JSON-serialised for readability
        4. Anything else   → ``str()`` fallback

    Args:
        result:    Raw value returned by the tool callable.
        func_name: Tool name used only for debug logging.

    Returns:
        A non-empty string representation of the result.
    """
    if result is None:
        logger.debug(
            "SmolAgent: tool '%s' returned None – using sentinel '%s'",
            func_name,
            _TOOL_NO_OUTPUT,
        )
        return _TOOL_NO_OUTPUT

    if isinstance(result, str):
        if not result.strip():
            logger.debug(
                "SmolAgent: tool '%s' returned empty string – using sentinel",
                func_name,
            )
            return _TOOL_NO_OUTPUT
        return result

    try:
        return json.dumps(result, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(result)


class SmolAgent:
    """
    Async-only streaming chat agent with multi-step tool support.

    All logging, event fan-out, cancellation checkpoints and per-run
    analytics are delegated to :class:`AgentRunContext` (the unified
    agent runtime). Callers may pass their own context through
    ``config["run_context"]`` (e.g. to share a Socket.IO listener or a
    cancellation token) or plain listeners via ``config["event_listeners"]``.

    CHANGED: streaming callback contract:
        Callbacks registered via ``config["callbacks"]`` receive the FULL
        response accumulated so far on every flush, never just the newest
        delta. This makes mid-stream persistence of partial content
        crash-safe (no fragment-only saves).

    CHANGED: tool scope support:
        Global scope tools are always included in conversations regardless of
        the selected_tools list. Chat scope tools are selectively included
        based on the request configuration.

    CHANGED: dual-response tools:
        Tools can return a ToolResponse object with both user-facing content
        and LLM feedback. User content is accumulated for the final message,
        while LLM feedback is sent to the model for continued processing.

    CHANGED: global chat instructions:
        chat_global_instructions are loaded from GlobalSettings on every chat
        (not cached) and prepended to the system message. Extra system
        instructions passed to SmolAgent are appended after global instructions.

    CHANGED: session context injection:
        Tools can access the current chat and session via injected context in
        settings. This allows complex tools like generate_tasks_tool to interact
        with the broader conversation state.

    CHANGED: full response accumulation:
        Assistant responses from all iterations (including those with tool_calls)
        are now accumulated and merged into the final message. This preserves
        all assistant text generated during the tool-calling loop, not just
        the final response.

    CHANGED: loop guard with resolved limits:
        max_tool_calls and max_iterations are resolved from AISettings
        (priority: Model > Provider > Fallback) and enforced by LoopGuard
        on every tool round to prevent breadth and depth violations.

    CHANGED: robust tool result handling:
        Tool results are normalised via ``_normalise_tool_result`` before being
        sent back to the model. None/empty results are replaced with a
        meaningful sentinel. All exceptions (not just OSError/ValueError/
        TypeError/RuntimeError) are caught and returned as error strings so the
        model always receives a non-empty tool message, preventing re-issuance
        of identical calls.

    Conversation flow
    ```mermaid
        flowchart TD
            A[chat] --> B[Resolve AgentRunContext]
            B --> C[run_context.run - RUN_START]
            C --> D[Build OpenAI messages]
            D --> E[Stream completion via guard_stream]
            E -->|chunk| E1[Accumulate chunk]
            E1 -->|flush| E2[Callback with FULL accumulated content]
            E --> F{finish_reason?}
            F -->|tool_calls| G[LoopGuard.check - depth & breadth & stuck]
            G -->|ok| H["Save streamed content to llm_responses_accumulated"]
            H --> I[Execute tools - TOOL_START/END/ERROR]
            I --> J{Dual-response tool?}
            J -->|yes| J1[Extract user_content + normalise llm_feedback]
            J -->|no| J2[Normalise result - never None/empty]
            J1 --> J3[Accumulate user_content]
            J1 --> K[Send llm_feedback to model]
            J2 --> K
            J3 --> K
            K --> L[Append to openai_messages]
            L --> E
            G -->|limit exceeded| M[Raise ToolLoopError - RUN_ERROR]
            F -->|stop / length| N[Merge all llm_responses_accumulated + user_content]
            N --> O[Record usage - RUN_END]
            E -->|cancelled| P[RUN_CANCELLED - raise CancelledError]
    ```
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        llm_model: Optional[str] = None,
        user: Optional[CodxUser] = None,
        system: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> None:
        """
        Args:
            settings:  Project settings providing LLM configuration.
            llm_model: Optional model override.
            user:      Optional user (used for API key and analytics).
            system:    Optional extra system prompt content (appended after
                      chat_global_instructions).
            session:   Optional session context (injected for tools that need
                      access to current chat or session state).
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
        # Store extra system instructions; global instructions will be loaded
        # dynamically on each chat to ensure freshness
        self.extra_system: str = (system or "").strip()
        # Store session context for tools that need access to it
        self.session: Optional[Any] = session

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(
            "SmolAgent created. USER: %s, MODEL: %s, URL: %s, "
            "MAX_TOOL_CALLS: %s, MAX_ITERATIONS: %s",
            user.username if user else "NONE",
            self.model,
            self.base_url,
            self.llm_settings.max_tool_calls,
            self.llm_settings.max_iterations,
        )

    def _build_system_message(self) -> str:
        """
        Build the complete system message by combining:
        1. LLM settings system prompt (if any)
        2. chat_global_instructions (loaded fresh from GlobalSettings)
        3. Extra system instructions passed to __init__

        Returns:
            The complete system message string.
        """
        parts: List[str] = []

        # 1. LLM settings system prompt
        if self.llm_settings.system:
            parts.append(self.llm_settings.system.strip())

        # 2. chat_global_instructions (loaded fresh, not cached)
        global_instructions = _load_chat_global_instructions()
        if global_instructions:
            parts.append(global_instructions)

        # 3. Extra system instructions
        if self.extra_system:
            parts.append(self.extra_system)

        return "\n".join(parts).strip()

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
                      ``run_context`` (an :class:`AgentRunContext`),
                      ``event_listeners`` (list of event callables) and
                      ``current_chat`` (the Chat object for context).

        Returns:
            Updated *messages* list with the assistant reply appended.
            User-facing content from dual-response tools is included in
            the assistant message content. All assistant responses across
            the entire tool-calling loop are preserved and merged into
            the final message.

        Raises:
            ToolLoopError:  If max tool rounds, max tool calls, or a stuck
                           loop is detected.
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

        Flow:
        1. Stream completion from LLM
        2. Accumulate streamed content and check for tool calls
        3. If tool_calls exist:
           a. Guard against infinite loops (via LoopGuard):
              - Check iteration depth (max_iterations)
              - Check tool calls per round (max_tool_calls)
              - Detect stuck loops (identical consecutive rounds)
           b. **Save the streamed content to llm_responses_accumulated**
           c. Append assistant message with tool_calls to conversation
           d. For each tool:
              - Execute the tool
              - Normalise the result via _normalise_tool_result (never None/empty)
              - If result is ToolResponse: normalise both user_content and llm_feedback
              - Append tool message to conversation
           e. Loop back to step 1
        4. If no tool_calls, merge LLM content with accumulated user_content
           and all prior llm_responses_accumulated from tool-calling iterations
        5. Record analytics and return updated messages

        Args:
            messages:    Conversation history as LangChain message objects.
            config:      Chat configuration dict (see :meth:`chat`).
            run_context: Unified runtime context for this run.

        Returns:
            Updated *messages* list with the assistant reply appended.

        Raises:
            ToolLoopError:  If max iterations, max tool calls, or stuck loop
                           is detected.
            AgentCancelled: If cancellation is requested mid-run.
        """
        chat_id: Optional[str] = config.get("chat_id")
        cancellation_token: Optional[CancellationToken] = config.get(
            "cancellation_token"
        )
        headers: Dict[str, str] = config.get("headers", {})
        session_id: Optional[str] = headers.get("session_id")
        tags: str = self._build_tags(headers)
        headers["x-litellm-tags"] = tags

        # Inject session context into settings for tools that need it
        current_chat = config.get("current_chat")
        if self.session and current_chat:
            self.settings._active_session = self.session
            self.session._current_chat = current_chat

        send_callback = self._make_callback_sender(config.get("callbacks"))
        kwargs = self._build_request_kwargs(config.get("tools", []))
        # Build system message dynamically on each chat (fresh global instructions)
        system_message = self._build_system_message()
        openai_messages = to_openai_messages(messages, system=system_message)

        # Initialize LoopGuard with resolved limits from AISettings.
        # Priority: Model > Provider > Fallback.
        # These limits are enforced on every tool round to prevent runaway
        # execution or breadth violations.
        loop_guard = LoopGuard(
            max_iterations=self.llm_settings.max_iterations,
            max_tool_calls=self.llm_settings.max_tool_calls,
        )
        request_start = time.monotonic()
        user_facing_content: List[str] = []
        llm_responses_accumulated: List[str] = []

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
                # Final response (no tool calls): add current content to accumulated
                if content:
                    llm_responses_accumulated.append(content)
                break

            # Tool calls detected: save streamed content and continue loop
            if content:
                llm_responses_accumulated.append(content)
                logger.debug(
                    "SmolAgent: round %d accumulated %d bytes of LLM text "
                    "before tool execution",
                    loop_guard.rounds + 1,
                    len(content),
                )

            # Guard against loops BEFORE executing any tool.
            # This checks: depth (max_iterations), breadth (max_tool_calls),
            # and stuck loops (identical consecutive rounds).
            loop_guard.check(tool_calls)

            logger.info(
                "SmolAgent: round %d: executing %d tool(s)",
                loop_guard.rounds,
                len(tool_calls),
            )
            openai_messages.append(
                make_assistant_tool_calls_message(tool_calls, content=content)
            )
            for tool_call in tool_calls.values():
                tool_result = await self._execute_tool(
                    tool_call,
                    request_id=request_id,
                    chat_id=chat_id,
                    run_context=run_context,
                )

                if isinstance(tool_result, ToolResponse):
                    # Dual-response tool: accumulate user-facing content and
                    # send normalised LLM feedback back to the model.
                    # Guard against None/empty user_content before appending.
                    if tool_result.user_content:
                        user_facing_content.append(tool_result.user_content)
                        logger.debug(
                            "SmolAgent: dual-response tool '%s' produced %d bytes "
                            "of user content",
                            tool_call["function"],
                            len(tool_result.user_content),
                        )
                    # Normalise LLM feedback – the model must never receive
                    # an empty tool message or it will repeat the same call.
                    llm_feedback = _normalise_tool_result(
                        tool_result.llm_feedback, tool_call["function"]
                    )
                    openai_messages.append(
                        make_tool_message(
                            tool_call_id=tool_call["id"],
                            content=llm_feedback,
                        )
                    )
                else:
                    # Traditional single-response tool: normalise before sending.
                    # This handles None, empty string, and non-string return values
                    # that would otherwise cause the model to repeat the call.
                    normalised = _normalise_tool_result(
                        tool_result, tool_call["function"]
                    )
                    openai_messages.append(
                        make_tool_message(
                            tool_call_id=tool_call["id"],
                            content=normalised,
                        )
                    )

                logger.debug(
                    "SmolAgent: tool '%s' appended to conversation "
                    "(openai_messages now has %d entries)",
                    tool_call["function"],
                    len(openai_messages),
                )

        duration_seconds = time.monotonic() - request_start
        self._record_usage(
            openai_messages=openai_messages,
            output_text="\n\n".join(llm_responses_accumulated),
            duration_seconds=duration_seconds,
            tags=tags,
            session_id=session_id,
            request_id=request_id,
            usage_info=usage_info,
            chat_id=chat_id,
        )

        # Merge all components into the final response:
        # 1. All LLM-streamed content across all iterations (tool-calling and final)
        # 2. User-facing content from dual-response tools
        final_content_parts: List[str] = []
        final_content_parts.extend(llm_responses_accumulated)
        final_content_parts.extend(user_facing_content)
        final_content = "\n\n".join(part for part in final_content_parts if part)

        if user_facing_content:
            logger.info(
                "SmolAgent: merged %d user-facing content segment(s) "
                "with %d LLM response segment(s) into final message",
                len(user_facing_content),
                len(llm_responses_accumulated),
            )
        if len(llm_responses_accumulated) > 1:
            logger.info(
                "SmolAgent: final message contains text from %d iteration(s) "
                "of the tool loop",
                len(llm_responses_accumulated),
            )

        messages.append(AIMessage(content=final_content))
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
            send_callback:      Chunk callback sender (accumulating: flushes
                                the full response so far to callbacks).
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
    ) -> Union[str, ToolResponse]:
        """
        Execute a single tool call and return its output.

        Emits ``TOOL_START`` / ``TOOL_END`` / ``TOOL_ERROR`` events on the
        run context. Event payloads carry the ``tool_call_id``, the parsed
        JSON request args (``args``) and a truncated ``result`` preview so
        listeners can render tool executions as chat messages. Errors never
        propagate to the caller: ALL exceptions are caught and returned as
        error strings so the model can react to failed tool invocations and
        never receives an empty tool message that would cause it to repeat
        the same call.

        Tools can return either:
            - str: Traditional single-response (used for LLM context)
            - ToolResponse: Dual-response with user_content and llm_feedback

        Args:
            tool_call:   Dict with keys ``id``, ``function``, ``arguments``.
            run_context: Unified runtime context for this run.
            request_id:  Traceability link to the triggering LLM request.
            chat_id:     Chat identifier for analytics.

        Returns:
            The tool result as a string or ToolResponse object.
            Never returns None.

        Raises:
            AgentCancelled: If cancellation was requested before execution.
        """
        # Safe abort point before spending time on a tool.
        run_context.checkpoint()

        func_name: str = tool_call["function"]
        tool_call_id: Optional[str] = tool_call.get("id")
        params = self._parse_tool_arguments(tool_call.get("arguments", "{}"), func_name)
        tool = next(
            (t for t in self.tools if t["tool_json"]["function"]["name"] == func_name),
            None,
        )

        success = True
        error_message: Optional[str] = None
        result_preview: str = ""
        tool_start = time.monotonic()
        # Emit a COPY of the parsed args: `params` is mutated later (settings
        # injection) and listeners may keep a reference to the payload.
        run_context.emit(
            AgentEventType.TOOL_START,
            tool=func_name,
            tool_call_id=tool_call_id,
            args=dict(params),
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

            # Build result_preview for the TOOL_END event payload.
            if isinstance(result, ToolResponse):
                result_preview = (result.llm_feedback or "")[:TOOL_RESULT_PREVIEW_MAX_CHARS]
            else:
                result_str = result if isinstance(result, str) else json.dumps(result)
                result_preview = result_str[:TOOL_RESULT_PREVIEW_MAX_CHARS]
            return result

        except Exception as ex:
            # Catch ALL exceptions (not just OSError/ValueError/TypeError/RuntimeError)
            # so the model always receives a non-empty error string and never
            # re-issues the same tool call due to a missing tool message.
            success = False
            error_message = str(ex)
            logger.exception("SmolAgent: error executing tool '%s'", func_name)
            return f"Error executing tool '{func_name}': {ex}"

        finally:
            duration_ms = (time.monotonic() - tool_start) * 1000
            if success:
                run_context.emit(
                    AgentEventType.TOOL_END,
                    tool=func_name,
                    tool_call_id=tool_call_id,
                    duration_ms=duration_ms,
                    result=result_preview,
                )
            else:
                run_context.emit(
                    AgentEventType.TOOL_ERROR,
                    tool=func_name,
                    tool_call_id=tool_call_id,
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

        Tools are filtered by scope: global scope tools are always included
        regardless of selected_tools, while chat scope tools are selectively
        included based on the request configuration.

        Args:
            selected_tools: Names of chat-scoped tools enabled for this
                           conversation. Global scope tools are added
                           automatically.

        Returns:
            Dict of request kwargs (model, stream, tools, temperature).
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        # Collect all enabled tools: global scope tools (always) + selected
        # chat scope tools.
        selected_tool_set: Set[str] = set(selected_tools) if selected_tools else set()
        enabled_tools: List[Dict[str, Any]] = []

        for tool in self.tools:
            tool_name: str = tool["tool_json"]["function"]["name"]
            tool_scope: str = tool.get("settings", {}).get("scope", TOOL_SCOPE_CHAT)

            # Include tool if it's global or explicitly selected.
            if tool_scope == TOOL_SCOPE_GLOBAL or tool_name in selected_tool_set:
                enabled_tools.append(tool["tool_json"])
                if tool_scope == TOOL_SCOPE_GLOBAL:
                    logger.debug(
                        "SmolAgent: including global scope tool '%s'", tool_name
                    )

        if enabled_tools:
            kwargs["tools"] = enabled_tools

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
        Return a closure that batches streamed chunks and flushes the FULL
        ACCUMULATED response to callbacks.

        CHANGED: accumulation fix:
        Previously each flush sent only the delta buffered since the last
        flush and then cleared the buffer. Downstream consumers (e.g.
        ``ChatEngine.send_message_event``) ASSIGN the callback payload to
        ``response_message.content`` and may PERSIST it mid-stream via the
        ChatEventBridge throttled persist: so partial saves contained only
        the last fragment of the response. Now the sender keeps the complete
        response accumulated across the whole run and sends it on every
        flush, guaranteeing that no streamed information is ever lost in
        mid-run persists.

        flowchart TD
            A[chunk arrives] --> B[Append to buffer]
            B --> C{flush or interval elapsed?}
            C -->|No| D[Return - keep buffering]
            C -->|Yes| E[Move buffer into accumulated]
            E --> F[Join FULL accumulated content]
            F --> G[Invoke callbacks with full content]

        Args:
            callbacks: Callables accepting a str containing the FULL response
                       accumulated so far (may be ``None``).

        Returns:
            A ``send_callback(chunk, flush)`` function.
        """
        state: Dict[str, Any] = {
            "buffer": [],        # chunks pending since the last flush
            "accumulated": [],   # ALL chunks flushed so far (full response)
            "ts": datetime.now(),
        }

        def send_callback(chunk_content: str, flush: bool = False) -> None:
            """Buffer *chunk_content*; flush the FULL accumulated response periodically."""
            if not callbacks:
                return
            state["buffer"].append(chunk_content or "")
            elapsed = (datetime.now() - state["ts"]).total_seconds()
            if flush or elapsed > CALLBACK_FLUSH_SECONDS:
                state["ts"] = datetime.now()
                # Move the pending delta into the accumulated response and
                # send the COMPLETE content so far: never just the delta.
                # This keeps mid-stream persistence crash-safe: any partial
                # save always contains everything streamed up to that point.
                state["accumulated"].extend(state["buffer"])
                state["buffer"] = []
                message = "".join(state["accumulated"])
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
            output_text:      Final assistant response text (all iterations merged).
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