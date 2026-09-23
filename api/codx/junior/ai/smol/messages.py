"""
Message handling utilities for SmolAgent.

Converts LangChain messages to OpenAI format, manages tool call accumulation,
and constructs tool/assistant messages for the iterative tool loop.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Union

from langchain.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)


def to_openai_message(message: Union[Dict[str, Any], HumanMessage, AIMessage]) -> Dict[str, Any]:
    """
    Convert a LangChain or dict message to OpenAI format.

    Handles three input types:
    1. HumanMessage / AIMessage: extracted role + content
    2. Dict with "type": "image": image attachment with JSON-parsed content
    3. Dict with "role": regular OpenAI format (pass-through with safety check)

    Content parsing rules:
    - If content is a JSON string (starts with '[' or '{'), parse it
    - If content is a plain string, keep as-is
    - If content is already a list/dict, keep as-is

    Args:
        message: LangChain or dict message object.

    Returns:
        OpenAI-compatible message dict.

    Raises:
        JSONDecodeError: If content is malformed JSON (rare, defensive check).
    """
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}

    if isinstance(message, AIMessage):
        return {"role": "assistant", "content": message.content}

    if isinstance(message, dict):
        if message.get("type") == "image":
            # Image message with JSON-stringified content array
            content = message.get("content", "[]")
            try:
                # Try to parse if it's a JSON string
                if isinstance(content, str) and content.strip().startswith(("[", "{")):
                    return {"role": "user", "content": json.loads(content)}
                else:
                    # Plain string or already parsed — keep as-is
                    return {"role": "user", "content": content}
            except json.JSONDecodeError as ex:
                logger.error(
                    "to_openai_message: failed to parse image content as JSON: %s",
                    ex
                )
                raise

        # Regular message dict with role
        content = message.get("content")
        role = message.get("role", "user")
        
        # Safely parse content only if it's a JSON string
        if isinstance(content, str) and content.strip().startswith(("[", "{")):
            try:
                return {"role": role, "content": json.loads(content)}
            except json.JSONDecodeError as ex:
                logger.warning(
                    "to_openai_message: content appears to be JSON but parse failed; "
                    "treating as plain string. Error: %s, Content: %s",
                    ex, content[:100]
                )
                return {"role": role, "content": content}
        else:
            # Plain string or already a list/dict — keep as-is
            return {"role": role, "content": content}

    # Fallback for unexpected types
    logger.warning(
        "to_openai_message: unexpected message type %s, converting to string",
        type(message).__name__
    )
    return {"role": "user", "content": str(message)}


def to_openai_messages(
    messages: List[Union[Dict[str, Any], HumanMessage, AIMessage]],
    system: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convert a list of LangChain or dict messages to OpenAI format.

    Optionally prepends a system message if provided.

    Args:
        messages: List of message objects (LangChain or dict).
        system:   Optional system prompt to prepend.

    Returns:
        List of OpenAI-compatible message dicts.
    """
    openai_messages: List[Dict[str, Any]] = []

    if system:
        openai_messages.append({"role": "system", "content": system})

    openai_messages = openai_messages + [to_openai_message(msg) for msg in messages]

    return openai_messages


class ToolCallAccumulator:
    """Accumulates and manages tool calls from streamed chunks."""

    def __init__(self) -> None:
        """Initialize the accumulator with empty tool calls dict."""
        self.tool_calls: Dict[str, Dict[str, Any]] = {}

    def add(self, deltas: List) -> None:
        """
        Accumulate tool call deltas from streaming chunks.
        
        Handles both dict and Pydantic model formats by converting to dict.
        """
        if not deltas:
            return
        
        for delta in deltas:
            # Convert Pydantic model to dict if needed
            if hasattr(delta, 'model_dump'):
                # Pydantic v2
                delta_dict = delta.model_dump(exclude_unset=True)
            elif hasattr(delta, 'dict'):
                # Pydantic v1
                delta_dict = delta.dict(exclude_unset=True)
            elif isinstance(delta, dict):
                delta_dict = delta
            else:
                # Fallback: try to extract as dict
                delta_dict = {
                    'id': getattr(delta, 'id', None),
                    'type': getattr(delta, 'type', 'function'),
                    'function': getattr(delta, 'function', None),
                }
            
            call_id = delta_dict.get("id")
            call_type = delta_dict.get("type", "function")
            func_info = delta_dict.get("function")
            
            if not call_id:
                continue
            
            if call_id not in self.tool_calls:
                self.tool_calls[call_id] = {
                    "id": call_id,
                    "type": call_type,
                    "function": "",
                    "arguments": ""
                }
            
            if func_info:
                if isinstance(func_info, dict):
                    if "name" in func_info:
                        self.tool_calls[call_id]["function"] += func_info["name"]
                    if "arguments" in func_info:
                        self.tool_calls[call_id]["arguments"] += func_info["arguments"]
                else:
                    # Handle as object
                    if hasattr(func_info, 'name') and func_info.name:
                        self.tool_calls[call_id]["function"] += func_info.name
                    if hasattr(func_info, 'arguments') and func_info.arguments:
                        self.tool_calls[call_id]["arguments"] += func_info.arguments

    def get_tool_calls(self) -> Dict[str, Dict[str, Any]]:
        """
        Return accumulated tool calls with arguments normalised to valid JSON strings.

        OpenAI requires the ``arguments`` field to be a valid JSON string.
        Tools called with no arguments stream an empty string, which OpenAI's
        strict parser rejects with ``Failed to parse JSON: ``.

        Returns:
            Dict of tool calls with ``arguments`` guaranteed to be a valid
            JSON string (at minimum ``"{}"``) .
        """
        normalised: Dict[str, Dict[str, Any]] = {}
        for call_id, info in self.tool_calls.items():
            raw_args = info.get("arguments", "")
            # Normalise empty / blank arguments to "{}" so OpenAI never
            # receives an empty string in the arguments field.
            if not raw_args or not raw_args.strip():
                logger.debug(
                    "ToolCallAccumulator: tool '%s' has empty arguments, "
                    "normalising to '{}'",
                    info.get("function", "?"),
                )
                raw_args = "{}"
            normalised[call_id] = {**info, "arguments": raw_args}
        return normalised


def make_assistant_tool_calls_message(
    tool_calls: Dict[str, Dict[str, Any]], content: str = ""
) -> Dict[str, Any]:
    """
    Create an assistant message recording tool calls.

    OpenAI requires ``function.arguments`` to be a valid JSON **string**
    (e.g. ``"{}"``).  An empty string is rejected with
    ``"Failed to parse JSON: "`` (400 Bad Request).  This function
    normalises empty/blank arguments to ``"{}"`` as the last safety net
    before the message is appended to the conversation history.

    Args:
        tool_calls: Dict of tool call info keyed by call_id.
        content:    Optional assistant reasoning/preamble.

    Returns:
        OpenAI assistant message dict with tool_calls.
    """
    normalised_calls = []
    for call_id, info in tool_calls.items():
        raw_args = info.get("arguments", "")
        # Guard: OpenAI rejects empty-string arguments — normalise to "{}"
        if not raw_args or not raw_args.strip():
            logger.warning(
                "make_assistant_tool_calls_message: tool '%s' (id=%s) has "
                "empty arguments string — normalising to '{}' to prevent "
                "OpenAI 400 'Failed to parse JSON' error",
                info.get("function", "?"),
                call_id,
            )
            raw_args = "{}"
        normalised_calls.append((call_id, info, raw_args))

    return {
        "role": "assistant",
        "content": content or None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": info["function"],
                    "arguments": raw_args,
                },
            }
            for call_id, info, raw_args in normalised_calls
        ],
    }


def make_tool_message(tool_call_id: str, content: str) -> Dict[str, Any]:
    """
    Create a tool result message.

    Args:
        tool_call_id: The ID of the tool call being responded to.
        content:      The tool's result.

    Returns:
        OpenAI tool message dict.
    """
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }