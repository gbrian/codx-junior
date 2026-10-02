# Agent Runtime Documentation

## Overview

The Agent Runtime module provides unified logging, event emission, and cancellation management for agent runs. It wraps OpenAI AI functionality without modifying it, adapting OpenAI's stream and tool callbacks onto the `AgentRunContext`.

## Core Components

### Errors

#### AgentCancelled
An exception raised at checkpoints when an agent run has been cancelled.

#### InsufficientFundsError
An exception raised by the wallet pre-flight check when there are insufficient funds to execute the agent.

### Cancellation Management

#### CancellationToken
A thread-safe cancellation token that allows cancellation to be requested from any thread (such as a Socket.IO 'stop' handler) while the agent loop runs on another thread.

**Methods:**
- `cancel(reason: str = "user_requested")` — Cancels the token with an optional reason
- `cancelled` (property) — Returns whether the token has been cancelled
- `raise_if_cancelled()` — Raises `AgentCancelled` if the token has been cancelled

### Event System

#### AgentEventType
An enumeration of all possible event types emitted during agent execution:
- `RUN_START` — Agent run initialization
- `RUN_END` — Agent run completion
- `RUN_ERROR` — Agent run encountered an error
- `RUN_CANCELLED` — Agent run was cancelled
- `LLM_REQUEST` — Language model request
- `LLM_CHUNK` — Language model streaming chunk
- `LLM_USAGE` — Language model token usage
- `TOOL_START` — Tool execution started
- `TOOL_END` — Tool execution completed
- `TOOL_ERROR` — Tool execution failed
- `WALLET_CHECK` — Wallet balance verification

#### AgentEvent
A dataclass representing a single event emitted during agent execution.

**Fields:**
- `type` — The event type
- `run_id` — Unique identifier for the run
- `project_id` — Associated project identifier
- `payload` — Event-specific data (dict)
- `ts` — Timestamp (auto-generated)

**Methods:**
- `to_dict()` — Serializes the event to a dictionary

### Analytics

#### RunAnalytics
Automatically tracks and aggregates metrics throughout the agent run.

**Tracked Metrics:**
- `prompt_tokens` — Total prompt tokens consumed
- `completion_tokens` — Total completion tokens generated
- `tool_calls` — Per-tool statistics including count, error count, and total execution time

**Methods:**
- `on_event(event: AgentEvent)` — Processes an event and updates analytics
- `summary()` — Returns a dictionary containing all tracked metrics

### Agent Run Context

#### AgentRunContext
The primary context object passed through the agent loop, encapsulating all runtime state and operations.

**Initialization:**
```python
AgentRunContext(project_id: str, 
                listeners: list[Callable] | None = None,
                chunk_emit_every: float = 0.25)
```

**Key Attributes:**
- `run_id` — Unique 12-character identifier for this run
- `project_id` — Associated project identifier
- `token` — Cancellation token for this run
- `analytics` — Runtime analytics collector

#### Event Management

**Methods:**
- `add_listener(fn: Callable[[AgentEvent], Any])` — Registers an event listener
- `emit(type_: AgentEventType, **payload)` — Emits an event with structured logging, analytics tracking, and listener notification

Events are:
1. Logged as machine-parseable JSON lines correlated by `run_id`
2. Processed by the analytics system
3. Fanned out to all registered listeners (failures in listeners do not affect the run)

#### Cancellation Control

**Methods:**
- `cancel(reason: str = "user_requested")` — Requests cancellation of the run
- `checkpoint()` — Safe abort point that raises `AgentCancelled` if cancellation was requested

#### Stream Handling

**Methods:**
- `guard_stream(chunks: Iterable) -> Iterator` — Wraps an LLM stream to check cancellation on every chunk and emit throttled chunk events (controlled by `chunk_emit_every` parameter) for UI progress updates

#### Tool Instrumentation

**Context Manager:**
```python
@contextmanager
def tool(self, name: str, **args)
```

Automatically instruments tool execution by:
1. Checking cancellation before execution
2. Emitting `TOOL_START` event with arguments
3. Measuring execution duration
4. Emitting either `TOOL_END` or `TOOL_ERROR` event
5. Propagating exceptions (except `AgentCancelled`)

#### Run Lifecycle

**Context Manager:**
```python
@contextmanager
def run(self, wallet=None, estimated_cost: float = 0.0)
```

Manages the complete agent run lifecycle:

1. **Pre-flight wallet check** — Verifies sufficient balance before spending tokens
2. **Run initialization** — Emits `RUN_START` event
3. **Execution** — Yields the context for agent logic
4. **Completion handling:**
   - On cancellation — Emits `RUN_CANCELLED` with reason and analytics summary
   - On error — Emits `RUN_ERROR` with error details and analytics summary, then re-raises
   - On success — Emits `RUN_END` with analytics summary