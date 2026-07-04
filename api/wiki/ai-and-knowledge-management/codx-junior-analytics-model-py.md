## TokenUsageEvent Object Documentation

The `TokenUsageEvent` dataclass is designed to hold comprehensive metadata about a single Large Language Model (LLM) call, specifically tracking token consumption and associated costs. It ensures that detailed records are maintained for analysis and billing purposes, including timing information and project context.

### Fields

| Field Name | Type | Description | Default/Notes |
| :--- | :--- | :--- | :--- |
| `username` | `str` | The user who triggered the request. | Required string input. |
| `project_name` | `str` | The project context for the request. | Required string input. |
| `project_id` | `str` | The unique identifier for the project. | Required string input. |
| `model` | `str` | The specific LLM model name used (e.g., "gpt-4o"). | Required string input. |
| `provider` | `str` | The LLM provider used (e.g., "openai", "litellm"). | Required string input. |
| `input_tokens` | `int` | The count of tokens provided in the prompt/input. | Defaults to 0. |
| `output_tokens` | `int` | The count of tokens generated in the completion/output. | Defaults to 0. |
| `total_tokens` | `int` | The sum of input and output tokens (`input_tokens + output_tokens`). | Calculated total token count. |
| `duration_seconds` | `float` | Wall-clock time elapsed from the first request to the last chunk completion. | Defaults to 0.0. |
| `timestamp` | `float` | The Unix epoch timestamp marking when the event occurred. | Default is the current time (`time.time`). |
| `iso_date` | `str` | The date in ISO-8601 format (YYYY-MM-DD), used for data partitioning. | Defaults to today's ISO date string. |
| `session_id` | `Optional[str]` | An optional identifier used if the request is part of a multi-turn conversation or session. | Optional, defaults to `None`. |
| `tags` | `str` | Comma-separated tags associated with the specific request event. | Defaults to an empty string (`""`). |
| `input_k_tokens_cxjcoins`| `float` | The cost price per 1K input tokens, defined in CXJ coins (read from AISettings). | Defaults to 0.0. |
| `output_k_tokens_cxjcoins`| `float` | The cost price per 1K output tokens, defined in CXJ coins (read from AISettings). | Defaults to 0.0. |
| `total_cxjcoins` | `float` | Total computed cost incurred by this event across all resources. | Calculated total cost. If initialized to 0.0, it is calculated during initialization (`__post_init__`). |
| `request_id` | `str` | A unique ID used for tracing and tracking the specific request. | Optional string identifier. |
| `tokens_from_provider`| `bool` | A flag indicating whether the token count was sourced directly from the provider's response, or if it was calculated internally. | Defaults to `False`. |

### Methods and Utility

#### `__post_init__(self)`
This method executes automatically after the object is initialized. If the `total_cxjcoins` field has not been explicitly set (i.e., it equals 0.0), this method calculates and sets the final total cost based on the provided token counts and the respective input/output pricing factors (`input_k_tokens_cxjcoins`, `output_k_tokens_cxjcoins`).

#### `to_dict(self)`
Converts the instance of the `TokenUsageEvent` object into a standard Python dictionary, making it easily serializable. It utilizes `asdict()`.

#### `@classmethod from_dict(cls, data: dict) -> "TokenUsageEvent"`
This class method is responsible for building and validating an instance from a provided dictionary (`data`). It incorporates robust **backwards-compatibility** rules to ensure graceful handling of older or incomplete records:
*   **Legacy Pricing Support:** If the input dictionary contains an old field called `k_tokens_cxjcoins`, this method interprets it and automatically sets both `input_k_tokens_cxjcoins` and `output_k_tokens_cxjcoins` to that value.
*   **Type Safety:** It attempts type coercion for primitive types (like integers and floats) and falls back to a default if any field is missing or the provided data type is incompatible.

## Dependencies
**Imported by:** codx/junior/analytics/analytics.py, codx/junior/analytics/storage.py