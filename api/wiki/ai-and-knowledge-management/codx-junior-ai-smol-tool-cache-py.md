# Tool Execution Cache Manager

## Overview

The `ToolCache` class provides an in-memory caching mechanism for tool execution results within a single conversation. It prevents redundant tool executions by storing and retrieving results based on deterministic hashing of tool names and parameters.

## Key Features

### Cache Transparency
- Cached results bypass tool loop guards and do not count towards execution limits
- Results emit `TOOL_START`/`END` events with `cached=True` flag for observability
- Cached results are sent directly to the model without re-execution

### Deterministic Hashing
- Uses SHA256 hash of `(tool_name, sorted JSON parameters)` as cache key
- Ensures identical tool calls always produce the same key regardless of:
  - Dictionary key order
  - JSON formatting differences

### Error Handling
- Both successful and failed tool results are cached
- Prevents re-execution of tools that previously failed with identical arguments
- Gracefully skips caching when parameters cannot be serialized

## Core Methods

### `get_cache_key(tool_name, params)`
Generates a deterministic cache key from tool name and parameters.

**Parameters:**
- `tool_name` (str): Name of the tool function
- `params` (Dict[str, Any]): Arguments dictionary passed to the tool

**Returns:**
- SHA256 hex digest string, or empty string if serialization fails

**Behavior:**
- JSON parameters are sorted before hashing for consistency
- Non-serializable parameters are logged and skipped from caching

### `get(tool_name, params)`
Retrieves a cached tool result if available.

**Parameters:**
- `tool_name` (str): Name of the tool function
- `params` (Dict[str, Any]): Arguments dictionary

**Returns:**
- Cached result if found, otherwise `None`
- Automatically increments hit counter on successful retrieval

### `set(tool_name, params, result, success)`
Stores a tool result in the cache.

**Parameters:**
- `tool_name` (str): Name of the tool function
- `params` (Dict[str, Any]): Arguments dictionary
- `result` (Any): The result returned by the tool or error message
- `success` (bool): Whether the tool executed successfully

**Behavior:**
- Both successful and failed results are cached
- Invalid cache keys prevent storage

### `clear()`
Clears all cached entries and resets the cache to empty state.

### `stats()`
Returns cache performance statistics.

**Returns:**
- Dictionary containing:
  - `hits`: Number of cache hits
  - `misses`: Number of cache misses
  - `size`: Current number of cached entries
  - `hit_rate`: Percentage of hits (0-100)

## Cache Entry Structure

Cache entries are stored as tuples containing:
- `result` (Any): The cached tool result
- `was_successful` (bool): Success status of the tool execution

## Usage Considerations

- Cache is conversation-scoped and exists for a single conversation session
- Non-serializable parameters automatically skip caching
- Invalid cache keys prevent both storage and retrieval operations
- Debug logging includes first 8 characters of cache key for traceability