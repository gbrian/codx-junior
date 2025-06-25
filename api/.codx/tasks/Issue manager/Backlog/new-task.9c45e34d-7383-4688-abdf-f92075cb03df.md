# [[{"id": "9c45e34d-7383-4688-abdf-f92075cb03df", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/home/codx-junior/codx-junior/api/codx/junior/misc/github.py", "/home/codx-junior/codx-junior/api/codx/junior/api/github.py"], "profiles": ["software_developer"], "users": ["admin"], "name": "New Task", "description": "In this conversation, the user requested a new method in the `github.py` file to download GitHub issue information using a given URL and return JSON data embedded in the HTML. The task involved updating the API to parse the HTML for the JSON script identified as `react-app.embeddedData`. I provided detailed instructions and code on how to implement this method, ensuring it includes proper headers for web requests, JSON parsing, error handling, and explanatory comments for complex logic. Finally, the enhancements offered a straightforward way to extract detailed JSON data from individual GitHub issue pages.", "created_at": "2025-05-28 13:24:47.065517", "updated_at": "2025-05-28T14:19:43.654055", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Issue manager", "column": "Backlog", "chat_index": 0, "url": "", "branch": "", "file_path": "", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "8102fcd2-decf-4f94-bec1-e02ea17ef84e", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-28 13:24:47.063693", "updated_at": "2025-05-28 13:24:47.063777", "images": [], "files": ["/home/codx-junior/codx-junior/api/codx/junior/misc/github.py", "/home/codx-junior/codx-junior/api/codx/junior/api/github.py"], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": []}]]
@file://github.py add new method to download github issue information, will receive the url of the issue and return json extracted from the line having "react-app.embeddedData"


## [[{"doc_id": "85465b60-66ba-466e-9094-155013e746a3", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-28 13:24:47.063693", "updated_at": "2025-05-28 13:24:47.063777", "images": [], "files": [], "meta_data": {"time_taken": 9.04860234260559, "first_chunk_time_taken": 3.494361400604248, "model": "gpt-4o"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
To enhance the module with a new method to download GitHub issue information, you will need to create a function similar to `search_github_issues` that fetches data from a single issue URL. This new function will extract JSON data embedded within the HTML content of the issue page, specifically from a script tag that contains the identifier `react-app.embeddedData`. Here is how you can implement it:

```python
# File: /home/codx-junior/codx-junior/api/codx/junior/misc/github.py

import requests
import json
import os
import time

CACHE_FILE = 'cache.json'
CACHE_EXPIRATION = 3 * 86400  # 3 days in seconds

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
            if time.time() - cache_data.get('timestamp', 0) < CACHE_EXPIRATION:
                return cache_data.get('results', [])
    return None

def save_cache(results):
    with open(CACHE_FILE, 'w') as f:
        json.dump({'timestamp': time.time(), 'results': results}, f)

def search_github_issues():
    """
    Searches GitHub for issues labeled as "help wanted", with a cached
    response for 3 days to enhance performance.

    :return: Data contained in the 'results' key of the JSON if available, otherwise the full response text.
    :raises: ValueError if the JSON cannot be decoded.
    """
    cached_results = load_cache()
    if cached_results is not None:
        return cached_results

    url = "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc"
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error on a failed request

    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            
            try:
                json_data = json.loads(json_text)
                results = json_data["payload"]["results"]
                save_cache(results)
                return results
            except json.JSONDecodeError as e:
                raise ValueError("Error decoding JSON content.") from e

    # If the JSON data is not found, return the full response content
    return response.text

def download_issue_info(issue_url):
    """
    Downloads issue information from a given GitHub issue URL, extracting
    JSON data from the specified line containing 'react-app.embeddedData'.

    :param issue_url: URL of the GitHub issue.
    :return: JSON data extracted from the specified line.
    :raises: ValueError if the JSON cannot be decoded.
    """
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    }

    # Make a request to the provided GitHub issue URL with appropriate headers.
    response = requests.get(issue_url, headers=headers)
    response.raise_for_status()  # Raise an error for failed requests like 404, 500, etc.

    # Iterate through each line in the response to find the required script tag.
    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            # Extract JSON block between the tag and convert it as JSON
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            
            try:
                issue_json_data = json.loads(json_text)
                return issue_json_data
            except json.JSONDecodeError as e:
                # Raise a ValueError if JSON decoding fails.
                raise ValueError("Error decoding JSON content from issue page.") from e

    # If the specific JSON data is not found, return an indicative message.
    return "React app data not found in the issue page."

```

### Explanation:

1. **Function Definition**: The new method, `download_issue_info`, is defined to accept an `issue_url` parameter. It uses this URL to fetch the issue page.

2. **Headers for Request**: The function makes a GET request using headers to mimic a web browser, helping to avoid potential content restrictions on API requests.

3. **Parsing HTML**: It parses the HTML line-by-line to find the `<script>` tag containing `react-app.embeddedData`. This helps locate the JSON we want to extract.

4. **JSON Parsing**: It extracts the JSON data from the `<script>` tag content and loads it with `json.loads()`.

5. **Error Handling**: If JSON parsing fails (e.g., due to malformed data), it raises a `ValueError`.

6. **Return Value**: Returns the extracted JSON data as a dictionary for easy access to individual elements.

This complete function can now be used as part of the module to pull specific data from any GitHub issue when given a valid URL.