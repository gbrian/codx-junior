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

# ── Tool usage summary (generated only when the tool loop breaks) ─────────────
# When LoopGuard stops a run, the tool conversation (the results the model saw)
# would otherwise be discarded. A single lightweight request to the project's
# knowledge/RAG model distils the value of the tools used so it can be appended
# to the assistant answer and reused in the next iteration without re-running
# the same tools.

# Analytics tag used for the summary request token usage, so its cost is
# visible but separable from the main chat run.
TOOL_ANALYSIS_TAG: str = "tool-analysis"

# Maximum characters of each tool result embedded in the summary prompt.
TOOL_ANALYSIS_RESULT_MAX_CHARS: int = 2000

# Maximum characters of the user request embedded in the summary prompt.
TOOL_ANALYSIS_TASK_MAX_CHARS: int = 3000

# Maximum tokens requested for the generated summary.
TOOL_ANALYSIS_MAX_TOKENS: int = 800

# Heading that delimits the summary block appended to the assistant answer.
TOOL_ANALYSIS_HEADING: str = "### 🧰 Tool usage summary"

# System prompt for the tool usage summary request.
TOOL_ANALYSIS_SYSTEM_PROMPT: str = (
    "You review how an autonomous agent used its tools. The agent was "
    "interrupted because it reached its tool-usage limits, and its work must "
    "be preserved so the next iteration can continue without repeating tools.\n"
    "Given the user request and the tools that were executed (arguments and "
    "results), write a concise Markdown summary with these sections:\n"
    "1. **Useful findings** – what each relevant tool call revealed, with the "
    "concrete evidence (paths, files, values) that must NOT be re-discovered.\n"
    "2. **Not useful / already known** – tool calls that returned nothing new "
    "or were irrelevant, so they should not be repeated.\n"
    "3. **Suggested next step** – the smallest next action to continue.\n"
    "Be factual and specific. Never invent information absent from the tool "
    "results. Keep it under ~300 words."
)

# Fallback note appended when the summary cannot be produced by the model.
# It still lists the tools already executed so the next iteration is never
# worse off than before this feature existed.
TOOL_ANALYSIS_FALLBACK_NOTE: str = (
    "The tool iteration limit was reached. The tools listed below were "
    "already executed in this run and should not be repeated unless their "
    "inputs changed."
)

# Made with ❤️ by codx-junior