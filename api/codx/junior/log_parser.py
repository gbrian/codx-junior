import re
import json
from typing import List, Dict, Optional

def request_extractor(content: str) -> Optional[Dict[str, str]]:
    # Define regex patterns to capture url, status_code, and time_taken
    url_pattern = re.compile(
        r'Request\s+(?P<url>https?://[^\s]+)\s+-\s+(?P<time_taken>\d+\.\d+)\s+ms'
    )
    status_code_pattern = re.compile(
        r'\s"(?P<method>GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\s+[^\s]+\s+HTTP/1.1"\s+(?P<status_code>\d{3})'
    )

    # Attempt to match patterns in the content
    url_match = url_pattern.search(content.strip().split("\n")[0])
    status_code_match = status_code_pattern.search(content)

    if url_match and status_code_match:
        # Extract and return the information if both patterns are matched
        return {
            "request": {
                "url": url_match.group('url'),
                "status_code": status_code_match.group('status_code'),
                "time_taken": float(url_match.group('time_taken')),
                "method": status_code_match.group('method')
            }
        }
    
    # Return None if no request info is found
    return None

def profiler_extractor(content: str) -> Optional[Dict[str, str]]:
    # Define a regex pattern to capture the profiler message
    profiler_pattern = re.compile(
        r'Profiler:\s+(?P<profiler_data>\{.*\})'
    )

    # Attempt to match the pattern in the content
    match = profiler_pattern.search(content)

    if match:
        # Extract the JSON-like content
        profiler_data_str = match.group('profiler_data')
        try:
            # Parse the JSON-like string to a dict
            profiler_data = json.loads(profiler_data_str)
            return { "profiler": profiler_data }
        except json.JSONDecodeError:
            # Handle invalid JSON format
            return None
    
    # Return None if no profiler info is found
    return None

EXTRACTORS = [request_extractor, profiler_extractor]

def parse_logs(log_stream: str) -> List[Dict[str, str]]:
    log_entries = {}
    log_entry = None

    # Define the regex pattern for log lines
    log_pattern = re.compile(
        r'^\[(?P<timestamp>[^\]]+)\]\s+(?P<level>\w+)\s+\[(?P<module>[^\]:]*):(?P<line>\d+)\]\s+(?P<content>.*)$'
    )

    def add_log_entry(entry):
        entry["data"] = {}
        for extactor in EXTRACTORS:
            data = extactor(entry["content"])
            if data:
                entry["data"] = { **entry["data"], **data }
            log_entries[entry["id"]] = entry

    for line in log_stream.splitlines():
        match = log_pattern.match(line)
        if match:
            # If there's a match, it indicates a new log entry            
            # Start a new log entry
            log_entry = {
                "timestamp": match.group('timestamp'),
                "level": match.group('level'),
                "module": match.group('module'),
                "line": int(match.group('line')),
                "content": match.group('content').strip()
            }
            log_entry["id"] = f"{log_entry['timestamp']}:{log_entry['level']}:{log_entry['module']}:{log_entry['line']}"
            # Append the accumulated log entry to the list
            add_log_entry(log_entry)
        elif log_entry:
            # Accumulate content lines that are part of the previous log entry
            log_entry["content"] += "\n" + line.strip()
        else:
            log_entry = {
                "timestamp": "",
                "level": "",
                "module": "",
                "line": "",
                "id": line,
                "content": line
            }
            add_log_entry(log_entry)
            log_entry = None

    return list(log_entries.values())