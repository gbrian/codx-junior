# Loop Protection for SmolAgent Tool Calling

## Overview

The loop guard module provides protection mechanisms for SmolAgent tool calling by enforcing constraints on tool execution rounds. It prevents agents from entering infinite loops where they repeatedly request the same tools without making progress.

## Key Features

The `LoopGuard` class enforces two primary safety measures:

1. **Depth Guard**: Limits the maximum number of sequential tool rounds allowed in a single conversation
2. **Fingerprint-Based Loop Detection**: Identifies and prevents identical repeated tool-call rounds by detecting when the same tools are called consecutively with the same arguments

## Core Components

### ToolLoopError Exception

A `RuntimeError` subclass raised when the model becomes stuck requesting tools without demonstrating progress toward task completion.

### fingerprint_tool_calls Function

Generates a stable, order-independent hash of tool calls to enable loop detection.

**Parameters:**
- `tool_calls`: A mapping of tool call identifiers to tool call details (id, function, and arguments)

**Returns:**
- A hexadecimal digest that uniquely represents the complete set of tool calls

**Implementation Details:**
The function normalizes tool arguments by parsing JSON when present, sorts entries alphabetically to ensure order-independence, and applies SHA-256 hashing for unique identification.

### LoopGuard Class

A stateful helper class instantiated once per conversation to track and prevent infinite tool loops.

#### Initialization

**Parameters:**
- `max_rounds`: Maximum sequential tool rounds allowed (uses `MAX_TOOL_ROUNDS` constant by default)
- `max_identical_rounds`: Number of consecutive identical rounds that trigger loop detection (uses `MAX_IDENTICAL_ROUNDS` constant by default)

#### State Tracking

The guard maintains:
- `rounds`: Counter for the total number of tool rounds executed
- `fingerprints`: List of fingerprints from each tool round for historical comparison

#### check Method

Registers a new tool round and validates both guard mechanisms.

**Parameters:**
- `tool_calls`: The current round's accumulated tool calls

**Behavior:**
- Increments the round counter
- Raises `ToolLoopError` if maximum rounds are exceeded
- Compares the current fingerprint against recent round fingerprints
- Raises `ToolLoopError` if identical rounds are detected consecutively
- Appends the current fingerprint to the history for future comparison

**Raises:**
- `ToolLoopError`: When max rounds threshold is exceeded or when a stuck loop pattern (identical consecutive rounds) is identified

## Usage Pattern

```python
guard = LoopGuard()
while ...:
    guard.check(tool_calls)  # raises ToolLoopError when stuck
```

## Logging

The module provides debug and error-level logging through Python's standard logging module, including round counters and truncated fingerprint representations for monitoring agent behavior.