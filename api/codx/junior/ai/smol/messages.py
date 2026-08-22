"""
Message helpers for SmolAgent.

Converts LangChain messages to the OpenAI Chat Completions format and builds
the assistant/tool messages required by the tool-calling protocol. Also
provides :class:`ToolCallAccumulator` to stitch together streaming tool-call
fragments.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Union

from langchain.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)


def to_openai_message(message: Union[AIMessage, HumanMessage]) -> Dict[str, Any]:
    """
    Convert a single LangChain message to an OpenAI message dict.

    Args:
        message: A LangChain :class:`AIMessage` or :class:`HumanMessage`.

    Returns:
        A dict with ``role`` and ``content`` keys suitable for the OpenAI API.

    Raises:
        json.JSONDecodeError: If an image message contains invalid JSON.
    """
    if message.type == "image":
        return {"role": "user", "content": json.loads(message.content)}
    return {
        "role": "assistant" if message.type == "ai" else "user",
        "content": message.content,
    }


def to_openai_messages(
    messages: List[Union[AIMessage, HumanMessage]],
    system: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convert a LangChain message list to the OpenAI format, prepending the
    system prompt when provided.

    Args:
        messages: Conversation history as LangChain messages.
        system:   Optional system prompt content.

    Returns:
        List of OpenAI-compatible message dicts.
    """
    openai_messages = [to_openai_message(msg) for msg in messages]
    if system and system.strip():
        openai_messages = [{"role": "system", "content": system.strip()}] + openai_messages
    return openai_messages


def make_tool_message(tool_call_id: str, content: Any) -> Dict[str, Any]:
    """
    Build an OpenAI ``role=tool`` result message.

    Every tool invocation listed in the assistant's ``tool_calls`` array must
    be answered by a matching ``role="tool"`` message, otherwise the next
    completion request is rejected by the API.

    Args:
        tool_call_id: The ``id`` from the assistant's tool_call entry.
        content:      Result returned by the tool (serialised if not a string).

    Returns:
        A dict ready to be appended to the OpenAI messages list.
    """
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content if isinstance(content, str) else json.dumps(content),
    }


def make_assistant_tool_calls_message(
    tool_calls: Dict[str, Dict[str, Any]],
    content: str = "",
) -> Dict[str, Any]:
    """
    Build the assistant message that records which tools were requested.

    Args:
        tool_calls: Mapping of tool_call_id → {id, function, arguments}.
        content:    Any partial text content generated before the tool calls.

    Returns:
        A dict with ``role="assistant"`` and a ``tool_calls`` list.
    """
    payload: List[Dict[str, Any]] = []
    for tool_call in tool_calls.values():
        arguments = tool_call.get("arguments", "")
        if isinstance(arguments, dict):
            arguments = json.dumps(arguments)
        payload.append({
            "id": tool_call["id"],
            "type": "function",
            "function": {
                "name": tool_call["function"],
                "arguments": arguments,
            },
        })
    return {"role": "assistant", "content": content or "", "tool_calls": payload}


class ToolCallAccumulator:
    """
    Stitch together streaming tool-call fragments.

    The OpenAI streaming API sends tool-call data fragmented across chunks:
    the first chunk for a tool provides ``id`` and ``function.name``,
    subsequent chunks append ``function.arguments`` characters.
    """

    def __init__(self) -> None:
        """Initialise an empty accumulator."""
        self.tool_calls: Dict[str, Dict[str, Any]] = {}
        self._last_tool_id: Optional[str] = None

    def add(self, tool_calls_delta: List[Any]) -> None:
        """
        Merge a list of streaming tool-call delta objects into the accumulator.

        Args:
            tool_calls_delta: List of delta tool-call objects from a chunk.
        """
        for delta in tool_calls_delta:
            if delta.id and delta.id not in self.tool_calls:
                self.tool_calls[delta.id] = {
                    "id": delta.id,
                    "function": "",
                    "arguments": "",
                }
            active_id = delta.id or self._last_tool_id
            if not active_id or active_id not in self.tool_calls:
                logger.warning("ToolCallAccumulator: cannot resolve tool id, skipping delta")
                continue
            if delta.id:
                self._last_tool_id = delta.id
            if delta.function and delta.function.name:
                self.tool_calls[active_id]["function"] += delta.function.name
            if delta.function and delta.function.arguments:
                self.tool_calls[active_id]["arguments"] += delta.function.arguments

    def has_calls(self) -> bool:
        """Return ``True`` when at least one tool call has been accumulated."""
        return bool(self.tool_calls)

# Made with ❤️ by codx-junior