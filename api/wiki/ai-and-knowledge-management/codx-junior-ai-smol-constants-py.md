# Constants

This module defines shared constants used across the SmolAgent package for controlling agent behavior and handling tool-call interactions.

## Tool Round Limits

### MAX_TOOL_ROUNDS
- **Type:** `int`
- **Value:** `20`
- **Description:** Sets the maximum number of sequential tool-call rounds before aborting the conversation. Each round may contain multiple parallel tool calls.

### MAX_IDENTICAL_ROUNDS
- **Type:** `int`
- **Value:** `3`
- **Description:** Defines the number of consecutive identical tool-call rounds that trigger loop detection. This helps prevent the model from getting stuck in repetitive patterns.

## Error Messages

### TOOL_ROUNDS_ERROR_MSG
- **Type:** `str`
- **Description:** Error message displayed when the maximum tool rounds limit is exceeded. Indicates that the model continues requesting tools without producing a final answer.
- **Format:** `"Maximum tool rounds ({rounds}) exceeded. The model keeps requesting tools without producing a final answer."`

### TOOL_LOOP_ERROR_MSG
- **Type:** `str`
- **Description:** Error message displayed when an infinite tool-call loop is detected. Triggered when the model requests the identical set of tools with the same arguments multiple times in succession.
- **Format:** `"Infinite tool-call loop detected: the model requested the identical set of tools with the same arguments {count} times in a row."`

## Callback Configuration

### CALLBACK_FLUSH_SECONDS
- **Type:** `float`
- **Value:** `1.0`
- **Description:** Specifies the number of seconds to buffer streamed chunks before flushing them to callbacks. Controls the timing of callback execution for streamed data.