# Custom Tool Executor

## Overview

The `CustomToolExecutor` is a utility class designed to execute custom tools (bash scripts) with dynamic parameter substitution. It handles script execution, error capture, timeout management, and response formatting for the codx-junior system.

## Key Features

- **Parameter Substitution**: Replaces placeholders in scripts with provided parameter values
- **Security**: Uses `shlex.quote()` to escape parameters and prevent shell injection attacks
- **Timeout Management**: Enforces maximum execution time limits on scripts
- **Error Handling**: Captures and formats execution errors, timeouts, and validation failures
- **Response Formatting**: Separates user-facing responses (stderr) from LLM responses (stdout)
- **Execution Tracking**: Logs execution details including return codes and execution time

## Configuration

### Initialization

```python
executor = CustomToolExecutor(timeout_seconds=30)
```

**Parameters:**
- `timeout_seconds` (int, optional): Maximum execution time for scripts in seconds. Defaults to `DEFAULT_TIMEOUT_SECONDS` (30 seconds).

## Core Methods

### execute()

Executes a custom tool with the provided parameters and returns a `CustomToolExecutionResponse`.

**Parameters:**
- `tool` (CustomTool): The custom tool instance to execute
- `parameters` (Dict[str, Any], optional): Dictionary of parameter values to substitute

**Returns:**
- `CustomToolExecutionResponse`: Contains execution status, responses, timing, and error information

**Execution Logic:**
1. Validates that the tool is active
2. Validates all required parameters are provided
3. Substitutes parameters into the script using `{{param_name}}` syntax
4. Executes the script as a bash command with the configured timeout
5. Captures stdout (LLM response) and stderr (user response)
6. Returns formatted response with execution metadata

**Return Codes:**
- Success (return code 0): `success=True`, `llm_response` contains stdout
- Non-zero exit code: `success=False`, `user_response` contains error information
- Timeout: `success=False`, `error="Timeout"`
- Validation failure: `success=False`, `error` explains the issue

### _validate_parameters() (Static)

Validates that all required parameters are provided.

**Parameters:**
- `tool` (CustomTool): Tool with parameter definitions
- `parameters` (Dict[str, Any]): Provided parameter values

**Returns:**
- `list`: List of missing required parameter names (empty if valid)

### _substitute_parameters() (Static)

Substitutes parameter values into script templates using `{{param_name}}` syntax.

**Parameters:**
- `script` (str): Script template with placeholders
- `parameters` (Dict[str, Any]): Parameter values to substitute

**Returns:**
- `str`: Script with substituted and escaped parameters

**Security Note:** All parameter values are escaped using `shlex.quote()` regardless of type (strings, lists, dicts, or other types are converted to strings and escaped). This prevents shell injection attacks.

## Output Limits

- `MAX_OUTPUT_LENGTH`: 10,000 characters maximum for both stdout and stderr

## Error Handling

The executor captures and handles the following error scenarios:

- **Tool Disabled**: Tool is marked as inactive
- **Missing Parameters**: Required parameters not provided
- **Timeout**: Script execution exceeds the timeout duration
- **Non-zero Exit Code**: Script exits with error status
- **Execution Errors**: Unexpected exceptions during execution

All errors are logged with appropriate context and returned in the `CustomToolExecutionResponse`.

## Example Usage

```python
# Create a custom tool
tool = CustomTool(
    id="my-tool",
    script_body="echo 'Hello {{name}}'",
    active=True,
    parameters=[Parameter(name="name", required=True)]
)

# Execute with parameters
executor = CustomToolExecutor(timeout_seconds=30)
response = executor.execute(tool, {"name": "World"})

# Check response
if response.success:
    print(f"Output: {response.llm_response}")
else:
    print(f"Error: {response.user_response}")
```