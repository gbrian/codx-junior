# Loop Protection for SmolAgent Tool Calling

## Overview

The `LoopGuard` class provides stateful protection against infinite tool loops in SmolAgent implementations. It enforces three complementary protection mechanisms to ensure safe and controlled tool execution:

1. **Depth Guard** — Limits the maximum number of sequential tool rounds
2. **Breadth Guard** — Restricts the number of tool calls per single round
3. **Stuck Loop Detection** — Identifies when the model repeats identical tool-call rounds without progress

## Key Concepts

### Limit Resolution Priority

The guard resolves configuration limits with the following priority:
1. Explicitly passed parameters (from model/provider configuration)
2. Fallback defaults (safe defaults for unconfined execution)

This design ensures that configured settings override defaults while maintaining safe bounds even when no explicit configuration is provided.

### Fingerprint-Based Detection

The `fingerprint_tool_calls()` function generates a stable, order-independent hash of tool calls. This fingerprinting enables detection of identical consecutive rounds by:

- Normalizing tool call arguments to JSON format
- Sorting entries for consistency
- Generating a SHA256 hash of the normalized set

## LoopGuard Class

### Initialization

```python
guard = LoopGuard(
    max_iterations=model_settings.max_iterations,
    max_tool_calls=model_settings.max_tool_calls
)
```

**Parameters:**

- `max_iterations` (Optional[int]) — Maximum sequential tool rounds allowed. Defaults to `DEFAULT_MAX_ITERATIONS` if None.
- `max_tool_calls` (Optional[int]) — Maximum tool calls allowed per single round. Defaults to `DEFAULT_MAX_TOOL_CALLS` if None.
- `max_identical_rounds` (int) — Number of identical consecutive rounds that trigger loop detection (typically 3).

### The check() Method

```python
guard.check(tool_calls)
```

Registers a new tool round and verifies all three guard mechanisms.

**Parameters:**

- `tool_calls` — Dictionary mapping `tool_call_id` to tool call information (containing `id`, `function`, and `arguments`).

**Behavior:**

The method performs checks in the following order:

1. Increments the round counter and compares against `max_iterations`
2. Validates that the number of tool calls doesn't exceed `max_tool_calls`
3. Checks for identical consecutive rounds using fingerprint comparison

**Exceptions:**

Raises `ToolLoopError` when:
- Maximum iterations are exceeded
- Tool call limit per round is violated
- A stuck loop is detected (same tool calls repeated for `max_identical_rounds` consecutive rounds)

## ToolLoopError Exception

```python
class ToolLoopError(RuntimeError):
    """Raised when the model is stuck requesting tools without progress."""
```

This exception is raised by the `LoopGuard` when any of its three protection mechanisms detect a violation.

## Usage Pattern

```python
guard = LoopGuard(
    max_iterations=model_settings.max_iterations,
    max_tool_calls=model_settings.max_tool_calls
)
while ...:
    guard.check(tool_calls)  # raises ToolLoopError when stuck
```

The guard should be instantiated once per conversation and its `check()` method called after each tool round to maintain protection throughout the agent's execution cycle.