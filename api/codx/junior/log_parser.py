import re
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
            "url": url_match.group('url'),
            "status_code": status_code_match.group('status_code'),
            "time_taken": url_match.group('time_taken')
        }
    
    # Return None if no request info is found
    return None

EXTRACTORS = [request_extractor]

def parse_logs(log_stream: str) -> List[Dict[str, str]]:
    log_entries = []
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
            log_entries.append(entry)

    for line in log_stream.splitlines():
        match = log_pattern.match(line)
        if match:
            # If there's a match, it indicates a new log entry
            if log_entry:
                # Append the accumulated log entry to the list
                add_log_entry(log_entry)
            
            # Start a new log entry
            log_entry = {
                "timestamp": match.group('timestamp'),
                "level": match.group('level'),
                "module": match.group('module'),
                "line": int(match.group('line')),
                "content": match.group('content').strip()
            }
            log_entry["id"] = f"{log_entry['timestamp']}:{log_entry['level']}:{log_entry['module']}:{log_entry['line']}"
        elif log_entry:
            # Accumulate content lines that are part of the previous log entry
            log_entry["content"] += "\n" + line.strip()

    # Don't forget to add the last log entry
    if log_entry:
        add_log_entry(log_entry)

    return log_entries