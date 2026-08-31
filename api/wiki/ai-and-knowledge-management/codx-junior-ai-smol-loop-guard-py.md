# Loop Guard Documentation

## Overview

The `LoopGuard` class provides protection against infinite tool loops in SmolAgent tool calling. It enforces three complementary protection mechanisms to ensure safe and bounded execution of iterative tool-calling workflows.

## Key Features

### Three-Layer Protection

1. **Depth Guard**: Enforces a maximum number of sequential tool rounds
2. **Breadth Guard**: Limits the number of tool calls allowed in a single round
3. **Stuck Loop Detection**: Uses fingerprint-based analysis to detect when the model repeats identical tool-call sequences

### Intelligent Limit Resolution

The guard resolves limits using the following priority:
- Explicitly passed parameters (model/provider configured)
- Fallback defaults (safe defaults for unconfined execution)

This ensures that model or provider settings can override defaults while maintaining safe bounds even when no configuration is present.

## Core Components

### LoopGuard Class

The main stateful helper that should be instantiated once per conversation.

**Constructor Parameters:**
- `max_iterations` (Optional[int]): Maximum sequential tool rounds allowed. Defaults to `DEFAULT_MAX_ITERATIONS` if not specified.
- `max_tool_calls` (Optional[int]): Maximum tool calls allowed per single round. Defaults to `DEFAULT_MAX_TOOL_CALLS` if not specified.
- `max_identical_rounds` (int): Number of identical consecutive rounds that trigger loop detection (typically 3).

**State Management:**
- `rounds` (int): Tracks the current round counter
- `fingerprints` (List[str]): Maintains a history of tool-call fingerprints for stuck loop detection

### ToolLoopError Exception

A `RuntimeError` subclass raised when the model is stuck requesting tools without progress. This can occur when:
- Maximum iterations are exceeded
- Tool call limit is violated in a single round
- A stuck loop is detected through fingerprint analysis

### fingerprint_tool_calls Function

Produces a stable, order-independent hash of a set of tool calls.

**Parameters:**
- `tool_calls` (Dict[str, Dict[str, Any]]): Mapping of tool_call_id → {id, function, arguments}

**Returns:**
- A hex digest (SHA256) uniquely representing the tool-call set

**Key Behavior:**
- Arguments are normalized to JSON with sorted keys for consistency
- The fingerprint is order-independent, meaning identical calls in different order produce the same hash
- Gracefully handles non-JSON arguments by converting them to strings

## Usage Pattern

```python
# Initialize guard with model settings
guard = LoopGuard(
    max_iterations=model_settings.max_iterations,
    max_tool_calls=model_settings.max_tool_calls
)

# Check each tool round
while ...:
    guard.check(tool_calls)  # raises ToolLoopError when violations occur
```

## Check Method Behavior

The `check()` method validates tool calls through three sequential checks:

1. **Depth Guard Check**: Increments the round counter and verifies it hasn't exceeded `max_iterations`
2. **Breadth Guard Check**: Verifies the number of tool calls doesn't exceed `max_tool_calls`
3. **Stuck Loop Guard Check**: Analyzes the last `max_identical_rounds` fingerprints to detect if the model is repeating identical tool-call sequences

**Parameters:**
- `tool_calls` (Dict[str, Dict[str, Any]]): The current round's accumulated tool calls dictionary

**Raises:**
- `ToolLoopError`: When any protection mechanism is violated

## Error Messages

The guard provides specific error messages for each violation type:
- `TOOL_ROUNDS_ERROR_MSG`: Raised when maximum iterations are exceeded
- `TOOL_CALLS_EXCEEDED_ERROR_MSG`: Raised when breadth limit is violated
- `TOOL_LOOP_ERROR_MSG`: Raised when a stuck loop is detected

## Logging

The guard integrates logging at multiple levels:
- **DEBUG**: Logs initialization parameters and successful round validation with fingerprints
- **ERROR**: Logs detailed information when any protection mechanism is triggered

Fingerprints are logged in truncated form (first 12 characters) for readability.