# Custom Tool Executor

## Overview

The Custom Tool Executor is a service component responsible for executing custom tools (bash scripts) with parameter substitution, error handling, and response formatting. It provides a secure and controlled environment for running shell commands with variable parameters.

## Purpose

This module handles:
- Script execution with configurable timeout
- Parameter validation and safe substitution
- Error capture and standardized response formatting
- Security measures to prevent shell injection attacks

## Architecture

### Main Class: CustomToolExecutor

The `CustomToolExecutor` class manages the execution lifecycle of custom tools.

#### Initialization

```python
__init__(timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS)
```

Initializes the executor with a configurable timeout value (default: 30 seconds).

#### Core Method: execute()

```python
execute(tool: CustomTool, parameters: Dict[str, Any] = None) -> CustomToolExecutionResponse
```

The primary method that orchestrates tool execution through the following logic:

1. **Validation**: Checks if the tool is active
2. **Parameter Validation**: Verifies all required parameters are provided
3. **Parameter Substitution**: Replaces placeholders in the script with parameter values
4. **Script Execution**: Runs the bash script with timeout protection
5. **Output Capture**: Collects stdout and stderr with size limits
6. **Response Formatting**: Returns structured execution results

### Helper Methods

#### Parameter Validation

```python
_validate_parameters(tool: CustomTool, parameters: Dict[str, Any]) -> list
```

Validates that all required parameters defined in the tool are present in the parameters dictionary. Returns a list of missing parameter names.

#### Parameter Substitution

```python
_substitute_parameters(script: str, parameters: Dict[str, Any]) -> str
```

Substitutes parameter values into the script template using `{{param_name}}` placeholder syntax. Implements security measures by escaping all parameter values using `shlex.quote()` to prevent shell injection attacks.

## Configuration

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `DEFAULT_TIMEOUT_SECONDS` | 30 | Default maximum execution time for scripts |
| `MAX_OUTPUT_LENGTH` | 10000 | Maximum characters captured from stdout/stderr |

## Response Format

The `execute()` method returns a `CustomToolExecutionResponse` containing:

- **tool_id**: Identifier of the executed tool
- **success**: Boolean indicating successful execution (return code 0)
- **user_response**: Error messages or stderr output (user-facing)
- **llm_response**: stdout output (for LLM processing)
- **execution_time_ms**: Script execution duration in milliseconds
- **error**: Error description if execution failed

## Security Features

### Shell Injection Prevention

All parameter values are escaped using Python's `shlex.quote()` function before substitution into the script. This applies to:
- String parameters
- List and dictionary parameters (converted to string then escaped)
- Numeric parameters (converted to string then escaped)

### Execution Safety

- Tools can be marked as inactive to prevent execution
- Script execution is isolated within a subprocess
- Timeout protection prevents long-running scripts from blocking
- Output is truncated to prevent memory issues (10,000 character limit)

## Error Handling

The executor handles the following error scenarios:

| Scenario | Response |
|----------|----------|
| Inactive tool | Returns failure with "Tool disabled" error |
| Missing parameters | Returns failure with parameter names |
| Timeout (>30s) | Returns timeout error with user message |
| Non-zero exit code | Returns failure with exit code error |
| Exception during execution | Returns failure with exception details |

## Logging

Execution events are logged at appropriate levels:
- **INFO**: Successful tool execution with metrics
- **ERROR**: Timeouts, missing tools, or unexpected exceptions

All logs include the tool ID, return code, and execution time for debugging purposes.