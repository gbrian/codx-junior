"""
ChatEventBridge — translates AgentRunContext events into chat messages.

During an AI turn the SmolAgent emits :class:`engine.agent_runtime.AgentEvent`
notifications (tool start/end/error, LLM requests, usage, run lifecycle).
This bridge converts those events into ``role="tool"`` chat messages that are:

    * appended to the in-memory :class:`codx.junior.db.Chat` (shared reference),
    * persisted immediately via :class:`codx.junior.chat_manager.ChatManager`
      granular merge-safe methods (crash-safe),
    * streamed to clients in real time via the EventManager.

Event details are stored in the **typed** message properties:

    * ``message.tool_event``      → :class:`codx.junior.db.ToolEvent`
    * ``message.lifecycle_event`` → :class:`codx.junior.db.LifeCycleEvent`

``meta_data`` is only used for supplementary information not covered by the
typed models (e.g. ``run_id`` on tool messages, aggregated ``analytics`` and
``events`` count on lifecycle messages).

Tool messages are updated **in place** (one message per tool call:
running → done/error). All run-lifecycle events share a single message per
run, also updated in place, to avoid flooding the chat timeline.

    ```mermaid
    sequenceDiagram
        participant SmolAgent
        participant Bridge as ChatEventBridge
        participant ChatManager
        participant EventManager

        SmolAgent->>Bridge: TOOL_START (tool_call_id, tool, args)
        Bridge->>Bridge: create Message(role=tool, tool_event.status=running)
        Bridge->>ChatManager: add_message (persist)
        Bridge->>EventManager: message_event (stream)
        SmolAgent->>Bridge: TOOL_END (tool_call_id, duration, result)
        Bridge->>Bridge: update SAME message (tool_event.status=done, response)
        Bridge->>ChatManager: update_message (persist)
        Bridge->>EventManager: message_event (stream)
    ```
"""
import logging
import uuid
from typing import Dict, List, Optional

from engine.agent_runtime import AgentEvent, AgentEventType

from codx.junior.db import (
    Chat,
    LifeCycleEvent,
    Message,
    ROLE_TOOL,
    ToolEvent,
)

logger = logging.getLogger(__name__)

# Maximum characters of a tool response stored in the message tool_event/content.
TOOL_RESPONSE_MAX_CHARS: int = 4000

# Shared status values for ToolEvent / LifeCycleEvent
STATUS_RUNNING: str = "running"
STATUS_DONE: str = "done"
STATUS_ERROR: str = "error"

# Lifecycle events surfaced to the user (LLM_CHUNK is intentionally excluded:
# streaming previews are already handled by the response message callbacks).
LIFECYCLE_EVENT_TYPES = {
    AgentEventType.RUN_START,
    AgentEventType.RUN_END,
    AgentEventType.RUN_ERROR,
    AgentEventType.RUN_CANCELLED,
    AgentEventType.LLM_REQUEST,
    AgentEventType.LLM_USAGE,
    AgentEventType.WALLET_CHECK,
}


def _truncate(text: str, max_chars: int = TOOL_RESPONSE_MAX_CHARS) -> str:
    """
    Truncate *text* to *max_chars*, appending an ellipsis marker when cut.

    :param text: The text to truncate.
    :param max_chars: Maximum number of characters to keep.
    :return: The (possibly truncated) text.
    """
    if text and len(text) > max_chars:
        return text[:max_chars] + "\n… (truncated)"
    return text or ""


class ChatEventBridge:
    """
    Bridges agent runtime events into persisted + streamed chat messages.

    The bridge is registered as a listener on an
    :class:`engine.agent_runtime.AgentRunContext` and must **never raise**:
    any persistence/streaming failure is logged and swallowed so a broken
    notification can never kill the AI run.
    """

    def __init__(self, chat: Chat, chat_manager, event_manager) -> None:
        """
        :param chat: The in-memory chat being processed (mutated in place).
        :param chat_manager: ChatManager providing add_message/update_message.
        :param event_manager: EventManager used to stream message events.
        """
        self.chat: Chat = chat
        self.chat_manager = chat_manager
        self.event_manager = event_manager
        # tool_call_id (or tool name fallback) -> in-place updated Message
        self._tool_messages: Dict[str, Message] = {}
        # Single lifecycle message per run, updated in place
        self._lifecycle_message: Optional[Message] = None
        self._lifecycle_lines: List[str] = []

    # ── Event entry point ──────────────────────────────────────────────────────

    def on_event(self, event: AgentEvent) -> None:
        """
        Handle an :class:`AgentEvent` emitted by the agent run context.

        :param event: The emitted event.
        """
        try:
            if event.type == AgentEventType.TOOL_START:
                self._on_tool_start(event)
            elif event.type == AgentEventType.TOOL_END:
                self._on_tool_finished(event, error=False)
            elif event.type == AgentEventType.TOOL_ERROR:
                self._on_tool_finished(event, error=True)
            elif event.type in LIFECYCLE_EVENT_TYPES:
                self._on_lifecycle(event)
        except (OSError, ValueError, TypeError, RuntimeError) as ex:
            # A broken notification must NEVER kill the AI run.
            logger.exception(
                "ChatEventBridge: failed handling event '%s' for chat '%s': %s",
                event.type,
                self.chat.id,
                ex,
            )

    # ── Tool events ────────────────────────────────────────────────────────────

    @staticmethod
    def _tool_key(event: AgentEvent) -> str:
        """Return the lookup key for the tool message of *event*."""
        return str(event.payload.get("tool_call_id") or event.payload.get("tool") or "")

    @staticmethod
    def _make_tool_event(event: AgentEvent, status: str) -> ToolEvent:
        """
        Build a :class:`ToolEvent` from an agent *event* payload.

        :param event: The TOOL_* agent event.
        :param status: Initial status ('running', 'done', or 'error').
        :return: A populated ToolEvent instance.
        """
        payload = event.payload
        return ToolEvent(
            tool=payload.get("tool", "unknown"),
            tool_call_id=str(payload.get("tool_call_id") or ""),
            status=status,
            request=payload.get("args") or {},
        )

    def _on_tool_start(self, event: AgentEvent) -> None:
        """Create a new visible tool message in 'running' state."""
        payload = event.payload
        tool_name = payload.get("tool", "unknown")
        message = Message(
            doc_id=str(uuid.uuid4()),
            role=ROLE_TOOL,
            content=f"🔧 Running tool **{tool_name}**...",
            done=False,
            tool_event=self._make_tool_event(event, status=STATUS_RUNNING),
            # run_id is not part of ToolEvent: keep it as supplementary metadata
            meta_data={"run_id": event.run_id},
        )
        self._tool_messages[self._tool_key(event)] = message
        logger.info(
            "ChatEventBridge: tool '%s' started (chat='%s', run='%s')",
            tool_name,
            self.chat.id,
            event.run_id,
        )
        self._publish(message, is_new=True)

    def _on_tool_finished(self, event: AgentEvent, error: bool) -> None:
        """Update the tool message's ToolEvent in place with the final result / error."""
        payload = event.payload
        tool_name = payload.get("tool", "unknown")
        duration_ms = payload.get("duration_ms", 0.0) or 0.0
        message = self._tool_messages.get(self._tool_key(event))
        is_new = message is None
        if is_new:
            # Defensive: TOOL_END without a matching TOOL_START
            message = Message(
                doc_id=str(uuid.uuid4()),
                role=ROLE_TOOL,
                tool_event=self._make_tool_event(event, status=STATUS_RUNNING),
                meta_data={"run_id": event.run_id},
            )
            self._tool_messages[self._tool_key(event)] = message

        tool_event = message.tool_event
        if tool_event is None:
            # Defensive: message existed without a typed tool_event
            tool_event = self._make_tool_event(event, status=STATUS_RUNNING)
            message.tool_event = tool_event

        tool_event.duration_ms = duration_ms

        if error:
            error_text = str(payload.get("error") or "unknown error")
            tool_event.status = STATUS_ERROR
            tool_event.error = error_text
            message.content = (
                f"❌ Tool **{tool_name}** failed after {duration_ms:.0f} ms\n\n"
                f"{_truncate(error_text)}"
            )
            message.error = error_text
        else:
            response_preview = _truncate(str(payload.get("result") or ""))
            tool_event.status = STATUS_DONE
            tool_event.response = response_preview
            message.content = (
                f"🔧 Tool **{tool_name}** finished in {duration_ms:.0f} ms\n\n"
                f"**Response:**\n\n{response_preview}"
            )

        message.done = True
        logger.info(
            "ChatEventBridge: tool '%s' %s in %.0f ms (chat='%s')",
            tool_name,
            STATUS_ERROR if error else STATUS_DONE,
            duration_ms,
            self.chat.id,
        )
        self._publish(message, is_new=is_new)

    # ── Lifecycle events ───────────────────────────────────────────────────────

    def _lifecycle_line(self, event: AgentEvent) -> Optional[str]:
        """
        Build the user-friendly summary line for a lifecycle *event*.

        :param event: The lifecycle event.
        :return: A markdown line, or None if the event should be skipped.
        """
        payload = event.payload
        if event.type == AgentEventType.RUN_START:
            return f"▶️ Run `{event.run_id}` started"
        if event.type == AgentEventType.LLM_REQUEST:
            return (
                f"🤖 Calling model **{payload.get('model', '?')}** "
                f"({payload.get('message_count', 0)} messages)"
            )
        if event.type == AgentEventType.LLM_USAGE:
            return (
                f"📊 Tokens — prompt: {payload.get('prompt_tokens', 0)}, "
                f"completion: {payload.get('completion_tokens', 0)}"
            )
        if event.type == AgentEventType.WALLET_CHECK:
            return f"💰 Wallet check — balance: {payload.get('balance', 0)}"
        if event.type == AgentEventType.RUN_END:
            return "✅ Run finished"
        if event.type == AgentEventType.RUN_CANCELLED:
            return f"🛑 Run cancelled: {payload.get('reason', 'user_requested')}"
        if event.type == AgentEventType.RUN_ERROR:
            return f"❌ Run error: {_truncate(str(payload.get('error', '')), 500)}"
        return None

    def _on_lifecycle(self, event: AgentEvent) -> None:
        """Append the event to the single, in-place-updated lifecycle message."""
        line = self._lifecycle_line(event)
        if not line:
            return
        self._lifecycle_lines.append(line)

        is_new = self._lifecycle_message is None
        if is_new:
            self._lifecycle_message = Message(
                doc_id=str(uuid.uuid4()),
                role=ROLE_TOOL,
                lifecycle_event=LifeCycleEvent(
                    status=STATUS_RUNNING,
                    run_id=event.run_id,
                ),
                # Supplementary data not covered by LifeCycleEvent
                meta_data={},
            )

        message = self._lifecycle_message
        lifecycle_event = message.lifecycle_event
        if lifecycle_event is None:
            # Defensive: message existed without a typed lifecycle_event
            lifecycle_event = LifeCycleEvent(
                status=STATUS_RUNNING,
                run_id=event.run_id,
            )
            message.lifecycle_event = lifecycle_event

        payload = event.payload
        meta = dict(message.meta_data or {})
        meta["events"] = len(self._lifecycle_lines)

        if event.type == AgentEventType.RUN_END:
            lifecycle_event.status = STATUS_DONE
            lifecycle_event.duration_ms = payload.get("duration_ms")
            meta["analytics"] = payload.get("analytics")
            message.done = True
        elif event.type in (AgentEventType.RUN_ERROR, AgentEventType.RUN_CANCELLED):
            lifecycle_event.status = STATUS_ERROR
            lifecycle_event.duration_ms = payload.get("duration_ms")
            lifecycle_event.error = str(
                payload.get("error") or payload.get("reason") or "unknown error"
            )
            meta["analytics"] = payload.get("analytics")
            message.done = True
        else:
            message.done = False

        message.meta_data = meta
        message.content = "\n\n".join(self._lifecycle_lines)
        self._publish(message, is_new=is_new)

    # ── Persist + stream ───────────────────────────────────────────────────────

    def _publish(self, message: Message, is_new: bool) -> None:
        """
        Persist the message change (crash-safe) and stream it to clients.

        :param message: The message to persist and stream.
        :param is_new: True when the message was just created.
        """
        try:
            if is_new:
                self.chat_manager.add_message(chat=self.chat, message=message)
            else:
                self.chat_manager.update_message(chat=self.chat, message=message)
        except (OSError, ValueError, TypeError, RuntimeError) as ex:
            logger.exception(
                "ChatEventBridge: error persisting message '%s' for chat '%s': %s",
                message.doc_id,
                self.chat.id,
                ex,
            )
        try:
            self.event_manager.message_event(chat=self.chat, message=message)
        except (OSError, ValueError, TypeError, RuntimeError) as ex:
            logger.exception(
                "ChatEventBridge: error streaming message '%s' for chat '%s': %s",
                message.doc_id,
                self.chat.id,
                ex,
            )

# Made with ❤️ by codx-junior