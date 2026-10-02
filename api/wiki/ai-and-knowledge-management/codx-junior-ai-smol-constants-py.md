# SmolAgent Constants Reference

This module defines configuration constants for SmolAgent tool calling and streaming functionality.

## Iteration and Tool Call Limits

### DEFAULT_MAX_ITERATIONS
Maximum number of iterative tool rounds when not configured in model or provider settings.
- **Value**: `10`
- **Purpose**: Fallback limit to prevent excessive iteration cycles

### DEFAULT_MAX_TOOL_CALLS
Maximum number of tool calls permitted in a single round when not configured in model or provider settings.
- **Value**: `5`
- **Purpose**: Fallback limit to control parallel tool execution within a round

## Round Management

### MAX_TOOL_ROUNDS
Maximum number of sequential tool-call rounds before aborting the conversation.
- **Value**: `20`
- **Note**: Each round may contain multiple parallel tool calls

### MAX_IDENTICAL_ROUNDS
Number of consecutive identical tool-call rounds that trigger loop detection.
- **Value**: `3`
- **Purpose**: Identifies when the model requests the same tools with identical arguments repeatedly

## Error Messages

### TOOL_ROUNDS_ERROR_MSG
Error message triggered when the maximum tool rounds limit is exceeded.
- **Format**: `"Maximum tool rounds ({rounds}) exceeded. The model keeps requesting tools without producing a final answer."`

### TOOL_LOOP_ERROR_MSG
Error message triggered when an infinite tool-call loop is detected.
- **Format**: `"Infinite tool-call loop detected: the model requested the identical set of tools with the same arguments {count} times in a row."`

### TOOL_CALLS_EXCEEDED_ERROR_MSG
Error message triggered when tool call limit is exceeded in a single round.
- **Format**: `"Tool call limit exceeded in round: maximum {max_calls} allowed, but {actual_calls} were requested. Try using fewer tools or simpler operations."`

## Streaming Configuration

### CALLBACK_FLUSH_SECONDS
Time interval (in seconds) for buffering streamed chunks before flushing to callbacks.
- **Value**: `1.0`
- **Purpose**: Optimizes callback delivery batching

### TOOL_RESULT_PREVIEW_MAX_CHARS
Maximum number of characters included in tool result TOOL_END event payloads.
- **Value**: `4000`
- **Purpose**: Maintains reasonable size for chat message metadata and streamed events