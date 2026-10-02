# Analytics Service Guide

The `Analytics` class provides a high-level API for recording and querying LLM token usage analytics within the Codx Junior environment. It centralizes data logging and retrieval for token consumption metrics, offering detailed breakdowns by user, project, model, and time period.

## Initialization

To use the service, an instance of `Analytics` must be created. By default, it reads its storage path from the global analytics path (`ANALYTICS_DATA_PATH`).

### `__init__(self, analytics_path: str = ANALYTICS_DATA_PATH)`
Initializes the analytics client by setting up the internal `AnalyticsStorage` component.

**Parameters:**
*   `analytics_path` (str): The global directory for analytics storage.

## Writing Data: Recording Token Usage

The primary way to log data is through `record_token_usage`. This method aggregates all necessary metrics into a single persistent `TokenUsageEvent`.

### `record_token_usage(...)`
Records a single LLM call's token consumption event.

**Parameters:**
*   `username` (str): The user who triggered the call.
*   `project_name` (str): The project context where the call occurred.
*   `project_id` (str): The specific identifier for the project.
*   `model` (str): LLM model name used.
*   `provider` (str): Identifier of the LLM provider (e.g., OpenAI, Anthropic).
*   `input_tokens` (int): Count of tokens in the prompt/input.
*   `output_tokens` (int): Count of tokens generated in the completion/output.
*   `duration_seconds` (float, optional): Wall-clock time for the request cycle. Defaults to `0.0`.
*   `session_id` (str, optional): Optional conversation or session ID.
*   `tags` (str): Comma-separated tag string often sourced from request headers.
*   `input_k_tokens_cxjcoins` (float): Cost per 1K input tokens in CXJ coins.
*   `output_k_tokens_cxjcoins` (float): Cost per 1K output tokens in CXJ coins.
*   `request_id` (str, optional): Unique ID for the specific request.

**Returns:**
*   `TokenUsageEvent`: The persisted and recorded event object.

## Querying Analytics Data

The service offers multiple methods to query aggregated usage data across different dimensions. All query methods accept optional date filters (`start_date` and `end_date`) using inclusive ISO format dates.

### 1. Time Period Functions

#### `list_available_dates()`
Retrieves all dates for which analytics data has been recorded.
**Returns:** A sorted list of strings in the `YYYY-MM-DD` format.

#### `get_usage_by_model(...)`
Aggregates total token usage grouped by LLM model name.
**Parameters:**
*   `start_date`, `end_date`: Date range for filtering access.
*   `username` (str, optional): Filter by a specific user.
*   `project_name` (str, optional): Filter by project name.
**Returns:** A dictionary `Dict[model, {...}]` containing aggregated metrics: input tokens, output tokens, total tokens (`input + output`), number of calls, total duration, and total CXJ coins spent for that model.

#### `get_usage_by_user(...)`
Aggregates total token usage grouped by username.
**Parameters:**
*   `start_date`, `end_date`: Date range for filtering access.
*   `project_name` (str, optional): Filter by project name.
*   `project_id` (str, optional): Filter by specific project ID.
**Returns:** A dictionary `Dict[username, {...}]` containing aggregated metrics per user.

#### `get_usage_by_project(...)`
Aggregates total token usage grouped by project name.
**Parameters:**
*   `start_date`, `end_date`: Date range for filtering access.
*   `username` (str, optional): Filter by a specific user.
**Returns:** A dictionary `Dict[project_name, {...}]` containing aggregated metrics per project.

#### `get_total_usage(...)`
Calculates global total token consumption across the specified date range and filters.
**Parameters:**
*   `start_date`, `end_date`: Date range for filtering access.
*   `username` (str, optional): Filter by user.
*   `project_name` (str, optional): Filter by project name.
*   `project_id` (str, optional): Filter by project ID.
*   `model` (str, optional): Filter by model name.
**Returns:** A single dictionary containing the combined totals: `input_tokens`, `output_tokens`, `total_tokens`, `calls`, `total_duration_seconds`, and `total_cxjcoins`.

### 2. Time-Based Aggregation

#### `get_daily_usage(...)`
Provides a list of aggregated token usage metrics broken down by specified time intervals, allowing for granular tracking.
**Parameters:**
*   `start_date`, `end_date`: Date range for filtering access.
*   `username` (str, optional): Filter by user.
*   `project_name` (str, optional): Filter by project name.
*   `grouping` (str, default: `'day'`): Defines the granularity of the returned periods. Accepts `'minute'`, `'hour'`, or `'day'`.

**Returns:** A sorted list of dictionaries `List[Dict[str, Any]]`. Each dictionary contains the period identifier (`period`) and aggregated metrics for that interval.

***

### Internal Utility Method (Not for direct use)

#### `_aggregate(events: List[TokenUsageEvent], key_fn)`
\[*Internal Static Method*\]
A utility method used internally to aggregate token counts from a list of events. It takes a `key_fn` (a function that extracts the grouping key, e.g., `lambda e: e.username`) and returns a structured dictionary grouping all calculated metrics (`input_tokens`, `output_tokens`, etc.) based on that key.

## Dependencies
**Imports from:** codx/junior/analytics/model.py, codx/junior/analytics/storage.py, codx/junior/globals.py
**Imported by:** codx/junior/ai/wallet_check.py, codx/junior/analytics/__init__.py, codx/junior/api/users.py