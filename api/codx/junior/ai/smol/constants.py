"""
Constants for SmolAgent tool calling and streaming.

Made with ❤️ by codx-junior
"""

# Fallback maximum number of iterative tool rounds
# (when not configured in model/provider settings)
DEFAULT_MAX_ITERATIONS: int = 10

# Fallback maximum number of tool calls per single round
# (when not configured in model/provider settings)
DEFAULT_MAX_TOOL_CALLS: int = 5

# Maximum number of sequential tool-call rounds (each round may contain
# multiple parallel tool calls) before aborting the conversation.
MAX_TOOL_ROUNDS: int = 20

# Number of consecutive identical tool-call rounds that trigger loop detection.
MAX_IDENTICAL_ROUNDS: int = 3

TOOL_ROUNDS_ERROR_MSG: str = (
    "Maximum tool rounds ({rounds}) exceeded. "
    "The model keeps requesting tools without producing a final answer."
)

TOOL_LOOP_ERROR_MSG: str = (
    "Infinite tool-call loop detected: the model requested the identical "
    "set of tools with the same arguments {count} times in a row."
)

# Seconds to buffer streamed chunks before flushing them to callbacks.
CALLBACK_FLUSH_SECONDS: float = 1.0

# Maximum characters of a tool result included in TOOL_END event payloads.
# Keeps chat message meta_data and streamed events reasonably small.
TOOL_RESULT_PREVIEW_MAX_CHARS: int = 4000


TOOL_CALLS_EXCEEDED_ERROR_MSG: str = (
    "Tool call limit exceeded in round: maximum {max_calls} allowed, but {actual_calls} were requested. "
    "Try using fewer tools or simpler operations."
)

# Made with ❤️ by codx-junior