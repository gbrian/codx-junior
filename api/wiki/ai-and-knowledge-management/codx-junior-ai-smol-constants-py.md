# SmolAgent Constants Documentation

## Overview

This module defines shared constants used across the SmolAgent package for managing AI model interactions, tool execution, and event streaming.

## Tool Execution Limits

### MAX_TOOL_ROUNDS
**Type:** `int`  
**Value:** `20`

Specifies the maximum number of sequential tool-call rounds before the conversation is automatically aborted. Each round may contain multiple parallel tool calls.

### MAX_IDENTICAL_ROUNDS
**Type:** `int`  
**Value:** `3`

Defines the threshold for loop detection. When the model requests an identical set of tools with the same arguments this many times consecutively, an infinite loop is detected and the process is halted.

## Error Messages

### TOOL_ROUNDS_ERROR_MSG
**Type:** `str`

Error message displayed when the maximum tool rounds limit is exceeded. Indicates that the model continues requesting tools without producing a final answer.

**Format:** "Maximum tool rounds ({rounds}) exceeded. The model keeps requesting tools without producing a final answer."

### TOOL_LOOP_ERROR_MSG
**Type:** `str`

Error message displayed when an infinite tool-call loop is detected. Indicates that the model has repeatedly requested the identical set of tools with the same arguments.

**Format:** "Infinite tool-call loop detected: the model requested the identical set of tools with the same arguments {count} times in a row."

## Event Streaming Configuration

### CALLBACK_FLUSH_SECONDS
**Type:** `float`  
**Value:** `1.0`

Specifies the time interval in seconds to buffer streamed chunks before flushing them to registered callbacks.

### TOOL_RESULT_PREVIEW_MAX_CHARS
**Type:** `int`  
**Value:** `4000`

Limits the maximum number of characters from a tool result that are included in TOOL_END event payloads. This constraint helps keep chat message metadata and streamed events at a manageable size.