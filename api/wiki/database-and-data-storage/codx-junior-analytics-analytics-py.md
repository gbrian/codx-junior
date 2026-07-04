# Analytics Service (`Analytics` Class)

The `Analytics` class provides a high-level API for recording and querying LLM token usage metrics. It is designed to interact with persistent data storage to manage usage tracking across various dimensions, such as users, projects, and models.

## Initialization

To initialize the service, an instance of `Analytics` must be created, passing the global path where the analytics data resides.

**`__init__(self, analytics_path: str = ANALYTICS_DATA_PATH)`**

*   **`analytics_path`**: The global directory for all analytic storage. By default, it reads from `codx.junior.globals.ANALYTICS_DATA_PATH`.

## Writing Usage Data

### `record_token_usage(...)`

This method is used to record consumption details for a single LLM call event. It aggregates various metrics including token counts, duration, and calculated costs (CXJ coins).

**Parameters:**

| Parameter | Type | Description | Required/Optional |
| :--- | :--- | :--- | :--- |
| `username` | `str` | The user who triggered the call. | Required |
| `project_name` | `str` | The project context name. | Required |
| `project_id` | `str` | The unique project identifier. | Required |
| `model` | `str` | The specific LLM model used (e.g., "gpt-4"). | Required |
| `provider` | `str` | The LLM provider (e.g., "openai", "anthropic"). | Required |
| `input_tokens` | `int` | Token count for the prompt/input. | Required |
| `output_tokens` | `int` | Token count for the completion/output. | Required |
| `duration_seconds` | `float`| Wall-clock time taken by the request/response cycle. (Default: 0.0) | Optional |
| `session_id` | `Optional[str]`| Identifier for a continuous work session or conversation. | Optional |
| `tags` | `str` | Comma-separated tag string from request headers. (Default: "") | Optional |
| `input_k_tokens_cxjcoins` | `float`| Price per 1K input tokens in CXJ coins. (From `AISettings`) | Required |
| `output_k_tokens_cxjcoins` | `float`| Price per 1K output tokens in CXJ coins. (From `AISettings`) | Required |
| `request_id` | `str` | Unique identifier for the specific API request. (Default: None) | Optional |
| `tokens_from_provider` | `bool` | Indicates if token count originated directly from the provider. (Default: `False`) | Optional |

**Returns:**

*   `TokenUsageEvent`: The persisted event object containing all recorded data points.

## Querying Analytics Data

The following methods retrieve aggregated usage statistics based on various filters and grouping levels. All query methods first read raw events using `self.storage.read_events()` before aggregation (`_aggregate`).

### 1. Global Usage Totals

**`get_total_usage(...)`**
Returns a dictionary containing cumulative token totals, call counts, and costs across all filtered events.

*   **Parameters:**
    *   `start_date`: Optional start date (ISO format, inclusive).
    *   `end_date`: Optional end date (ISO format, inclusive).
    *   `username`: Optional user filter.
    *   `project_name`: Optional project filter.
    *   `project_id`: Optional project ID filter.
    *   `model`: Optional model name filter.
*   **Returns:** `Dict[str, Any]` containing the totals for: `input_tokens`, `output_tokens`, `total_tokens`, `calls`, `total_duration_seconds`, `total_cxjcoins`, and `tokens_from_provider`.

### 2. Usage Grouped by Dimensions (Dictionary Output)

These methods aggregate usage, returning a dictionary where the key is the grouping dimension (e.g., username), and the value is a detailed metrics dictionary for that group.

**`get_usage_by_user(...)`**
Aggregates token usage grouped by individual `username`.

*   **Parameters:** Filters include `start_date`, `end_date`, `project_name`, and `project_id`.
*   **Returns:** `Dict[username, {metrics}]`

**`get_usage_by_project(...)`**
Aggregates token usage grouped by `project_name`.

*   **Parameters:** Filters include `start_date`, `end_date`, and optional `username`.
*   **Returns:** `Dict[project_name, {metrics}]`

**`get_usage_by_model(...)`**
Aggregates token usage grouped by specific `model` name.

*   **Parameters:** Filters include `start_date`, `end_date`, optional `username`, and `project_name`.
*   **Returns:** `Dict[model, {metrics}]`

### 3. Period-Specific Usage (List Output)

**`get_daily_usage(...)`**
Retrieves per-period aggregated token usage with configurable temporal grouping. The results are returned as a list of dictionaries, sorted by the period key ascendingly.

*   **Parameters:**
    *   `start_date`: Optional start date (ISO format, inclusive).
    *   `end_date`: Optional end date (ISO format, inclusive).
    *   `username`: Optional user filter.
    *   `project_name`: Optional project filter.
    *   `grouping`: The time granularity level: `'day'` (default), `'hour'`, or `'minute'`.
*   **Returns:** `List[Dict[str, Any]]` containing the period key (`period`) and aggregate metrics for that interval.

### 4. Utility Methods

**`list_available_dates()`**
Retrieves all available dates with stored analytics data.

*   **Parameters:** None.
*   **Returns:** `List[str]` of sorted date strings in `YYYY-MM-DD` format, representing days for which usage is recorded.

## Dependencies
**Imports from:** codx/junior/analytics/model.py, codx/junior/analytics/storage.py, codx/junior/globals.py
**Imported by:** codx/junior/ai/wallet_check.py, codx/junior/analytics/__init__.py, codx/junior/api/users.py