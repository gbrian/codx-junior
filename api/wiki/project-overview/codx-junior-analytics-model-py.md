# Token Usage Event and Tool Usage Event Documentation

## Overview of TokenUsageEvent Class
The `TokenUsageEvent` class represents a single LLM call with token consumption metadata. It includes fields such as `username`, `project_name`, `model`, and `provider`, which provide context for the request and identify the usage patterns.

### Fields

*   **username**: The user who triggered the request.
*   **project_name**: The project context for the request.
*   **project_id**: The project identifier.
*   **model**: LLM model name used (e.g., "gpt-4o").
*   **provider**: LLM provider (e.g., "openai", "litellm").
*   **input_tokens**: Number of tokens in the prompt/input.
*   **output_tokens**: Number of tokens in the completion/output.
*   **total_tokens**: Sum of input + output tokens.
*   **duration_seconds**: Wall-clock seconds from first request to last chunk.
*   **timestamp**: Unix epoch timestamp of the event.
*   **iso_date**: ISO-8601 date string (YYYY-MM-DD) for partitioning.
*   **session_id**: Optional session/conversation identifier.
*   **tags**: Comma-separated tags associated with the request.
*   **input_k_tokens_cxjcoins**: Price per 1K input tokens in CXJ coins (from AISettings).
*   **output_k_tokens_cxjcoins**: Price per 1K output tokens in CXJ coins (from AISettings).
*   **total_cxjcoins**: Total cost in CXJ coins for this event.
*   **request_id**: Request id for tracebility
*   **tokens_from_provider**: Token count comes from provider's response, else they are calculated

### Behavior

The class has a behavior of computing `total_cxjcoins` from `input_tokens`, `output_tokens`, and their respective prices if not set.

### Methods

It defines two methods:

*   The `__post_init__` method which computes the total cost in CXJ coins for this event.
*   The `to_dict` method that returns a dictionary representation of the object.

### from_dict Method
The class also provides a static method to build a TokenUsageEvent from a dict, tolerating old/missing/incorrect fields and includes backwards compatibility rules.

## Dependencies
**Imported by:** codx/junior/analytics/analytics.py, codx/junior/analytics/storage.py