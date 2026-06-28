# TokenUsageEvent Model

The `TokenUsageEvent` is a data structure used to track LLM call metadata, including token consumption, cost calculation in CXJ coins, and usage analytics. It is implemented as a dataclass to ensure structured data handling across the analytics pipeline.

## Overview
This model captures the lifecycle and cost of an LLM request. It records details such as the user, project, model provider, and token-level consumption, providing both raw usage data and calculated financial metrics.

## Data Fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `username` | `str` | The user who triggered the request. |
| `project_name` | `str` | The project context for the request. |
| `project_id` | `str` | The project identifier. |
| `model` | `str` | LLM model name used (e.g., "gpt-4o"). |
| `provider` | `str` | LLM provider (e.g., "openai", "litellm"). |
| `input_tokens` | `int` | Number of tokens in the prompt/input. |
| `output_tokens` | `int` | Number of tokens in the completion/output. |
| `total_tokens` | `int` | Sum of input + output tokens. |
| `duration_seconds` | `float` | Wall-clock seconds from first request to last chunk. |
| `timestamp` | `float` | Unix epoch timestamp of the event. |
| `iso_date` | `str` | ISO-8601 date string (YYYY-MM-DD) for partitioning. |
| `session_id` | `Optional[str]` | Optional session/conversation identifier. |
| `tags` | `str` | Comma-separated tags associated with the request. |
| `input_k_tokens_cxjcoins` | `float` | Price per 1K input tokens in CXJ coins. |
| `output_k_tokens_cxjcoins` | `float` | Price per 1K output tokens in CXJ coins. |
| `total_cxjcoins` | `float` | Total cost in CXJ coins for this event. |
| `request_id` | `str` | Request ID for traceability. |
| `tokens_from_provider` | `bool` | Indicates if token counts were provided by the API; otherwise, calculated. |

## Lifecycle and Logic

### Cost Calculation
The `__post_init__` method automatically calculates the `total_cxjcoins` if it is not provided during initialization. The calculation logic is:
* `input_cost = (input_tokens / 1000.0) * input_k_tokens_cxjcoins`
* `output_cost = (output_tokens / 1000.0) * output_k_tokens_cxjcoins`
* `total_cxjcoins = input_cost + output_cost`

### Serialization
* **`to_dict()`**: Exports the model instance as a dictionary using `asdict`.
* **`from_dict(data)`**: A class method used to reconstruct the object from a dictionary.

## Backwards Compatibility
The `from_dict` method includes logic to handle legacy data structures:
* **Legacy Pricing**: If the input dictionary contains the field `k_tokens_cxjcoins` (instead of the modern split `input_k_tokens_cxjcoins` and `output_k_tokens_cxjcoins`), the value is applied to both pricing fields.
* **Error Resilience**: The method performs type coercion and gracefully handles missing or incompatible fields by falling back to the dataclass defaults.

---

### References
* [codx/junior/analytics/model.py](file:///codx/junior/analytics/model.py)

## Dependencies
**Imported by:** codx/junior/analytics/analytics.py, codx/junior/analytics/storage.py