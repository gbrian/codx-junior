## Log Parser Utility

This module provides utility functions for parsing log entries, specifically extracting request details and profiler data.

### Functions

#### `request_extractor(content: str) -> Optional[Dict[str, str]]`

This function extracts request-related information from a log entry's content. It looks for patterns that capture the URL, status code, time taken, and HTTP method.

*   **Parameters:**
    *   `content` (str): The content of a log entry.
*   **Returns:**
    *   A dictionary containing the extracted request details if found, otherwise `None`. The dictionary has the following structure:
        ```json
        {
            "request": {
                "url": "string",
                "status_code": "string",
                "time_taken": float,
                "method": "string"
            }
        }
        ```

#### `profiler_extractor(content: str) -> Optional[Dict[str, str]]`

This function extracts profiler data from a log entry's content. It specifically looks for a "Profiler:" tag followed by JSON-like data.

*   **Parameters:**
    *   `content` (str): The content of a log entry.
*   **Returns:**
    *   A dictionary containing the parsed profiler data if found and valid JSON, otherwise `None`. The dictionary has the following structure:
        ```json
        {
            "profiler": { ... profiler data ... }
        }
        ```

#### `parse_logs(log_stream: str) -> List[Dict[str, str]]`

This is the main function that parses a stream of log data. It iterates through each line, identifies individual log entries using a defined pattern, and then uses the `EXTRACTORS` list to process each entry for specific data like request and profiler information.

*   **Parameters:**
    *   `log_stream` (str): A string containing the log data, potentially with multiple lines.
*   **Returns:**
    *   A list of dictionaries, where each dictionary represents a parsed log entry with its timestamp, level, module, line number, content, and any extracted data.

### Extractor Configuration

The `EXTRACTORS` list holds references to the different extractor functions available in this module. Currently, it includes:

*   `request_extractor`
*   `profiler_extractor`

This list can be extended with new extractor functions to support parsing of additional log data formats.

```python
# /codx/junior/log_parser.py
EXTRACTORS = [request_extractor, profiler_extractor]
```