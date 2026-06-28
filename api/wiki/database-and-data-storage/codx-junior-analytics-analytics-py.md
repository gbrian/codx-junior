# Analytics Service API Reference

The `Analytics` class provides a high-level interface for recording, storing, and querying usage metrics related to LLM tokens consumed across various projects and models. By utilizing this service, applications can track resource consumption (tokens, duration, cost) over time and by specific dimensions like user or project.

## Initialization

Instantiate the `Analytics` object by providing a path to the global storage directory:

```python
analytics = Analytics(analytics_path=ANALYTICS_DATA_PATH)
```

The service internally initializes an `AnalyticsStorage` instance using the provided path (`codx.junior.globals.ANALYTICS_DATA_PATH`).

## Recording Token Usage

Use the `record_token_usage` method to log a single LLM call's token consumption event. This function bundles all necessary metadata, including user identity, project context, model details, and financial cost data (CXJ coins).

### `Analytics.record_token_usage()`

**Parameters:**

*   `username` (`str`): The user who initiated the LLM call.
*   `project_name` (`str`): Descriptive name of the project context.
*   `project_id` (`str`): Unique identifier for the project.
*   `model` (`str`): The specific LLM model used (e.g., "gpt-4").
*   `provider` (`str`): The external service provider (e.g., "OpenAI", "Anthropic").
*   `input_tokens` (`int`): Count of tokens in the prompt/input sequence.
*   `output_tokens` (`int`): Count of tokens generated in the response/completion.
*   `duration_seconds` (`float`, default `0.0`): The total wall-clock time taken for the request/response cycle.
*   `session_id` (`Optional[str]`): Identifier for an ongoing conversation or session.
*   `tags` (`str`, default `""`): Comma-separated tag string, potentially derived from request headers.
*   `input_k_tokens_cxjcoins` (`float`, default `0.0`): Calculated cost per 1K input tokens in CXJ coins (from AISettings).
*   `output_k_tokens_cxjcoins` (`float`, default `0.0`): Calculated cost per 1K output tokens in CXJ coins (from AISettings).
*   `request_id` (`Optional[str]`): Tracking ID for the specific API call request.
*   `tokens_from_provider` (`bool`, default `False`): Flag indicating if tokens were sourced directly from an external provider mechanism.

**Returns:**
A persisted instance of `TokenUsageEvent`.

## Querying Analytics Data

The service offers various querying methods to aggregate and retrieve usage statistics based on different dimensions. All query methods accept optional date range filters (`start_date` and `end_date`) in ISO format.

### 1. Aggregate Usage by User

Retrieves aggregated token usage metrics grouped by the unique `username`.

**Method Signature:**
`get_usage_by_user(start_date: Optional[str], end_date: Optional[str], project_name: Optional[str] = None, project_id: Optional[str] = None)`

**Filters:**
*   Date Range (`start_date`, `end_date`)
*   Project Name (`project_name`)
*   Project ID (`project_id`)

**Returns:**
A dictionary where keys are usernames and values are dictionaries containing aggregated statistics for that user:
`Dict[username, {input_tokens, output_tokens, total_tokens, calls, total_duration_seconds, total_cxjcoins, tokens_from_provider}]`

### 2. Aggregate Usage by Project

Retrieves token usage metrics grouped by the project's `project_name`.

**Method Signature:**
`get_usage_by_project(start_date: Optional[str], end_date: Optional[str], username: Optional[str] = None)`

**Filters:**
*   Date Range (`start_date`, `end_date`)
*   Username (`username`)

**Returns:**
A dictionary where keys are project names and values are dictionaries containing aggregated statistics for that project.

### 3. Aggregate Usage by Model

Retrieves token usage metrics grouped by the specific LLM model used.

**Method Signature:**
`get_usage_by_model(start_date: Optional[str], end_date: Optional[str], username: Optional[str] = None, project_name: Optional[str] = None)`

**Filters:**
*   Date Range (`start_date`, `end_date`)
*   Username (`username`)
*   Project Name (`project_name`)

**Returns:**
A dictionary where keys are model names and values are dictionaries containing aggregated statistics for that model.

### 4. Time-Series Usage (Grouping)

This function calculates usage totals segmented into configurable time periods, making it suitable for trend analysis.

**Method Signature:**
`get_daily_usage(start_date: Optional[str], end_date: Optional[str], username: Optional[str] = None, project_name: Optional[str] = None, grouping: str = "day")`

**Parameters:**
*   Date Range (`start_date`, `end_date`)
*   Username (`username`): Optional user filter.
*   Project Name (`project_name`): Optional project filter.
*   Grouping (`grouping`): The time granularity for aggregation. Accepts `'minute'`, `'hour'`, or `'day'`. Defaults to `'day'`.

**Returns:**
A sorted list of dictionaries, where each dictionary represents a specific time period and contains aggregated metrics:
`List[{period, input_tokens, output_tokens, total_tokens, calls, total_duration_seconds, total_cxjcoins, tokens_from_provider}]`

### 5. Global Total Usage

Returns a single summary dictionary containing the cumulative token totals across all specified filters and events.

**Method Signature:**
`get_total_usage(start_date: Optional[str], end_date: Optional[str], username: Optional[str] = None, project_name: Optional[str] = None, project_id: Optional[str] = None, model: Optional[str] = None)`

**Filters:**
*   Date Range (`start_date`, `end_date`)
*   Username (`username`): Optional user filter.
*   Project Name (`project_name`): Optional project filter.
*   Project ID (`project_id`): Optional project identifier filter.
*   Model (`model`): Optional model name filter.

**Returns:**
A dictionary containing the sum of all metrics across the filtered dataset:
`Dict with keys: input_tokens, output_tokens, total_tokens, calls, total_duration_seconds, total_cxjcoins, tokens_from_provider.`

### Utility Methods

#### `list_available_dates()`
Returns a sorted list of dates available in the analytics storage, formatted as `"YYYY-MM-DD"`.

## Dependencies
**Imports from:** codx/junior/analytics/model.py, codx/junior/analytics/storage.py, codx/junior/globals.py
**Imported by:** codx/junior/ai/wallet_check.py, codx/junior/analytics/__init__.py, codx/junior/api/users.py