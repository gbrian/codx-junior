# SmolAgent Constants Reference

This module defines constants for SmolAgent tool calling and streaming functionality, providing default values and limits for agent behavior control.

## Iteration and Tool Call Limits

### DEFAULT_MAX_ITERATIONS
Maximum number of iterative tool rounds when not configured in model or provider settings.
- **Value:** 10
- **Purpose:** Provides a fallback limit to prevent infinite agent loops

### DEFAULT_MAX_TOOL_CALLS
Maximum number of tool calls allowed per single round when not configured in model or provider settings.
- **Value:** 5
- **Purpose:** Controls parallelization of tool execution within each round

### MAX_TOOL_ROUNDS
Maximum number of sequential tool-call rounds before aborting the conversation.
- **Value:** 20
- **Purpose:** Hard limit across all iterative rounds to ensure conversation termination

### MAX_IDENTICAL_ROUNDS
Number of consecutive identical tool-call rounds that trigger loop detection.
- **Value:** 3
- **Purpose:** Identifies when the model enters repetitive behavior patterns

## Streaming and Output Configuration

### CALLBACK_FLUSH_SECONDS
Buffer duration for streamed chunks before flushing to callbacks.
- **Value:** 1.0 seconds
- **Purpose:** Optimizes callback performance by batching stream chunks

### TOOL_RESULT_PREVIEW_MAX_CHARS
Maximum character limit for tool results included in TOOL_END event payloads.
- **Value:** 4000 characters
- **Purpose:** Maintains reasonable size for chat message metadata and streamed events

## Error Messages

### TOOL_ROUNDS_ERROR_MSG
Raised when maximum tool rounds are exceeded without a final answer.
- **Template:** "Maximum tool rounds ({rounds}) exceeded. The model keeps requesting tools without producing a final answer."

### TOOL_LOOP_ERROR_MSG
Raised when infinite tool-call loop is detected.
- **Template:** "Infinite tool-call loop detected: the model requested the identical set of tools with the same arguments {count} times in a row."

### TOOL_CALLS_EXCEEDED_ERROR_MSG
Raised when tool call limit is exceeded within a single round.
- **Template:** "Tool call limit exceeded in round: maximum {max_calls} allowed, but {actual_calls} were requested. Try using fewer tools or simpler operations."