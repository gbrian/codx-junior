"""
SmolAgent: a small, async-only OpenAI chat agent.

Compared to the removed :class:`codx.junior.ai.openai_ai.OpenAI_AI`, this
implementation:
    * exposes a single async ``chat()`` method (no sync variant),
    * uses an **iterative** tool loop instead of recursion,
    * delegates loop protection to :class:`LoopGuard`,
    * delegates logging, event emission and cancellation to
      :class:`engine.agent_runtime.AgentRunContext`,
    * keeps streaming, callbacks, cancellation and analytics.
    * caches tool results per conversation to avoid re-execution.
    * returns a typed :class:`AgentRunResult` (no untyped ``additional_kwargs``).

Tool events (``TOOL_START`` / ``TOOL_END`` / ``TOOL_ERROR`` / ``TOOL_LOGS``) carry the
``tool_call_id``, the parsed JSON request args and a truncated result preview
so listeners (e.g. the ChatEventBridge) can surface tool executions as chat
messages in real time. Tool logs are emitted for forensic audit trail.

Loop-Limit Handling
When :class:`LoopGuard` stops the run (max rounds, max tool calls or stuck
loop), the run is **not** aborted. Instead the tool-usage value is summarised
by the project's knowledge/RAG model and appended to the assistant answer, so
the findings survive in the persisted message and the next iteration can
continue without re-running the same tools. The summary request is
best-effort, does not count towards the loop limits, and its token usage is
recorded separately with the ``tool-analysis`` tag.

Cost-Limit Handling
Every round (iteration) computes its cost in cxjcoins from the provider usage
and the model price settings, accumulates it into the chat total and reports it
on the returned :class:`AgentRunResult` (``result.cost``). Tools that report
their own cost through :attr:`ToolResponse.cost` are summed into both the
per-run total and the chat total. The chat total is seeded from ``Chat.cost``
(the accumulated, deletion-safe value maintained by ChatManager) so the budget
applies to the whole chat and is not reset when messages are deleted. When the
chat reaches its estimated cost (``Chat.estimation_cost``), the run stops
gracefully — before executing further tools — to keep the chat within budget.

Message Structure
When tools are used in a conversation, the agent now produces a single final
answer message that combines all tool user_response outputs (thinking content)
with the final LLM answer. This ensures that all tool-generated user-facing
content is preserved in the persisted message. The thinking content is also streamed
live to the client via send_callback during tool rounds for real-time feedback.

Vision API Support
Binary files (PDFs, images) are passed as vision content when models support it.
The content is merged into the final user message to enable vision-capable models
to process images and documents alongside text.
"""
import json
import logging
import time
import uuid
import inspect
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Set
from asyncio import Future

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
    TOOL_ANALYSIS_TAG,
    TOOL_ANALYSIS_RESULT_MAX_CHARS,
    TOOL_ANALYSIS_TASK_MAX_CHARS,
    TOOL_ANALYSIS_MAX_TOKENS,
    TOOL_ANALYSIS_HEADING,
    TOOL_ANALYSIS_SYSTEM_PROMPT,
    TOOL_ANALYSIS_FALLBACK_NOTE,
    ESTIMATION_COST_EXCEEDED_MSG,
)
from codx.junior.ai.smol.loop_guard import LoopGuard, ToolLoopError
from codx.junior.ai.smol.messages import (
    ToolCallAccumulator,
    make_assistant_tool_calls_message,
    make_tool_message,
    to_openai_messages,
)
from codx.junior.ai.smol.tool_cache import ToolCache
from codx.junior.analytics import Analytics
from codx.junior.analytics.model import ArchivedMessage, ToolCallMessage
from codx.junior.analytics.token_counter import count_tokens
from codx.junior.model.agent import (
    AgentRunResult,
    CostInfo,
    RoundCost,
    ToolCacheStats,
    ToolRunSummary,
)
from codx.junior.model.model import CodxUser
from codx.junior.settings import CODXJuniorSettings
from codx.junior.tools import (
    TOOLS,
    ToolResponse
)
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

# Replace the GLOBAL_CHAT_INSTRUCTIONS constant (also mirrored in engine/session.py)

HARDCODED_SYSTEM_RULES = """
CRITICAL INFORMATION — FILE CHANGES:
Never wrap a file change inside a plain markdown code fence. Propose file changes only as follows.

1) Prefer calling the `code_block_generator` tool once per file with:
   file_path (project-relative), language, content (the FULL new content), change_type (new|update|delete).

2) If tools are unavailable, emit one envelope per file with the sentinels on their own lines:

@@ CODX_FILE @@
path: <project-relative path>
language: <language id>
change_type: <new|update|delete>
encoding: text
@@ CODX_CONTENT @@
<full file content, verbatim — markdown/fences allowed here>
@@ CODX_END @@

Content between the CONTENT and END sentinels is taken verbatim. If the content contains a
line equal to one of the sentinels, use `encoding: base64` instead. Use valid project paths.

### Observe this rules when working with files
 * Use valid file path (absolute or relative) based on the project and conversation context.
 * New file changes must follow original file formating and identation.
 * Avoid unnecessary changes, format changes, or cleanup unless explicitely been asked for it.
 * Keep changes simple and easy to review by the user.
"""



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

    ENHANCED: Now handles more edge cases where tools might return falsy values:
    - Empty lists/dicts
    - Zero (which is falsy but valid)
    - False boolean (which is falsy but valid)

    Conversion rules (in priority order):
        1. ``None``             → sentinel ``_TOOL_NO_OUTPUT``
        2. ``str``              → returned as-is (empty str → sentinel)
        3. ``dict``/``list``    → JSON-serialised for readability
        4. ``0`` or ``False``   → serialised as string (not sentinel!)
        5. Anything else        → ``str()`` fallback

    Args:
        result:    Raw value returned by the tool callable.
        func_name: Tool name used only for debug logging.

    Returns:
        A non-empty string representation of the result.
    """
    # Handle None explicitly (common case)
    if result is None:
        logger.debug(
            "SmolAgent: tool '%s' returned None – using sentinel '%s'",
            func_name,
            _TOOL_NO_OUTPUT,
        )
        return _TOOL_NO_OUTPUT

    # Handle strings (including empty)
    if isinstance(result, str):
        if not result.strip():
            logger.debug(
                "SmolAgent: tool '%s' returned empty string – using sentinel",
                func_name,
            )
            return _TOOL_NO_OUTPUT
        return result

    # Handle empty lists/dicts (valid return values, not "no output")
    if isinstance(result, (list, dict)):
        if not result:  # Empty list or dict
            logger.debug(
                "SmolAgent: tool '%s' returned empty %s – serialising as JSON",
                func_name,
                type(result).__name__,
            )
            return json.dumps(result, ensure_ascii=False)
        try:
            return json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(result)

    # Handle falsy but valid values (0, False, etc.)
    # These SHOULD be serialised, not replaced with sentinel
    if result == 0 or result is False:
        logger.debug(
            "SmolAgent: tool '%s' returned %r (falsy but valid)",
            func_name,
            result,
        )
        return str(result)

    # Fallback: serialize any other type
    try:
        return json.dumps(result, ensure_ascii=False)
    except (TypeError, ValueError):
        serialized = str(result)
        # Guard against empty string from str() fallback
        if not serialized.strip():
            logger.warning(
                "SmolAgent: tool '%s' returned %r which str() converted to empty string",
                func_name,
                result,
            )
            return _TOOL_NO_OUTPUT
        return serialized


class SmolAgent:
    """
    Async-only streaming chat agent with multi-step tool support.

    All logging, event fan-out, cancellation checkpoints and per-run
    analytics are delegated to :class:`AgentRunContext` (the unified
    agent runtime). Callers may pass their own context through
    ``config["run_context"]`` (e.g. to share a Socket.IO listener or a
    cancellation token) or plain listeners via ``config["event_listeners"]``.

    Conversation flow
    ```mermaid
        flowchart TD
            A[chat] --> B[Resolve AgentRunContext]
            B --> C[run_context.run - RUN_START]
            C --> D[Build OpenAI messages]
            D --> E[Initialize ToolCache]
            E --> F[Stream completion via guard_stream]
            F -->|chunk| F1[Accumulate chunk]
            F1 -->|flush| F2[Callback with FULL accumulated content]
            F --> G{finish_reason?}
            G -->|tool_calls| H[Check ToolCache]
            H -->|HIT| H1[Skip _execute_tool - use cached]
            H -->|HIT| H2[Emit TOOL_END with cached=true]
            H -->|HIT - ToolResponse| H3[Surface user_response to thinking_content]
            H -->|MISS| I[LoopGuard.check - depth & breadth & stuck]
            I -->|ok| J[Execute tool - TOOL_START/END/ERROR/LOGS]
            H1 --> K{Dual-response tool?}
            J --> K
            K -->|yes| K1[Append user_response to thinking_content]
            K -->|yes| K2[Send llm_response as tool result to model only]
            K -->|no| K3[Send normalised result as tool result to model only]
            K1 --> K4[Flush new thinking_content block to callback]
            K2 --> L[Append to openai_messages]
            K3 --> L
            K4 --> L
            L --> F
            I -->|limit exceeded| M[Summarise tool usage and finish gracefully]
            G -->|stop / length| N[Append final LLM text to final_answer_content]
            N --> O[Append final AIMessage + return typed AgentRunResult]
            M --> O
            O --> P[Record usage + cache stats - RUN_END]
            F -->|cancelled| Q[RUN_CANCELLED - raise CancelledError]
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
    ) -> AgentRunResult:
        """
        Run a streaming chat completion with iterative multi-step tool support.

        The whole run is wrapped in :meth:`AgentRunContext.run`, which emits
        ``RUN_START`` / ``RUN_END`` / ``RUN_ERROR`` / ``RUN_CANCELLED`` events
        with an analytics summary attached.

        Tool results are cached within this conversation to avoid re-execution
        if the model requests the same tool with identical arguments.

        Loop limits are handled gracefully: instead of raising, the run is
        stopped and a summary of the tools used is appended to the assistant
        answer (see :meth:`_summarize_tool_usage`). This keeps the work in the
        persisted message so the next iteration can continue without repeating
        the same tools.

        Cost limits are handled gracefully too: every round's cost (plus any
        cost reported by tools via :attr:`ToolResponse.cost`) is accumulated and
        returned in the typed :class:`AgentRunResult`. Once the chat reaches
        ``Chat.estimation_cost``, the run stops before executing further tools so
        the chat never exceeds its budget.

        Message Structure
        The response always appends a single final answer AIMessage that
        combines thinking content (tool user_response outputs) with the final
        LLM answer. This ensures all tool-generated user-facing content is
        persisted correctly.

        Args:
            messages: Conversation history as LangChain message objects.
            config:   Optional dict with keys: ``tools``, ``chat_id``,
                      ``cancellation_token``, ``headers``, ``callbacks``,
                      ``run_context`` (an :class:`AgentRunContext`),
                      ``event_listeners`` (list of event callables),
                      ``current_chat`` (the Chat object for context), and
                      ``vision_content`` (optional vision API content blocks).

        Returns:
            The typed :class:`AgentRunResult` for this run. Its ``messages``
            attribute contains the updated conversation (with the final
            assistant reply appended); ``cost`` carries the cost breakdown.

        Raises:
            CancelledError: If the request is cancelled by the caller.
        """
        config = config or {}
        self._preflight_limit_check()

        run_context = self._resolve_run_context(config)
        result: Optional[AgentRunResult] = None

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
    ) -> AgentRunResult:
        """
        Execute the iterative streaming/tool loop for one conversation.

        Response accumulation strategy:
        - ``thinking_content``: Accumulates LLM text and dual-response
          user_response strings during tool-calling rounds. Streamed live
          to the client via send_callback. ALSO included in the final AIMessage
          so all tool-generated user-facing content is persisted correctly.
        - ``final_answer_content``: Accumulates LLM text during the final
          round (after the model stops making tool calls).

        Message generation:
        - Always emits exactly one AIMessage combining thinking_content and
          final_answer_content so the persisted message contains everything
          the user saw during streaming. All run information (cost, usage,
          tool summaries) is returned in the typed :class:`AgentRunResult`.

        Tool caching:
        - Identical tool calls (same name + args) are cached per conversation.
        - Cached results bypass LoopGuard checks (don't count towards limits).
        - Cached ToolResponse results surface user_response to thinking_content
          exactly like uncached ones.

        Loop limits:
        - When LoopGuard raises, the loop is broken gracefully (no exception
          propagates) and a summary of the tools used is appended to
          ``thinking_content`` so it is streamed to the user and persisted in
          the final answer.

        Cost limits:
        - Every round is priced in cxjcoins from provider usage + model prices
          and accumulated into the chat total. When the chat reaches its
          ``estimation_cost``, the loop is broken gracefully (before running
          more tools) and a notice is appended to the answer.

        Args:
            messages:    Conversation history as LangChain message objects.
            config:      Chat configuration dict (see :meth:`chat`).
            run_context: Unified runtime context for this run.

        Returns:
            The typed :class:`AgentRunResult` for this run.

        Raises:
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

        # Initialize tool cache for this conversation.
        # Cached results bypass LoopGuard checks and don't count towards limits.
        tool_cache = ToolCache()

        # Chat cost budget: seed the accumulated chat cost from Chat.cost, the
        # deletion-safe accumulator maintained by ChatManager. Falling back to
        # summing the message costs keeps this working for chats persisted
        # before the accumulator existed.
        chat_cost: float = self._accumulated_chat_cost(current_chat)
        # Cost of THIS run (this SmolAgent iteration).
        iteration_cost: float = 0.0

        # Typed run accumulators (replace the previous additional_kwargs contract).
        # They feed the returned AgentRunResult.cost breakdown.
        total_input_tokens: int = 0
        total_output_tokens: int = 0
        total_input_cost: float = 0.0
        total_output_cost: float = 0.0
        total_tool_cost: float = 0.0
        tool_cost_by_name: Dict[str, float] = {}

        request_start = time.monotonic()

        # Track whether any tools were used in this conversation.
        tools_were_used: bool = False

        # thinking_content: accumulates tool user_response outputs and LLM text
        # during tool-calling rounds. Streamed live to client AND included in
        # the final AIMessage so persisted content matches what was streamed.
        # final_answer_content: the final LLM response after all tool calls.
        thinking_content: str = ""
        final_answer_content: str = ""

        # Set when LoopGuard stops the run. The loop is then broken gracefully
        # and a tool-usage summary is produced so the work is not lost.
        loop_limit_error: Optional[str] = None

        # Set when the chat reaches its estimated cost. The loop is then broken
        # gracefully (before executing more tools) and a notice is appended.
        cost_limit_error: Optional[str] = None

        # Initialised before the loop so they are always defined for the
        # post-loop analytics call, even when the very first budget check stops
        # the run before any completion is performed.
        request_id: Optional[str] = None
        usage_info: Any = None

        # Extract vision content from config (optional)
        vision_content: Optional[List[Dict[str, Any]]] = config.get("vision_content")

        # Iterative tool loop: keep streaming completions until the model
        # produces a final answer (no more tool_calls finish reason).
        while True:
            # Stop BEFORE spending more when the chat already reached its
            # estimated cost (covers the case where a previous round pushed the
            # chat over budget).
            if self._cost_limit_exceeded(current_chat, chat_cost):
                cost_limit_error = ESTIMATION_COST_EXCEEDED_MSG.format(
                    spent=chat_cost,
                    limit=current_chat.estimation_cost,
                )
                logger.warning(
                    "SmolAgent: chat cost limit reached before round %d "
                    "(spent=%.4f, limit=%.4f); stopping gracefully",
                    loop_guard.rounds + 1,
                    chat_cost,
                    current_chat.estimation_cost,
                )
                break

            request_id = str(uuid.uuid4())
            content, tool_calls, usage_info = await self._stream_completion(
                kwargs=kwargs,
                openai_messages=openai_messages,
                headers=headers,
                cancellation_token=cancellation_token,
                send_callback=send_callback,
                run_context=run_context,
                request_id=request_id,
                chat_id=chat_id,
                system_message=system_message,
                vision_content=vision_content,
            )

            # Register the cost of this round (iteration) in cxjcoins and add
            # it to both the iteration total and the chat total.
            round_cost = self._compute_cost(
                usage_info=usage_info,
                content=content,
                openai_messages=openai_messages,
            )
            iteration_cost += round_cost.total_cost_cxjcoins
            chat_cost += round_cost.total_cost_cxjcoins
            total_input_tokens += round_cost.input_tokens
            total_output_tokens += round_cost.output_tokens
            total_input_cost += round_cost.input_cost_cxjcoins
            total_output_cost += round_cost.output_cost_cxjcoins
            logger.info(
                "SmolAgent: round cost %.6f cxjcoins "
                "(iteration total %.6f, chat total %.6f)",
                round_cost.total_cost_cxjcoins,
                iteration_cost,
                chat_cost,
            )

            if not tool_calls:
                # Final response (no tool calls): accumulate in final_answer_content
                # and exit the loop.
                if content:
                    final_answer_content += content
                break

            # Enforce the chat cost budget BEFORE executing more tools so the
            # chat does not spend beyond the estimated cost the user set.
            if self._cost_limit_exceeded(current_chat, chat_cost):
                cost_limit_error = ESTIMATION_COST_EXCEEDED_MSG.format(
                    spent=chat_cost,
                    limit=current_chat.estimation_cost,
                )
                logger.warning(
                    "SmolAgent: chat cost limit reached at round %d "
                    "(spent=%.4f, limit=%.4f); stopping before tools",
                    loop_guard.rounds + 1,
                    chat_cost,
                    current_chat.estimation_cost,
                )
                break

            # Tool calls detected: mark that tools were used and accumulate LLM
            # text in thinking_content (this is preprocessing/reasoning).
            tools_were_used = True
            if content:
                thinking_content += content
                logger.debug(
                    "SmolAgent: round %d accumulated %d bytes of LLM text "
                    "before tool execution",
                    loop_guard.rounds + 1,
                    len(content),
                )

            # Separate cached and non-cached tool calls
            cached_calls: Dict[str, Dict[str, Any]] = {}
            uncached_calls: Dict[str, Dict[str, Any]] = {}

            for tool_id, tool_call in tool_calls.items():
                func_name = tool_call["function"]
                params = self._parse_tool_arguments(
                    tool_call.get("arguments"), func_name
                )
                cached_result = tool_cache.get(func_name, params)

                if cached_result is not None:
                    cached_calls[tool_id] = {
                        "tool_call": tool_call,
                        "params": params,
                        "result": cached_result,
                    }
                else:
                    uncached_calls[tool_id] = tool_call

            # Guard ONLY against uncached tool calls. Cached results bypass
            # LoopGuard checks entirely (don't count towards max_tool_calls
            # or max_iterations).
            if uncached_calls:
                try:
                    loop_guard.check(uncached_calls)
                except ToolLoopError as ex:
                    # Limits reached: do NOT let the exception abort the run
                    # (that would discard every tool result gathered so far).
                    # Stop the loop and summarise the tools used so the work
                    # survives in the response message and can be reused in the
                    # next iteration without re-executing the same tools.
                    loop_limit_error = str(ex)
                    logger.warning(
                        "SmolAgent: tool loop limit reached at round %d (%s); "
                        "stopping gracefully and summarising tool usage",
                        loop_guard.rounds,
                        loop_limit_error,
                    )
                    break

            total_tools = len(tool_calls)
            cached_count = len(cached_calls)
            if cached_count > 0:
                logger.info(
                    "SmolAgent: round %d: %d/%d tool(s) cached, "
                    "%d new",
                    loop_guard.rounds,
                    cached_count,
                    total_tools,
                    len(uncached_calls),
                )

            logger.info(
                "SmolAgent: round %d: executing %d tool(s)",
                loop_guard.rounds,
                len(uncached_calls),
            )

            # Add message to record which tools were requested
            openai_messages.append(
                make_assistant_tool_calls_message(tool_calls, content=content)
            )

            # Process cached tool calls (no execution, just emit events)
            for tool_id, cached_info in cached_calls.items():
                tool_call = cached_info["tool_call"]
                result = cached_info["result"]
                func_name = tool_call["function"]

                # Emit TOOL_END with cached=True for observability
                run_context.emit(
                    AgentEventType.TOOL_END,
                    tool=func_name,
                    tool_call_id=tool_id,
                    duration_ms=0,
                    result=(
                        result[:TOOL_RESULT_PREVIEW_MAX_CHARS]
                        if isinstance(result, str)
                        else str(result)[:TOOL_RESULT_PREVIEW_MAX_CHARS]
                    ),
                    cached=True,
                )

                # Emit tool logs if ToolResponse has any
                if isinstance(result, ToolResponse) and result.logs:
                    run_context.emit(
                        AgentEventType.TOOL_LOGS,
                        tool=func_name,
                        tool_call_id=tool_id,
                        logs=result.logs,
                    )

                # FIX Issue 1: cached ToolResponse must surface user_response
                # into thinking_content exactly like the uncached path does.
                if isinstance(result, ToolResponse):
                    if result.user_response:
                        # Build the new block ONCE so it is appended to
                        # thinking_content and streamed as a DELTA.
                        user_block = f"\n```\n{result.user_response}\n```\n"
                        thinking_content += user_block
                        # send_callback accumulates internally and emits the
                        # FULL accumulated response on flush. Passing only the
                        # NEW block avoids re-emitting everything already
                        # streamed (which previously duplicated content on
                        # every tool round).
                        send_callback(user_block, True)
                        logger.debug(
                            "SmolAgent: cached dual-response tool '%s' produced "
                            "%d bytes of user content; flushed new content block",
                            func_name,
                            len(result.user_response),
                        )
                    llm_response = _normalise_tool_result(
                        result.llm_response, func_name
                    )
                    openai_messages.append(
                        make_tool_message(
                            tool_call_id=tool_id,
                            content=llm_response,
                        )
                    )
                else:
                    # Plain cached result: send to model only
                    openai_messages.append(
                        make_tool_message(
                            tool_call_id=tool_id,
                            content=_normalise_tool_result(result, func_name),
                        )
                    )

                logger.debug(
                    "SmolAgent: cached tool '%s' appended to conversation "
                    "(openai_messages now has %d entries)",
                    func_name,
                    len(openai_messages),
                )

            # Process uncached tool calls — check cancellation between each
            # tool execution so a cancellation request is honoured promptly
            # even when multiple tools are being processed sequentially in
            # one round.
            for tool_id, tool_call in uncached_calls.items():
                # Cancellation checkpoint BEFORE each tool.
                # _execute_tool also calls checkpoint internally, but checking
                # here ensures we never start a tool when already cancelled.
                run_context.checkpoint()

                tool_result = await self._execute_tool(
                    tool_call,
                    request_id=request_id,
                    chat_id=chat_id,
                    run_context=run_context,
                    tool_cache=tool_cache,
                )

                if isinstance(tool_result, ToolResponse):
                    # Dual-response tool:
                    # - user_response → thinking_content (streamed live AND
                    #   included in final AIMessage for persistence)
                    # - llm_response → model tool message only (NOT in response)
                    if tool_result.user_response:
                        # Build the new block ONCE so it is appended to
                        # thinking_content and streamed as a DELTA.
                        user_block = (
                            f"\n```\n{tool_result.user_response}\n```\n"
                        )
                        thinking_content += user_block
                        # send_callback accumulates internally and emits the
                        # FULL accumulated response on flush. Passing only the
                        # NEW block ensures the user_response is visible during
                        # processing WITHOUT re-emitting everything that was
                        # already streamed (which previously duplicated content
                        # across tool rounds).
                        send_callback(user_block, True)
                        logger.debug(
                            "SmolAgent: dual-response tool '%s' produced %d bytes "
                            "of user content; flushed new content block",
                            tool_call["function"],
                            len(tool_result.user_response),
                        )
                    # Normalise LLM feedback – the model must never receive
                    # an empty tool message or it will repeat the same call.
                    llm_response = _normalise_tool_result(
                        tool_result.llm_response, tool_call["function"]
                    )
                    openai_messages.append(
                        make_tool_message(
                            tool_call_id=tool_id,
                            content=llm_response,
                        )
                    )
                else:
                    # Traditional single-response tool: normalise and send to
                    # the model only. Plain tool results are NOT added to any
                    # response (thinking or final).
                    normalised = _normalise_tool_result(
                        tool_result, tool_call["function"]
                    )
                    openai_messages.append(
                        make_tool_message(
                            tool_call_id=tool_id,
                            content=normalised,
                        )
                    )

                # Register any cost reported by the tool itself (e.g. a tool
                # that performs its own AI call) into this iteration and the
                # chat total, so it is billed on the response message and
                # counted towards the estimation_cost budget. Cached results
                # are intentionally skipped: no new cost is incurred when a
                # tool result is reused within the same run.
                tool_cost = self._tool_cost(tool_result)
                if tool_cost:
                    iteration_cost += tool_cost
                    chat_cost += tool_cost
                    total_tool_cost += tool_cost
                    tool_cost_by_name[tool_call["function"]] = (
                        tool_cost_by_name.get(tool_call["function"], 0.0)
                        + tool_cost
                    )
                    logger.info(
                        "SmolAgent: tool '%s' reported cost %.6f cxjcoins "
                        "(iteration total %.6f, chat total %.6f)",
                        tool_call["function"],
                        tool_cost,
                        iteration_cost,
                        chat_cost,
                    )

                logger.debug(
                    "SmolAgent: tool '%s' appended to conversation "
                    "(openai_messages now has %d entries)",
                    tool_call["function"],
                    len(openai_messages),
                )

            # FIX 1: INCREMENT LOOP GUARD AFTER PROCESSING ALL TOOLS
            # This is CRITICAL for preventing infinite loops when:
            # 1. All tool calls are cached (normally bypass loop guard checks)
            # 2. Model requests same tool repeatedly with identical args
            # 3. Vision content or attachments trigger repeated tool calls
            #
            # Incrementing here ensures:
            # - loop_guard.rounds increases every iteration (even all-cached)
            # - Stuck loop detection works for cached tool repetition
            # - max_iterations limit is enforced regardless of cache hits
            if tool_calls:
                loop_guard.rounds += 1
                logger.info(
                    "SmolAgent: round %d complete (cached=%d, uncached=%d, "
                    "iterations_left=%d/%d)",
                    loop_guard.rounds,
                    cached_count,
                    len(uncached_calls),
                    loop_guard.max_iterations - loop_guard.rounds if loop_guard.max_iterations else "unlimited",
                    loop_guard.max_iterations if loop_guard.max_iterations else "unlimited",
                )

        duration_seconds = time.monotonic() - request_start
        self._record_usage(
            openai_messages=openai_messages,
            output_text=final_answer_content,
            thinking_text=thinking_content if tools_were_used else "",
            duration_seconds=duration_seconds,
            tags=tags,
            session_id=session_id,
            request_id=request_id,
            usage_info=usage_info,
            chat_id=chat_id,
            tool_cache=tool_cache,
        )

        # When the run was stopped by LoopGuard, append a summary of the tools
        # used (findings + useless calls) produced by the knowledge/RAG model.
        # This preserves the tool context in the response message so the next
        # iteration can continue without re-executing the same tools, and gives
        # the user visibility into what was learned before the run stopped.
        if loop_limit_error:
            summary_block = self._summarize_tool_usage(
                openai_messages=openai_messages,
                loop_error=loop_limit_error,
                chat_id=chat_id,
                session_id=session_id,
            )
            if summary_block:
                thinking_content += summary_block
                # Stream the summary live so the user sees it as it is produced.
                send_callback(summary_block, True)
                logger.info(
                    "SmolAgent: appended tool usage summary (%d chars) after "
                    "loop limit was reached",
                    len(summary_block),
                )

        # When the chat reached its estimated cost, append a notice so the user
        # understands why the run stopped. No extra model request is made here
        # (that would spend more of the budget).
        if cost_limit_error:
            thinking_content += cost_limit_error
            # Stream the notice live so the user sees it immediately.
            send_callback(cost_limit_error, True)
            logger.info(
                "SmolAgent: appended chat cost limit notice (%d chars) after "
                "estimation_cost was reached",
                len(cost_limit_error),
            )

        # thinking_content is streamed live via send_callback during tool rounds
        # AND must be included in the final AIMessage so that chat_engine.py
        # persists it correctly. Without this, response_message.content only
        # gets final_answer_content and all tool user_response outputs are lost
        # from the saved message even though they were streamed to the client.
        if tools_were_used and thinking_content:
            logger.info(
                "SmolAgent: thinking content assembled with %d characters "
                "(streamed live via callback AND included in final AIMessage)",
                len(thinking_content),
            )

        # Always emit exactly one final answer AIMessage combining thinking
        # content (tool user_response outputs) and the final LLM answer.
        # This ensures the persisted message matches what was streamed.
        # NO untyped metadata is attached: the full cost/usage breakdown is
        # returned in the typed AgentRunResult below.
        combined_content = ""
        if thinking_content:
            combined_content += thinking_content
        if final_answer_content:
            combined_content += final_answer_content

        if combined_content:
            logger.info(
                "SmolAgent: final answer message assembled with %d characters "
                "(%d thinking + %d final answer, %.6f cxjcoins)",
                len(combined_content),
                len(thinking_content),
                len(final_answer_content),
                iteration_cost,
            )
            messages.append(AIMessage(content=combined_content))
        elif not tools_were_used:
            # Edge case: no tools used and no content (shouldn't happen, but handle it)
            logger.warning("SmolAgent: no content produced in chat")
            messages.append(AIMessage(content=""))

        # Build the typed run result (replaces the previous untyped
        # ``additional_kwargs = {"cost": ..., "chat_cost": ...}`` contract).
        analytics_summary = run_context.analytics.summary()
        tool_stats: Dict[str, Dict[str, Any]] = analytics_summary.get("tools", {}) or {}
        cache_stats = tool_cache.stats()

        cost_info = CostInfo(
            iteration_cost_cxjcoins=iteration_cost,
            chat_cost_cxjcoins=chat_cost,
            estimation_cost_cxjcoins=getattr(current_chat, "estimation_cost", None),
            budget_reached=bool(cost_limit_error),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            total_tokens=total_input_tokens + total_output_tokens,
            input_cost_cxjcoins=total_input_cost,
            output_cost_cxjcoins=total_output_cost,
            tool_cost_cxjcoins=total_tool_cost,
        )

        return AgentRunResult(
            content=combined_content,
            messages=messages,
            cost=cost_info,
            iterations=loop_guard.rounds,
            tools_used=tools_were_used,
            tools=[
                ToolRunSummary(
                    tool=name,
                    calls=stats.get("count", 0),
                    errors=stats.get("errors", 0),
                    duration_ms=stats.get("total_ms", 0.0),
                    cost_cxjcoins=tool_cost_by_name.get(name, 0.0),
                )
                for name, stats in tool_stats.items()
            ],
            cache=ToolCacheStats(
                hits=cache_stats.get("hits", 0),
                misses=cache_stats.get("misses", 0),
                size=cache_stats.get("size", 0),
                hit_rate=cache_stats.get("hit_rate", 0),
            ),
            loop_limit_reached=bool(loop_limit_error),
        )

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

    @staticmethod
    def _validate_vision_content(
        vision_content: List[Dict[str, Any]]
    ) -> bool:
        """
        Validate that vision content blocks are in valid OpenAI format.

        Each block must be JSON-serializable and have a valid structure:
        - image_url blocks must have image_url with url
        - Other types must have type and appropriate fields

        Args:
            vision_content: List of vision content blocks to validate.

        Returns:
            True if all blocks are valid, False otherwise.
        """
        if not vision_content:
            return True

        for i, block in enumerate(vision_content):
            if not isinstance(block, dict):
                logger.error(
                    "SmolAgent: vision block %d is not a dict: %s",
                    i, type(block)
                )
                return False

            block_type = block.get("type", "")
            
            if block_type == "image_url":
                image_url = block.get("image_url", {})
                if not isinstance(image_url, dict) or "url" not in image_url:
                    logger.error(
                        "SmolAgent: vision block %d (type='image_url') missing image_url.url",
                        i
                    )
                    return False
            elif block_type == "text":
                if "text" not in block:
                    logger.error(
                        "SmolAgent: vision block %d (type='text') missing text field",
                        i
                    )
                    return False
            else:
                logger.warning(
                    "SmolAgent: vision block %d has unsupported type '%s'",
                    i, block_type
                )

            # Ensure the block is JSON-serializable
            try:
                json.dumps(block)
            except (TypeError, ValueError) as ex:
                logger.error(
                    "SmolAgent: vision block %d is not JSON-serializable: %s",
                    i, ex
                )
                return False

        return True

    async def _stream_completion(
        self,
        kwargs: Dict[str, Any],
        openai_messages: List[Dict[str, Any]],
        headers: Dict[str, str],
        cancellation_token: Optional[CancellationToken],
        send_callback: Callable[[str, bool], None],
        run_context: AgentRunContext,
        request_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        system_message: Optional[str] = None,
        vision_content: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Dict[str, Dict[str, Any]], Any]:
        """
        Stream one completion, collecting content, tool calls and usage.

        The stream is wrapped by :meth:`AgentRunContext.guard_stream`, which
        checks cancellation on every chunk and emits throttled ``LLM_CHUNK``
        events for live UI progress. Provider usage is emitted as
        ``LLM_USAGE`` so run analytics aggregate tokens automatically.

        ADDED: vision_content (images, PDFs) can be merged into the final
        user message for models that support vision APIs.

        Args:
            kwargs:             Base OpenAI request kwargs.
            openai_messages:    Current OpenAI-format conversation history.
            headers:            Extra request headers.
            cancellation_token: Optional legacy cancellation token (bridged
                                onto the run context token).
            send_callback:      Chunk callback sender (accumulating: flushes
                                the full response so far to callbacks).
            run_context:        Unified runtime context for this run.
            request_id:         Unique request identifier for traceability.
            chat_id:            Chat identifier for linking to archived messages.
            system_message:     The system message used (for forensic audit).
            vision_content:     Optional list of vision content blocks (image_url, file types)
                               to merge into the final user message.

        Returns:
            Tuple of ``(content, tool_calls, usage_info)``.

        Raises:
            AgentCancelled: If cancellation is requested mid-stream.
        """
        # ADDED: Validate vision content before merging
        if vision_content:
            if not self._validate_vision_content(vision_content):
                logger.error(
                    "SmolAgent: invalid vision content structure detected, skipping"
                )
                vision_content = None

        # ADDED: Merge vision content into the last user message if provided and valid
        if vision_content and openai_messages:
            # Find the last user message (iterate backwards)
            for msg in reversed(openai_messages):
                if msg.get("role") == "user":
                    current_content = msg.get("content")
                    if isinstance(current_content, str):
                        # Convert to list format to add vision content
                        msg["content"] = [
                            {"type": "text", "text": current_content},
                            *vision_content
                        ]
                    elif isinstance(current_content, list):
                        # Append vision content to existing list
                        msg["content"].extend(vision_content)
                    
                    # Validate the merged message is JSON-serializable
                    try:
                        json.dumps(msg)
                        logger.info(
                            "Added %d vision content block(s) to user message",
                            len(vision_content)
                        )
                    except (TypeError, ValueError) as ex:
                        logger.error(
                            "SmolAgent: merged message not JSON-serializable: %s, "
                            "reverting vision content",
                            ex
                        )
                        # Revert to original content
                        if isinstance(current_content, str):
                            msg["content"] = current_content
                        else:
                            # Remove the vision content we just added
                            msg["content"] = msg["content"][:-len(vision_content)]
                    break

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
        content = "".join(content_parts)

        # Archive the complete message exchange after successful streaming
        # Captures complete forensic data: request kwargs, tool definitions, system prompt
        if request_id and (content or accumulator.tool_calls):
            try:
                analytics = _get_analytics()
                
                # Extract complete LLM request kwargs for forensic audit trail
                # These parameters are needed to reproduce the exact model behavior
                temperature = kwargs.get("temperature")
                max_tokens = kwargs.get("max_tokens")
                tools = kwargs.get("tools")  # Complete tool definitions array
                
                analytics.record_archived_message(
                    message_id=str(uuid.uuid4()),
                    chat_id=chat_id or "",
                    username=self.user.username if self.user else "anonymous",
                    project_name=self.settings.project_name or "",
                    project_id=getattr(self.settings, "project_id", "") or "",
                    model=self.model,
                    provider=self.llm_settings.provider or "",
                    request_messages=openai_messages,  # Full conversation history
                    response_content=content,  # Complete LLM response
                    request_id=request_id,
                    duration_seconds=0.0,
                    input_tokens=getattr(usage_info, "prompt_tokens", 0) or 0,
                    output_tokens=getattr(usage_info, "completion_tokens", 0) or 0,
                    temperature=temperature,  # FORENSIC: Model temperature for reproducibility
                    max_tokens=max_tokens,  # FORENSIC: Max tokens limit
                    tools=tools,  # FORENSIC: Complete tool JSON schemas sent to model
                    system_prompt=system_message,  # FORENSIC: The system message sent
                )
            except OSError as ex:
                logger.warning("SmolAgent: failed to archive message: %s", ex)

        return content, accumulator.get_tool_calls(), usage_info

    # ── Tool execution ─────────────────────────────────────────────────────────

    def _get_tool_definition(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Extract the complete tool definition (JSON schema) for a given tool name.

        Used for forensic audit trail — stores the exact tool definition that
        was sent to the LLM model for this tool call.

        Args:
            tool_name: The name of the tool to find.

        Returns:
            The complete tool_json definition dict (with name, description, parameters),
            or None if not found.
        """
        for tool in self.tools:
            if tool["tool_json"]["function"]["name"] == tool_name:
                return tool.get("tool_json")
        return None

    async def _execute_tool(
        self,
        tool_call: Dict[str, Any],
        run_context: AgentRunContext,
        request_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        tool_cache: Optional[ToolCache] = None,
    ) -> Union[str, ToolResponse]:
        """
        Execute a single tool call and return its output.

        Emits ``TOOL_START`` / ``TOOL_END`` / ``TOOL_ERROR`` / ``TOOL_LOGS`` 
        events on the run context. Event payloads carry the ``tool_call_id``,
        the parsed JSON request args (``args``) and a truncated ``result`` 
        preview so listeners can render tool executions as chat messages. 
        Tool logs are emitted for forensic audit trail. Errors never propagate 
        to the caller: ALL exceptions are caught and returned as error strings 
        so the model can react to failed tool invocations and never receives 
        an empty tool message that would cause it to repeat the same call.

        Results are cached by tool name + parameters hash for reuse within
        the conversation.

        Tools can return either:
            - str: Traditional single-response (used for LLM context only)
            - ToolResponse: Dual-response; user_response goes to the thinking
              message, llm_response goes to the model only. ToolResponse can
              include logs for forensic audit trail and a cost (cxjcoins)
              which is summed into the response/chat cost.

        Args:
            tool_call:   Dict with keys ``id``, ``function``, ``arguments``.
            run_context: Unified runtime context for this run.
            request_id:  Traceability link to the triggering LLM request.
            chat_id:     Chat identifier for analytics.
            tool_cache:  Optional tool result cache for this conversation.

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
        params = self._parse_tool_arguments(tool_call.get("arguments"), func_name)
        tool = next(
            (t for t in self.tools if t["tool_json"]["function"]["name"] == func_name),
            None,
        )

        success = True
        error_message: Optional[str] = None
        result_preview: str = ""
        result: Union[str, ToolResponse] = ""
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
            # Pass tool cache to tools so they can share state across calls
            # (e.g., file content modifications in apply_file_changes)
            # Only pass tool_cache if the tool function accepts it, to avoid
            # TypeError for tools that don't support this parameter (fixes
            # "project_structure() got an unexpected keyword argument 'tool_cache'")
            if tool_cache:
                try:
                    sig = inspect.signature(tool["tool_call"])
                    if "tool_cache" in sig.parameters:
                        params["tool_cache"] = tool_cache
                except (ValueError, TypeError):
                    pass

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
                result_preview = (result.llm_response or "")[:TOOL_RESULT_PREVIEW_MAX_CHARS]
            else:
                result_str = result if isinstance(result, str) else json.dumps(result)
                result_preview = result_str[:TOOL_RESULT_PREVIEW_MAX_CHARS]

            # Cache the result before returning
            if tool_cache:
                tool_cache.set(func_name, params, result, success=True)

            return result

        except Exception as ex:
            # Catch ALL exceptions (not just OSError/ValueError/TypeError/RuntimeError)
            # so the model always receives a non-empty error string and never
            # re-issues the same tool call due to a missing tool message.
            success = False
            error_message = str(ex)
            error_result = f"Error executing tool '{func_name}': {ex}"
            logger.exception("SmolAgent: error executing tool '%s'", func_name)

            # Cache the error result too so we don't re-execute a failing tool
            if tool_cache:
                tool_cache.set(func_name, params, error_result, success=False)

            return error_result

        finally:
            duration_ms = (time.monotonic() - tool_start) * 1000
            duration_seconds = time.monotonic() - tool_start

            if success:
                run_context.emit(
                    AgentEventType.TOOL_END,
                    tool=func_name,
                    tool_call_id=tool_call_id,
                    duration_ms=duration_ms,
                    result=result_preview,
                )
                
                # Emit tool logs if ToolResponse has any
                if isinstance(result, ToolResponse) and result.logs:
                    run_context.emit(
                        AgentEventType.TOOL_LOGS,
                        tool=func_name,
                        tool_call_id=tool_call_id,
                        logs=result.logs,
                    )
            else:
                run_context.emit(
                    AgentEventType.TOOL_ERROR,
                    tool=func_name,
                    tool_call_id=tool_call_id,
                    duration_ms=duration_ms,
                    error=error_message,
                )

            # Archive the tool call execution with complete forensic data
            try:
                analytics = _get_analytics()
                # Sanitize params to remove non-serializable objects (asyncio.Future, etc.)
                sanitized_params = self._sanitize_for_serialization(dict(params))
                sanitized_result = self._sanitize_for_serialization(
                    result if isinstance(result, (str, dict, list)) else str(result)
                )
                
                # Extract complete tool definition for forensic audit trail
                # This is the exact tool schema that was sent to the LLM model
                tool_definition = self._get_tool_definition(func_name)
                
                # Extract logs from ToolResponse if present
                tool_logs = []
                if isinstance(result, ToolResponse) and result.logs:
                    tool_logs = result.logs
                
                analytics.record_tool_call_message(
                    message_id=str(uuid.uuid4()),
                    chat_id=chat_id or "",
                    tool_call_id=tool_call_id or "",
                    tool_name=func_name,
                    username=self.user.username if self.user else "anonymous",
                    project_name=self.settings.project_name or "",
                    project_id=getattr(self.settings, "project_id", "") or "",
                    request_args=sanitized_params,  # Complete parsed arguments
                    result=sanitized_result,  # Complete execution result
                    result_sent_to_model=_normalise_tool_result(result, func_name),  # What model saw
                    success=success,
                    error_message=error_message,
                    duration_seconds=duration_seconds,
                    cached=False,
                    tool_definition=tool_definition,  # FORENSIC: Complete tool schema
                    tool_logs=tool_logs,  # FORENSIC: Tool execution logs
                )
            except OSError as ex:
                logger.warning("SmolAgent: failed to archive tool call message: %s", ex)

            self._record_tool_usage(
                tool_name=func_name,
                time_taken=duration_seconds,
                success=success,
                error_message=error_message,
                chat_id=chat_id,
                request_id=request_id,
            )

    # ── Tool usage summary (generated only when the tool loop breaks) ──────────

    @staticmethod
    def _collect_tool_usage(
        openai_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Extract the tool calls executed during this run and their results.

        Only messages produced by this run are present in *openai_messages*
        (the original conversation carries no tool messages), so every
        ``assistant.tool_calls`` / ``tool`` pair gathered here belongs to the
        current run, whether it was executed or served from the cache.

        Args:
            openai_messages: Current OpenAI-format conversation history.

        Returns:
            List of ``{"name", "args", "result"}`` dicts in execution order.
        """
        pending: Dict[Optional[str], Dict[str, str]] = {}
        usages: List[Dict[str, str]] = []

        for msg in openai_messages:
            role = msg.get("role")
            if role == "assistant" and msg.get("tool_calls"):
                for call in msg["tool_calls"]:
                    fn = call.get("function") or {}
                    pending[call.get("id")] = {
                        "name": fn.get("name", ""),
                        "args": fn.get("arguments", ""),
                    }
            elif role == "tool":
                info = pending.pop(msg.get("tool_call_id"), None)
                if info is not None:
                    info["result"] = msg.get("content", "")
                    usages.append(info)

        return usages

    def _build_tool_usage_prompt(
        self,
        openai_messages: List[Dict[str, Any]],
        tool_usages: List[Dict[str, str]],
        loop_error: str,
    ) -> str:
        """
        Build the user prompt for the tool usage summary request.

        Includes the original request, why the run stopped, and a truncated
        listing of the executed tools with their results.

        Args:
            openai_messages: Current OpenAI-format conversation history.
            tool_usages:     Collected tool usages (see :meth:`_collect_tool_usage`).
            loop_error:      The LoopGuard message that stopped the run.

        Returns:
            The prompt content for the summary request.
        """
        task = ""
        for msg in openai_messages:
            content = msg.get("content")
            if msg.get("role") == "user" and isinstance(content, str) and content.strip():
                task = content.strip()[:TOOL_ANALYSIS_TASK_MAX_CHARS]
                break

        lines: List[str] = []
        for idx, usage in enumerate(tool_usages, start=1):
            result = (usage.get("result") or "")[:TOOL_ANALYSIS_RESULT_MAX_CHARS]
            lines.append(
                f"{idx}. {usage['name']}({usage['args']})\n   -> {result}"
            )
        tools_block = "\n".join(lines) if lines else "(no tools were executed)"

        return (
            "## User request\n"
            f"{task}\n\n"
            "## Why the run stopped\n"
            f"{loop_error}\n\n"
            "## Tools executed this run (name, arguments, result)\n"
            f"{tools_block}\n\n"
            "Write the summary now, following the system instructions."
        )

    @staticmethod
    def _tool_usage_fallback(tool_usages: List[Dict[str, str]]) -> str:
        """
        Build the deterministic fallback used when no model summary is available.

        Still lists the tools already executed so the next iteration is never
        worse off than before this feature existed.

        Args:
            tool_usages: Collected tool usages.

        Returns:
            Markdown fallback block (without the heading).
        """
        lines: List[str] = ["", TOOL_ANALYSIS_FALLBACK_NOTE, ""]
        for usage in tool_usages:
            lines.append(f"- `{usage['name']}({usage['args']})`")
        return "\n".join(lines)

    def _summarize_tool_usage(
        self,
        openai_messages: List[Dict[str, Any]],
        loop_error: str,
        chat_id: Optional[str],
        session_id: Optional[str],
    ) -> str:
        """
        Produce a Markdown summary of the value of the tools used this run.

        Runs a single best-effort request against the project's knowledge/RAG
        model (``settings.get_rag_model()``) — intended for this kind of
        lightweight analysis and typically smaller/cheaper than the chat model.

        The request does NOT count towards the loop limits and its token usage
        is recorded separately with the ``tool-analysis`` tag. Any failure is
        swallowed and a deterministic fallback is returned instead, so this can
        never turn a graceful stop into a hard error.

        Args:
            openai_messages: Current OpenAI-format conversation history.
            loop_error:      The LoopGuard message that stopped the run.
            chat_id:         Chat identifier for analytics.
            session_id:      Session identifier for analytics.

        Returns:
            A ready-to-append Markdown block (heading included), or an empty
            string when there is nothing to report.
        """
        heading = f"\n\n---\n\n{TOOL_ANALYSIS_HEADING}\n\n"
        tool_usages = self._collect_tool_usage(openai_messages)

        # Resolve the knowledge/RAG model dedicated to analysis-type tasks.
        try:
            rag_model = self.settings.get_rag_model()
            rag_settings = self.settings.get_llm_settings(llm_model=rag_model)
        except Exception as ex:
            logger.warning(
                "SmolAgent: tool usage summary skipped, cannot resolve "
                "analysis model: %s",
                ex,
            )
            return heading + self._tool_usage_fallback(tool_usages) + "\n"

        # Nothing was executed (e.g. the breadth guard tripped on round 1):
        # emit only the deterministic fallback.
        if not tool_usages:
            return heading + self._tool_usage_fallback(tool_usages) + "\n"

        prompt = self._build_tool_usage_prompt(
            openai_messages=openai_messages,
            tool_usages=tool_usages,
            loop_error=loop_error,
        )

        try:
            client = OpenAI(
                api_key=rag_settings.api_key,
                base_url=rag_settings.api_url,
            )
            analysis_start = time.monotonic()
            response = client.chat.completions.create(
                model=rag_settings.model,
                stream=False,
                temperature=0,
                max_tokens=TOOL_ANALYSIS_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": TOOL_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            summary = (response.choices[0].message.content or "").strip()

            self._record_tool_analysis_usage(
                rag_settings=rag_settings,
                usage=getattr(response, "usage", None),
                duration_seconds=time.monotonic() - analysis_start,
                chat_id=chat_id,
                session_id=session_id,
            )

            if summary:
                return f"{heading}{summary}\n"
            return heading + self._tool_usage_fallback(tool_usages) + "\n"
        except Exception as ex:
            logger.warning(
                "SmolAgent: tool usage summary failed (non-fatal): %s", ex
            )
            return heading + self._tool_usage_fallback(tool_usages) + "\n"

    def _record_tool_analysis_usage(
        self,
        rag_settings: Any,
        usage: Any,
        duration_seconds: float,
        chat_id: Optional[str],
        session_id: Optional[str],
    ) -> None:
        """
        Record token usage of the tool usage summary request (non-fatal).

        Tagged with ``tool-analysis`` and attributed to the analysis model so
        its cost is visible but separable from the main chat run.

        Args:
            rag_settings:    Resolved AISettings of the analysis model.
            usage:           Provider-reported usage (may be ``None``).
            duration_seconds: Wall-clock duration of the request.
            chat_id:         Chat identifier.
            session_id:      Session identifier.
        """
        try:
            input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage, "completion_tokens", 0) or 0
            if not input_tokens and not output_tokens:
                return

            _get_analytics().record_token_usage(
                username=self.user.username if self.user else "anonymous",
                project_name=self.settings.project_name or "",
                project_id=getattr(self.settings, "project_id", "") or "",
                model=rag_settings.model,
                provider=rag_settings.provider or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_seconds=duration_seconds,
                session_id=session_id,
                tags=TOOL_ANALYSIS_TAG,
                input_k_tokens_cxjcoins=getattr(
                    rag_settings, "input_k_tokens_cxjcoins", 0.0
                ) or 0.0,
                output_k_tokens_cxjcoins=getattr(
                    rag_settings, "output_k_tokens_cxjcoins", 0.0
                ) or 0.0,
                request_id=None,
                chat_id=chat_id,
                tokens_from_provider=True,
            )
        except Exception as ex:
            logger.warning(
                "SmolAgent: failed to record tool analysis usage (non-fatal): %s",
                ex,
            )

    # ── Cost tracking (Chat.estimation_cost) ───────────────────────────────────

    @staticmethod
    def _accumulated_chat_cost(current_chat: Optional[Any]) -> float:
        """
        Return the accumulated cost of the chat in cxjcoins.

        Prefers ``Chat.cost`` — the deletion-safe accumulator maintained by
        ``ChatManager`` (it is NOT reduced when messages are deleted). Falls
        back to summing the cost registered on the chat's messages for chats
        persisted before the accumulator existed.

        Args:
            current_chat: The Chat object in context (may be ``None``).

        Returns:
            Total cost in cxjcoins accumulated so far (0.0 when unknown).
        """
        if not current_chat:
            return 0.0

        accumulated = getattr(current_chat, "cost", None)
        if accumulated is not None and accumulated > 0:
            return float(accumulated)

        return sum(
            getattr(message, "cost", 0.0) or 0.0
            for message in (getattr(current_chat, "messages", None) or [])
        )

    @staticmethod
    def _tool_cost(tool_result: Any) -> float:
        """
        Return the cost in cxjcoins reported by a tool result.

        Tools that perform their own AI calls (or otherwise incur cost) can
        report it on the :class:`ToolResponse` ``cost`` field. The cost is
        summed into the iteration total (billed on the returned message) and
        the chat total (used to enforce ``Chat.estimation_cost``).

        Args:
            tool_result: The value returned by a tool (str, ToolResponse, ...).

        Returns:
            The reported cost in cxjcoins (0.0 when not a ToolResponse or unset).
        """
        if isinstance(tool_result, ToolResponse):
            try:
                return float(getattr(tool_result, "cost", 0.0) or 0.0)
            except (TypeError, ValueError):
                logger.warning(
                    "SmolAgent: ignoring invalid ToolResponse.cost value: %r",
                    getattr(tool_result, "cost", None),
                )
                return 0.0
        return 0.0

    def _compute_cost(
        self,
        usage_info: Any,
        content: str,
        openai_messages: List[Dict[str, Any]],
    ) -> RoundCost:
        """
        Compute the token usage and cost in cxjcoins of a single completion round.

        Uses the provider-reported usage when available, falling back to a
        token-count estimate otherwise. Only the input/output token prices of
        the active model (``AISettings``) are used, matching the pricing model
        used by the analytics subsystem.

        Args:
            usage_info:      Provider-reported usage for this round (may be ``None``).
            content:         Text generated in this round (for output fallback).
            openai_messages: Conversation history sent in this round (for input fallback).

        Returns:
            A :class:`RoundCost` with tokens and input/output costs in cxjcoins
            (zeroed when no pricing is configured).
        """
        input_price = getattr(self.llm_settings, "input_k_tokens_cxjcoins", 0.0) or 0.0
        output_price = getattr(self.llm_settings, "output_k_tokens_cxjcoins", 0.0) or 0.0
        if not input_price and not output_price:
            return RoundCost()

        input_tokens = getattr(usage_info, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage_info, "completion_tokens", 0) or 0

        if not input_tokens:
            input_text = "\n".join(
                m.get("content", "")
                for m in openai_messages
                if isinstance(m.get("content"), str)
            )
            input_tokens = count_tokens(input_text, model=self.model)
        if not output_tokens and content:
            output_tokens = count_tokens(content, model=self.model)

        return RoundCost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_cxjcoins=(input_tokens / 1000.0) * input_price,
            output_cost_cxjcoins=(output_tokens / 1000.0) * output_price,
        )

    @staticmethod
    def _cost_limit_exceeded(
        current_chat: Optional[Any],
        chat_cost: float,
    ) -> bool:
        """
        Return True when the accumulated chat cost reached ``estimation_cost``.

        A limit is enforced only when ``Chat.estimation_cost`` is set to a
        positive value; ``None`` or non-positive values disable the limit.

        Args:
            current_chat: The Chat object in context (may be ``None``).
            chat_cost:    Accumulated chat cost in cxjcoins.

        Returns:
            True when the chat budget has been reached or exceeded.
        """
        if not current_chat:
            return False
        limit = getattr(current_chat, "estimation_cost", None)
        if limit is None or limit <= 0:
            return False
        return chat_cost >= limit

    @staticmethod
    def _parse_tool_arguments(raw_arguments: Any, func_name: str) -> Dict[str, Any]:
        """
        Parse tool arguments that may arrive as a JSON string or a dict.

        Handles all edge cases from streaming delta accumulation:
        - ``dict``   → returned as-is (already parsed)
        - ``str``    → JSON-decoded; empty string treated as ``{}``
        - ``None``   → treated as ``{}`` (key present but value is None)
        - anything else → logged and treated as ``{}``

        Args:
            raw_arguments: The raw arguments payload (may be None from streaming).
            func_name:     Tool name (for logging).

        Returns:
            A dict of parsed arguments (empty on parse failure or missing args).
        """
        # Already a dict — return as-is
        if isinstance(raw_arguments, dict):
            return raw_arguments

        # None means the streaming accumulator never received an arguments chunk
        if raw_arguments is None:
            logger.warning(
                "SmolAgent: tool '%s' received None arguments – treating as {}",
                func_name,
            )
            return {}

        if isinstance(raw_arguments, str):
            # Empty or whitespace-only string: no arguments provided
            stripped = raw_arguments.strip()
            if not stripped:
                logger.warning(
                    "SmolAgent: tool '%s' received empty arguments string – treating as {}",
                    func_name,
                )
                return {}
            try:
                parsed = json.loads(stripped)
                if not isinstance(parsed, dict):
                    logger.error(
                        "SmolAgent: tool '%s' arguments parsed to non-dict type %s "
                        "(raw=%r) – treating as {}",
                        func_name,
                        type(parsed).__name__,
                        stripped[:200],
                    )
                    return {}
                logger.debug(
                    "SmolAgent: tool '%s' arguments parsed successfully: keys=%s",
                    func_name,
                    list(parsed.keys()),
                )
                return parsed
            except json.JSONDecodeError as ex:
                logger.error(
                    "SmolAgent: cannot parse arguments for tool '%s': %s "
                    "(raw=%r)",
                    func_name,
                    ex,
                    stripped[:200],
                )
                return {}

        # Unexpected type — log and return empty
        logger.error(
            "SmolAgent: tool '%s' received unexpected arguments type %s "
            "(value=%r) – treating as {}",
            func_name,
            type(raw_arguments).__name__,
            str(raw_arguments)[:200],
        )
        return {}

    @staticmethod
    def _sanitize_for_serialization(obj: Any) -> Any:
        """
        Recursively sanitize an object to remove non-serializable items
        (e.g., asyncio.Future, coroutines, Pydantic models).

        Args:
            obj: Object to sanitize.

        Returns:
            Serialization-safe version of the object.
        """
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        if isinstance(obj, Future):
            return f"<{type(obj).__name__}>"

        if inspect.iscoroutine(obj):
            return f"<{type(obj).__name__}>"

        if hasattr(obj, 'model_dump'):
            # Pydantic model
            try:
                return SmolAgent._sanitize_for_serialization(obj.model_dump())
            except Exception:
                return str(obj)

        if isinstance(obj, dict):
            return {
                SmolAgent._sanitize_for_serialization(k): SmolAgent._sanitize_for_serialization(v)
                for k, v in obj.items()
            }

        if isinstance(obj, (list, tuple)):
            return [SmolAgent._sanitize_for_serialization(item) for item in obj]

        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)

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

        The argument passed to ``send_callback`` is treated as a **delta**
        (a new chunk). It is appended to the internal buffer/accumulator and
        the FULL accumulated response is emitted on flush. Callers MUST NOT
        pass content that has already been sent — doing so would re-emit it.

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
        thinking_text: str,
        duration_seconds: float,
        tags: str,
        session_id: Optional[str],
        request_id: Optional[str],
        usage_info: Any,
        chat_id: Optional[str],
        tool_cache: Optional[ToolCache] = None,
    ) -> None:
        """
        Record token usage to analytics (non-fatal on error).

        Includes tool cache statistics in analytics for visibility into
        cache performance. Usage is calculated based on both thinking
        and final answer content produced by the model.

        Args:
            openai_messages:  Full conversation sent to the model.
            output_text:      Final answer content (the final response).
            thinking_text:    Thinking content (tool-calling rounds text).
            duration_seconds: Total wall-clock duration.
            tags:             Analytics tag string.
            session_id:       Session identifier.
            request_id:       Last request identifier.
            usage_info:       Provider-reported token usage (may be ``None``).
            chat_id:          Chat identifier.
            tool_cache:       Tool cache for this conversation (optional).
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
                # Count tokens for both thinking and final answer content
                combined_output = thinking_text + output_text
                output_tokens = count_tokens(combined_output, model=self.model)

            # Augment tags with cache statistics if available
            cache_tags = tags
            if tool_cache:
                cache_stats = tool_cache.stats()
                cache_tags += (
                    f",cache_hits:{cache_stats['hits']},"
                    f"cache_misses:{cache_stats['misses']},"
                    f"cache_hit_rate:{cache_stats['hit_rate']}"
                )

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
                tags=cache_tags,
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