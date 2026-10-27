"""
Message handling utilities for SmolAgent.

Converts LangChain messages to OpenAI format, manages tool call accumulation,
and constructs tool/assistant messages for the iterative tool loop.

Thought Signatures
Providers may attach opaque metadata to a tool call that MUST be echoed back
verbatim on the following request. Google's Gemini thinking models (e.g.
``gemini-3-pro``) return an encrypted ``thought_signature`` inside
``extra_content`` and reject the continuation with
``400 INVALID_ARGUMENT ... Function call is missing a thought_signature`` when
it is dropped. This module captures such fields while streaming
(:meth:`ToolCallAccumulator.add`) and re-attaches them to the assistant
tool-call message (:func:`make_assistant_tool_calls_message`).
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from langchain.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

# Provider-specific tool-call fields that must be echoed back verbatim on the
# next request. ``extra_content`` is the OpenAI-compatibility channel used by
# Google's Gemini API to carry ``{"google": {"thought_signature": "<blob>"}}``.
TOOL_CALL_EXTRA_CONTENT_KEYS: Tuple[str, ...] = ("extra_content",)

# Sentinel accepted by the Gemini API in place of a real thought signature. It
# disables signature validation for that function-call part, which is required
# for parallel tool calls where Gemini sometimes returns the signature for the
# first part(s) only and then rejects the rest with a 400 error.
THOUGHT_SIGNATURE_SKIP_SENTINEL: str = "skip_thought_signature_validator"


def _extract_extra_content(source: Any) -> Dict[str, Any]:
    """
    Return the provider-specific tool-call extras present on a streaming delta.

    Reads the allow-listed keys (:data:`TOOL_CALL_EXTRA_CONTENT_KEYS`) from
    either a plain dict (the result of ``model_dump()``) or the raw delta
    object. Both are inspected because not every SDK/gateway version serialises
    unknown ("extra") fields into ``model_dump()``.

    Args:
        source: A delta dict or the raw SDK delta object.

    Returns:
        Dict with the extra keys found (empty when none are present).
    """
    extras: Dict[str, Any] = {}

    for key in TOOL_CALL_EXTRA_CONTENT_KEYS:
        value = None
        if isinstance(source, dict):
            value = source.get(key)
        if value is None:
            value = getattr(source, key, None)
        if value:
            extras[key] = value

    return extras


def _merge_extra_content(target: Dict[str, Any], incoming: Dict[str, Any]) -> None:
    """
    Deep-merge provider extras into an accumulated tool-call entry.

    ``extra_content`` may arrive complete on the first chunk or split across
    several chunks, so nested mappings are merged instead of overwritten.

    Args:
        target:   Accumulated tool-call dict (mutated in place).
        incoming: Extras collected from the current delta.
    """
    for key, value in incoming.items():
        if isinstance(value, dict):
            existing = target.get(key)
            if not isinstance(existing, dict):
                existing = {}
                target[key] = existing
            _merge_extra_content(existing, value)
        elif value not in (None, ""):
            target[key] = value


def _skip_thought_signature_extra() -> Dict[str, Any]:
    """
    Build the placeholder ``extra_content`` used for parts without a signature.

    Returns:
        ``{"extra_content": {"google": {"thought_signature": "<sentinel>"}}}``.
    """
    return {
        "extra_content": {
            "google": {
                "thought_signature": THOUGHT_SIGNATURE_SKIP_SENTINEL,
            }
        }
    }


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
    """Accumulates and manages tool calls from streamed chunks.

    OpenAI streams tool calls across multiple chunks. The protocol is:
    - First chunk for a tool call: contains ``id``, ``type``, and possibly
      an empty ``function.arguments`` string.
    - Subsequent chunks: ``id`` is ``None``; ``index`` identifies which tool
      call the chunk belongs to; ``function.arguments`` contains the next
      fragment of the JSON arguments string.

    The accumulator uses ``index`` as the primary correlation key and maps it
    to the ``call_id`` seen on the first chunk, so argument fragments arriving
    on ``id=None`` chunks are correctly appended to the right tool call.

    Provider extras such as Gemini's ``extra_content.google.thought_signature``
    are captured alongside the call so they can be echoed back on the next
    request (see :func:`make_assistant_tool_calls_message`).
    """

    def __init__(self) -> None:
        """Initialize the accumulator with empty state."""
        # Primary store: call_id → accumulated tool call dict
        self.tool_calls: Dict[str, Dict[str, Any]] = {}
        # Secondary index: chunk index → call_id (for id=None argument chunks)
        self._index_to_call_id: Dict[int, str] = {}

    def add(self, deltas: List) -> None:
        """
        Accumulate tool call deltas from streaming chunks.

        Handles both dict and Pydantic model formats by converting to dict.

        KEY FIX: OpenAI only sets ``id`` on the FIRST chunk of each tool call.
        All subsequent chunks carrying ``function.arguments`` fragments have
        ``id=None``. The ``index`` field is always present and stable, so we
        use it to map back to the original ``call_id``.

        Provider-specific fields (``extra_content``, e.g. Gemini thought
        signatures) are captured per tool call and preserved so the assistant
        message can echo them back verbatim.
        """
        if not deltas:
            return
        
        for delta in deltas:
            # Convert Pydantic model to dict if needed
            if hasattr(delta, 'model_dump'):
                # Pydantic v2 — exclude_none=False so that explicit None id
                # fields are preserved and we can detect "no id on this chunk"
                delta_dict = delta.model_dump()
            elif hasattr(delta, 'dict'):
                # Pydantic v1
                delta_dict = delta.dict()
            elif isinstance(delta, dict):
                delta_dict = delta
            else:
                # Fallback: try to extract as dict
                delta_dict = {
                    'index': getattr(delta, 'index', 0),
                    'id': getattr(delta, 'id', None),
                    'type': getattr(delta, 'type', 'function'),
                    'function': getattr(delta, 'function', None),
                }

            chunk_index: int = delta_dict.get("index", 0)
            call_id: Optional[str] = delta_dict.get("id")  # None on non-first chunks
            call_type: str = delta_dict.get("type") or "function"
            func_info = delta_dict.get("function")

            if call_id:
                # First chunk for this tool call: register the index → call_id mapping
                # and initialise the accumulator entry.
                self._index_to_call_id[chunk_index] = call_id
                if call_id not in self.tool_calls:
                    self.tool_calls[call_id] = {
                        "id": call_id,
                        "type": call_type,
                        "function": "",
                        "arguments": "",
                    }
            else:
                # Subsequent chunk: resolve call_id via index
                call_id = self._index_to_call_id.get(chunk_index)
                if not call_id:
                    logger.warning(
                        "ToolCallAccumulator: received chunk with index=%d but no "
                        "matching call_id registered — dropping chunk",
                        chunk_index,
                    )
                    continue

            # Capture provider-specific tool-call metadata (e.g. Google's
            # extra_content.google.thought_signature). Read from both the dumped
            # dict and the raw delta object: not every SDK/gateway version
            # serialises unknown fields into model_dump().
            extra_content = _extract_extra_content(delta_dict)
            if not extra_content:
                extra_content = _extract_extra_content(delta)
            if extra_content:
                _merge_extra_content(self.tool_calls[call_id], extra_content)
                logger.debug(
                    "ToolCallAccumulator: captured extra_content for tool "
                    "'%s' (keys=%s)",
                    self.tool_calls[call_id].get("function") or "?",
                    list(extra_content.keys()),
                )

            if func_info:
                if isinstance(func_info, dict):
                    if func_info.get("name"):
                        self.tool_calls[call_id]["function"] += func_info["name"]
                    if func_info.get("arguments") is not None:
                        self.tool_calls[call_id]["arguments"] += func_info["arguments"]
                else:
                    # Handle as object (Pydantic not fully converted)
                    func_name = getattr(func_info, 'name', None)
                    func_args = getattr(func_info, 'arguments', None)
                    if func_name:
                        self.tool_calls[call_id]["function"] += func_name
                    if func_args is not None:
                        self.tool_calls[call_id]["arguments"] += func_args

    def get_tool_calls(self) -> Dict[str, Dict[str, Any]]:
        """
        Return accumulated tool calls with arguments normalised to valid JSON strings.

        OpenAI requires the ``arguments`` field to be a valid JSON string.
        Tools called with no arguments stream an empty string, which OpenAI's
        strict parser rejects with ``Failed to parse JSON: ``.

        Provider extras captured while streaming (e.g. ``extra_content``) are
        preserved on the returned entries.

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

    Provider extras captured while streaming (``extra_content``) are echoed
    back verbatim on each tool call. Gemini 3 thinking models REQUIRE the
    ``thought_signature`` they returned inside ``extra_content`` to be sent
    back in this message, otherwise the continuation fails with
    ``400 INVALID_ARGUMENT ... Function call is missing a thought_signature``.
    When the provider returned a signature for some parts but not for others
    (observed with parallel calls), the missing parts get the documented
    ``skip_thought_signature_validator`` sentinel so the turn is not rejected.

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

    # Detect whether the provider used the extra_content channel for this round
    # (Gemini thought signatures). Only then is it meaningful to fill the gaps
    # of the parts that arrived without one.
    provider_extras_seen = any(
        info.get(key)
        for _, info, _ in normalised_calls
        for key in TOOL_CALL_EXTRA_CONTENT_KEYS
    )

    tool_calls_payload: List[Dict[str, Any]] = []
    for call_id, info, raw_args in normalised_calls:
        tool_call_payload: Dict[str, Any] = {
            "id": call_id,
            "type": "function",
            "function": {
                "name": info["function"],
                "arguments": raw_args,
            },
        }

        # Echo provider-specific fields verbatim (Gemini thought_signature).
        for key in TOOL_CALL_EXTRA_CONTENT_KEYS:
            extra_value = info.get(key)
            if extra_value:
                tool_call_payload[key] = extra_value

        if provider_extras_seen and not any(
            key in tool_call_payload for key in TOOL_CALL_EXTRA_CONTENT_KEYS
        ):
            # Gemini omits the signature for some parallel tool calls and then
            # rejects the turn at that position. The documented sentinel keeps
            # the request valid (validation is skipped for this part only).
            tool_call_payload.update(_skip_thought_signature_extra())
            logger.warning(
                "make_assistant_tool_calls_message: tool '%s' (id=%s) has no "
                "extra_content while sibling tool calls do — sending the '%s' "
                "sentinel to avoid a 400 'missing thought_signature' error",
                info["function"],
                call_id,
                THOUGHT_SIGNATURE_SKIP_SENTINEL,
            )

        tool_calls_payload.append(tool_call_payload)

    return {
        "role": "assistant",
        "content": content or None,
        "tool_calls": tool_calls_payload,
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