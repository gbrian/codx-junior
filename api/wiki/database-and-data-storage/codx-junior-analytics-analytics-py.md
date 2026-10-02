# Analytics API Documentation
=====================================

## Overview

The Analytics API is a high-level interface for recording and querying LLM token usage and tool usage analytics. It provides a simple and consistent way to store and retrieve analytics data, making it easier to track usage patterns and trends.

## Class Diagram

### Analytics Class

The `Analytics` class serves as the core interface for interacting with the analytics storage system.

#### Methods

*   **Record Token Usage**
    *   Record a single LLM call's token consumption.
        *   Args: `username`, `project_name`, `project_id`, `model`, `provider`, `input_tokens`, `output_tokens`, `duration_seconds`, `session_id`, `tags`, `input_k_tokens_cxjcoins`, `output_k_tokens_cxjcoins`, and `request_id`.
        *   Returns: The persisted `TokenUsageEvent`.

*   **Record Tool Usage**
    *   Record a single tool execution event.
        *   Args: `name`, `username`, `project_name`, `project_id`, `time_taken`, `success`, `error_message`, `chat_id`, and `request_id`.
        *   Returns: The persisted `ToolUsageEvent`.

*   **Get Usage by User**
    *   Aggregate token usage grouped by username.
        *   Args: `start_date`, `end_date`, `project_name`, and `project_id`.
        *   Returns: A dictionary mapping usernames to their respective token usage metrics.

*   **Get Usage by Project**
    *   Aggregate token usage grouped by project name.
        *   Args: `start_date`, `end_date`, and `username`.
        *   Returns: A dictionary mapping project names to their respective token usage metrics.

*   **Get Usage by Model**
    *   Aggregate token usage grouped by model name.
        *   Args: `start_date`, `end_date`, `username`, and `project_name`.
        *   Returns: A dictionary mapping model names to their respective token usage metrics.

*   **Get Daily Usage**
    *   Return per-period aggregated token usage with configurable grouping.
        *   Args: `start_date`, `end_date`, `username`, `project_name`, and `grouping` (defaults to 'day').
        *   Returns: A list of dictionaries containing the aggregated token usage metrics for each period.

*   **Get Total Usage**
    *   Return global token totals across all filtered events.
        *   Args: `start_date`, `end_date`, `username`, `project_name`, and `project_id` (optional), with optional filtering by `model`.
        *   Returns: A dictionary containing the total token usage metrics.

*   **List Available Dates**
    *   Return all ISO dates for which analytics data is available.
    *   Returns: A sorted list of ``YYYY-MM-DD`` strings.

## Class Analytics
--------------------

### Docstring

```markdown
Analytics (class)
---------------

High-level API for recording and querying LLM token usage and tool usage analytics.
```

## Methods
-----------

*   **`__init__`**
    *   Initializes the `Analytics` object with optional `analytics_path` parameter.

        ```markdown
def __init__(self, analytics_path: str = ANALYTICS_DATA_PATH):
    """
    Args:
        analytics_path: Global directory for analytics storage.  Pass
                        ``codx.junior.globals.ANALYTICS_DATA_PATH`` here.
    """
```

*   **`record_token_usage`**
    *   Records a single LLM call's token consumption.

        ```markdown
def record_token_usage(
    *,
    username: str,
    project_name: str,
    project_id: str,
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    duration_seconds: float = 0.0,
    session_id: Optional[str] = None,
    tags: str = "",
    input_k_tokens_cxjcoins: float = 0.0,
    output_k_tokens_cxjcoins: float = 0.0,
    request_id: str = None,
    tokens_from_provider: bool = False
)-> TokenUsageEvent:
    """
    Record a single LLM call's token consumption.

    Args:
        username:           User who triggered the call.
        project_name:       Project context.
        project_id:         Project identifier.
        model:              LLM model name.
        provider:           LLM provider identifier.
        input_tokens:       Prompt token count.
        output_tokens:      Completion token count.
        duration_seconds:   Wall-clock seconds for the full request/response cycle.
        session_id:         Optional conversation/session id.
        tags:               Comma-separated tag string from request headers.
        input_k_tokens_cxjcoins:  Price per 1K tokens in CXJ coins (from AISettings).
        output_k_tokens_cxjcoins:  Price per 1K tokens in CXJ coins (from AISettings).

    Returns:
        The persisted `TokenUsageEvent`.
    """
```

*   **`record_tool_usage`**
    *   Records a single tool execution event.

        ```markdown
def record_tool_usage(
    *,
    name: str,
    username: str,
    project_name: str,
    project_id: str,
    time_taken: float,
    success: bool,
    error_message: Optional[str] = None,
    chat_id: Optional[str] = None,
    request_id: Optional[str] = None
)-> ToolUsageEvent:
    """
    Record a single tool execution event.

    Args:
        name:            Tool function name (e.g., "project_search").
        username:        User who triggered the tool.
        project_name:    Project context for the tool call.
        project_id:      Project identifier.
        time_taken:      Execution duration in seconds.
        success:         Boolean flag indicating successful execution.
        error_message:   Error details if execution failed (None if successful).
        chat_id:         Reference to the parent chat/conversation session.
        request_id:      Traceability link to the LLM request that triggered the tool.

    Returns:
        The persisted `ToolUsageEvent`.
    """
```

*   **`get_usage_by_user`**
    *   Aggregate token usage grouped by username.

        ```markdown
def get_usage_by_user(
    self,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None
)-> Dict[str, Dict[str, Any]]:
"""
Aggregate token usage grouped by username.

Args:
    start_date:   Inclusive ISO date lower bound.
    end_date:     Inclusive ISO date upper bound.
    project_name: Optional project filter.
    project_id:   Optional project id filter.

Returns:
    Dict[username, {input_tokens, output_tokens, total_tokens, calls,
                    total_duration_seconds, total_cxjcoins, tokens_from_provider}]
"""
```

*   **`get_usage_by_project`**
    *   Aggregate token usage grouped by project name.

        ```markdown
def get_usage_by_project(
    self,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    username: Optional[str] = None
)-> Dict[str, Dict[str, Any]]:
"""
Aggregate token usage grouped by project name.

Args:
    start_date: Inclusive ISO date lower bound.
    end_date:   Inclusive ISO date upper bound.
    username:   Optional user filter.

Returns:
    Dict[project_name, {input_tokens, output_tokens, total_tokens, calls,
                        total_duration_seconds, total_cxjcoins, tokens_from_provider}]
"""
```

*   **`get_usage_by_model`**
    *   Aggregate token usage grouped by model name.

        ```markdown
def get_usage_by_model(
    self,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    username: Optional[str] = None,
    project_name: Optional[str] = None
)-> Dict[str, Dict[str, Any]]:
"""
Aggregate token usage grouped by model name.

Args:
    start_date:   Inclusive ISO date lower bound.
    end_date:     Inclusive ISO date upper bound.
    username:     Optional user filter.
    project_name: Optional project filter.

Returns:
    Dict[model, {input_tokens, output_tokens, total_tokens, calls,
                 total_duration_seconds, total_cxjcoins, tokens_from_provider}]
"""
```

*   **`get_daily_usage`**
    *   Return per-period aggregated token usage with configurable grouping.

        ```markdown
def get_daily_usage(
    self,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    username: Optional[str] = None,
    project_name: Optional[str] = None,
    grouping: str = "day"
)-> List[Dict[str, Any]]:
"""
Return per-period aggregated token usage with configurable grouping.

Args:
    start_date:   Inclusive ISO date lower bound.
    end_date:     Inclusive ISO date upper bound.
    username:     Optional user filter.
    project_name: Optional project filter.
    grouping:     Time grouping level: 'minute', 'hour', or 'day'. Default: 'day'

Returns:
    List of dicts [{period, input_tokens, output_tokens, total_tokens,
                    calls, total_duration_seconds, total_cxjcoins, tokens_from_provider}]
    ordered by period ascending.
"""
```

*   **`get_total_usage`**
    *   Return global token totals across all filtered events.

        ```markdown
def get_total_usage(
    self,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    username: Optional[str] = None,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    model: Optional[str] = None
)-> Dict[str, Any]:
"""
Return global token totals across all filtered events.

Args:
    start_date:   Inclusive ISO date lower bound.
    end_date:     Inclusive ISO date upper bound.
    username:     Optional user filter.
    project_name: Optional project filter.
    project_id:   Optional project id filter.
    model:        Optional model filter.

Returns:
    Dict with keys: input_tokens, output_tokens, total_tokens, calls,
                    total_duration_seconds, total_cxjcoins, tokens_from_provider.
"""
```

*   **`list_available_dates`**
    *   Return all ISO dates for which analytics data is available.

        ```markdown
def list_available_dates(self)-> List[str]:
"""
Return all ISO dates for which analytics data is available.

Returns:
    Sorted list of ``YYYY-MM-DD`` strings.
"""
```

## Dependencies
**Imports from:** codx/junior/analytics/model.py, codx/junior/analytics/storage.py, codx/junior/globals.py
**Imported by:** codx/junior/ai/wallet_check.py, codx/junior/analytics/__init__.py, codx/junior/api/users.py