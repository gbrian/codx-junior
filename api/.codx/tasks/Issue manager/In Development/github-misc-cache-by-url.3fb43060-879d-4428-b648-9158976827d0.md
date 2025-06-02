# [[{"id": "3fb43060-879d-4428-b648-9158976827d0", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/codx/junior/misc/github.py"], "profiles": ["software_developer"], "users": ["admin"], "name": "github misc cache by url", "description": "1. The user requested modifications to cache GitHub API responses based on URL, not globally, and to use the system's temporary directory for storage.  \n2. I provided a comprehensive update to the `github.py` file, replacing the cache logic with per-URL files located in `tempfile.gettempdir()`.  \n3. The code was enhanced with proper logging, type hints, and detailed comments to improve maintainability and traceability.  \n4. Emphasis was placed on carefully analyzing existing code before making changes to preserve essential content.  \n5. The resulting code now dynamically caches responses per URL in the system's temp folder, ensuring better cache management and clarity.", "created_at": "2025-05-31 10:14:37.526949", "updated_at": "2025-05-31T10:21:58.693824", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Issue manager", "column": "In Development", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/api/.codx/tasks/Issue manager/In Development/github-misc-cache-by-url.3fb43060-879d-4428-b648-9158976827d0.md", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "d2cf81c4-6714-4b75-992d-f629136403f0", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-31 10:14:37.525203", "updated_at": "2025-05-31 10:14:37.525240", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": []}]]
@codx-api all methods like search_github_issues must cache by url not global, use the url as file cache name
## [[{"doc_id": "2200422b-312b-4c9b-8c2e-7eec62aae750", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-31 10:17:54.382402", "updated_at": "2025-05-31 10:17:54.382440", "images": [], "files": [], "meta_data": {"time_taken": 24.04345989227295, "first_chunk_time_taken": 15.349470138549805, "model": "gpt-4.1-nano"}, "profiles": ["software_developer", "software_developer"], "user": null, "knowledge_topics": []}]]
***Begin patch***


***Full file content with modifications***


```python
import requests
import json
import os
import time
import logging
from typing import List, Optional, Union, Dict, Any

# Configure logger for the module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = 'cache_files'
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Defining a class to store comment details alongside its summary
class IssueComment:
    """
    Represents a comment on a GitHub issue with relevant details.
    """

    def __init__(
        self,
        createdAt: str,
        author: str,
        body: str,
        summary: str,
        url: str,
        authorAssociation: str
    ):
        """
        Initialize IssueComment with all required fields.
        """
        self.createdAt: str = createdAt
        self.author: str = author
        self.body: str = body
        self.summary: str = summary
        self.url: str = url
        self.authorAssociation: str = authorAssociation


class Issue:
    """
    Represents a GitHub issue with its title and associated comments.
    """

    def __init__(self, title: str, url: str, comments: Optional[List[IssueComment]] = None):
        """
        Initialize Issue with a title and optional list of comments.
        """
        self.title: str = title
        self.url: str = url
        self.comments: List[IssueComment] = comments if comments is not None else []

def get_cache_filename(url: str) -> str:
    """
    Generate a cache filename based on the URL.
    """
    safe_filename = url.replace('/', '_').replace(':', '_').replace('?', '_').replace('&', '_').replace('=', '_')
    return os.path.join(CACHE_DIR, f"{safe_filename}.json")


def load_cache_for_url(url: str) -> Optional[Any]:
    """
    Load cached data for the given URL if available and valid.
    """
    cache_file = get_cache_filename(url)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                timestamp = cache_data.get('timestamp', 0)
                if time.time() - timestamp < 3 * 86400:
                    logger.info("Loaded cache for URL: %s", url)
                    return cache_data.get('results')
                else:
                    logger.info("Cache expired for URL: %s", url)
        except Exception as e:
            logger.warning("Failed to load cache for URL: %s, error: %s", url, e)
    return None

def save_cache_for_url(url: str, results: Any):
    """
    Save results to cache for the given URL.
    """
    cache_file = get_cache_filename(url)
    try:
        with open(cache_file, 'w') as f:
            json.dump({'timestamp': time.time(), 'results': results}, f)
        logger.info("Cache saved for URL: %s", url)
    except Exception as e:
        logger.warning("Failed to save cache for URL: %s, error: %s", url, e)


def search_github_issues(url: str = None) -> Union[List[Dict], str]:
    """
    Searches GitHub for issues labeled as "help wanted" with per-URL caching.

    :param url: The URL to fetch data from. If None, uses the default search URL.
    :return: List of results or response text if JSON is not found.
    """
    if url is None:
        url = "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc"

    # Check cache first
    cached_results = load_cache_for_url(url)
    if cached_results is not None:
        logger.info("Returning cached results for URL: %s", url)
        return cached_results

    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/136.0.0.0 Safari/537.36",
    }

    logger.info("Making request to GitHub search URL: %s", url)
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        logger.error("HTTP error occurred: %s", e)
        raise

    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            try:
                json_data = json.loads(json_text)
                results = json_data["payload"]["results"]
                save_cache_for_url(url, results)
                return results
            except json.JSONDecodeError as e:
                logger.error("JSON decoding error: %s", e)
                raise ValueError("Error decoding JSON content.") from e
    logger.warning("JSON data not found in response for URL: %s", url)
    return response.text


def download_issue_info(issue_url: str) -> Union[Issue, str]:
    """
    Downloads issue information from a given GitHub issue URL, extracting JSON data from the page.

    :param issue_url: URL of the GitHub issue.
    :return: Issue object with comments or string if data not found.
    """
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/136.0.0.0 Safari/537.36",
    }

    logger.info("Fetching issue data from URL: %s", issue_url)
    response = requests.get(issue_url, headers=headers)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        logger.error("HTTP error occurred: %s", e)
        raise

    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            try:
                issue_json_data = json.loads(json_text)
                issue_data = issue_json_data["payload"]["preloadedQueries"][0]["result"]["data"]["repository"]["issue"]
                nodes = issue_data["frontTimelineItems"]["edges"]
                comments: List[IssueComment] = []
                for node in nodes:
                    n = node["node"]
                    if n.get("__typename") == "IssueComment":
                        comment = IssueComment(
                            author=n["author"]["login"],
                            body=n["body"],
                            createdAt=n["createdAt"],
                            url=n["url"],
                            authorAssociation=n["authorAssociation"],
                            summary=None
                        )
                        comments.append(comment)
                return Issue(
                    title=issue_data["title"],
                    url=issue_url,
                    comments=comments
                )
            except json.JSONDecodeError as e:
                logger.error("JSON decoding error in issue data: %s", e)
                raise ValueError("Error decoding JSON content from issue page.") from e
    logger.warning("React app data not found in the issue page at URL: %s", issue_url)
    return "React app data not found in the issue page."

```


***End of patch***
## [[{"doc_id": "12d77989-1425-4c4f-9e72-207bc6d46746", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-31 10:17:54.382402", "updated_at": "2025-05-31 10:17:54.382440", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": []}]]
Use os temp folder for cache
## [[{"doc_id": "e027ad05-0e38-4e0c-9da0-d04820122ba4", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-31 10:17:54.382402", "updated_at": "2025-05-31 10:17:54.382440", "images": [], "files": [], "meta_data": {"time_taken": 15.918222188949585, "first_chunk_time_taken": 3.8751983642578125, "model": "gpt-4.1-nano"}, "profiles": ["software_developer", "software_developer"], "user": null, "knowledge_topics": []}]]
***Begin full file content with requested modifications***


```python
import requests
import json
import os
import time
import tempfile
import logging
from typing import List, Optional, Union

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Define cache directory in the system's temporary folder
CACHE_DIR = os.path.join(tempfile.gettempdir(), 'github_cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Cache expiration time in seconds (3 days)
CACHE_EXPIRATION = 3 * 86400  # 259200 seconds

class IssueComment:
    """
    Represents a comment on a GitHub issue with relevant details.
    """
    def __init__(
        self,
        createdAt: str,
        author: str,
        body: str,
        summary: str,
        url: str,
        authorAssociation: str
    ):
        """
        Initialize an IssueComment instance.

        :param createdAt: Timestamp when the comment was created.
        :param author: Username of the comment author.
        :param body: Text content of the comment.
        :param summary: Summary of the comment.
        :param url: URL of the comment.
        :param authorAssociation: Author's association with the repository.
        """
        self.createdAt: str = createdAt
        self.author: str = author
        self.body: str = body
        self.summary: str = summary
        self.url: str = url
        self.authorAssociation: str = authorAssociation


class Issue:
    """
    Represents a GitHub issue with its title, URL, and comments.
    """
    def __init__(
        self,
        title: str,
        url: str,
        comments: Optional[List[IssueComment]] = None
    ):
        """
        Initialize an Issue instance.

        :param title: Title of the issue.
        :param url: URL of the issue.
        :param comments: List of IssueComment instances related to the issue.
        """
        self.title: str = title
        self.url: str = url
        self.comments: List[IssueComment] = comments if comments is not None else []


def get_cache_filepath(url: str) -> str:
    """
    Generate a safe cache file path within the system's temporary directory based on the URL.

    :param url: The URL to generate cache filename for.
    :return: Full path to the cache file.
    """
    # Sanitize URL to create a filename
    safe_filename = url.replace('/', '_').replace(':', '_').replace('?', '_').replace('&', '_').replace('=', '_')
    return os.path.join(CACHE_DIR, f"{safe_filename}.json")


def load_cache_for_url(url: str) -> Optional[Union[List, str]]:
    """
    Loads cached results for the given URL if cache exists and is valid.

    :param url: The URL whose cache is to be loaded.
    :return: Cached data (list) if valid, None otherwise.
    """
    cache_filepath = get_cache_filepath(url)
    if os.path.exists(cache_filepath):
        try:
            with open(cache_filepath, 'r') as cache_file:
                cache_data = json.load(cache_file)
                timestamp = cache_data.get('timestamp', 0)
                if time.time() - timestamp < CACHE_EXPIRATION:
                    logger.info("Loaded valid cache for URL: %s", url)
                    return cache_data.get('results')
                else:
                    logger.info("Cache expired for URL: %s", url)
        except Exception as e:
            logger.warning("Failed to load cache for URL: %s, error: %s", url, e)
    return None


def save_cache_for_url(url: str, results: Union[List, str]) -> None:
    """
    Save results to cache file for the specified URL.

    :param url: The URL to associate with the cache.
    :param results: The results data to cache.
    """
    cache_filepath = get_cache_filepath(url)
    try:
        with open(cache_filepath, 'w') as cache_file:
            json.dump({'timestamp': time.time(), 'results': results}, cache_file)
        logger.info("Saved cache for URL: %s", url)
    except Exception as e:
        logger.warning("Failed to save cache for URL: %s, error: %s", url, e)


def search_github_issues(url: Optional[str] = None) -> Union[List, str]:
    """
    Search GitHub issues labeled 'help wanted' with per-URL caching.

    :param url: Optional URL to fetch data from; if None, defaults to GitHub search.
    :return: List of results or response text if JSON parsing fails.
    """
    if url is None:
        url = "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc"

    # Check cache first
    cached_results = load_cache_for_url(url)
    if cached_results is not None:
        logger.info("Returning cached results for URL: %s", url)
        return cached_results

    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/136.0.0.0 Safari/537.36",
    }

    try:
        logger.info("Making request to URL: %s", url)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info("Request successful for URL: %s", url)
    except requests.RequestException as e:
        logger.error("HTTP request failed for URL: %s, error: %s", url, e)
        raise

    # Parse the response for JSON embedded in script tag
    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            try:
                json_data = json.loads(json_text)
                results = json_data["payload"]["results"]
                save_cache_for_url(url, results)
                logger.info("Parsed and cached results for URL: %s", url)
                return results
            except json.JSONDecodeError as e:
                logger.error("JSON decoding error for URL: %s, error: %s", url, e)
                raise ValueError("Error decoding JSON content.") from e

    logger.warning("JSON data not found in response for URL: %s", url)
    # Return full response text if JSON not found
    return response.text


def download_issue_info(issue_url: str) -> Union[Issue, str]:
    """
    Fetch and parse issue data from a GitHub issue page URL, extracting JSON embedded in React app data.

    :param issue_url: The URL of the GitHub issue.
    :return: Issue object with comments or a string message if parsing fails.
    """
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/136.0.0.0 Safari/537.36",
    }

    try:
        logger.info("Fetching issue page: %s", issue_url)
        response = requests.get(issue_url, headers=headers)
        response.raise_for_status()
        logger.info("Issue page fetched successfully: %s", issue_url)
    except requests.RequestException as e:
        logger.error("Failed to fetch issue URL: %s, error: %s", issue_url, e)
        raise

    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            try:
                issue_json_data = json.loads(json_text)
                issue_data = issue_json_data['payload']['preloadedQueries'][0]['result']['data']['repository']['issue']
                nodes = issue_data['frontTimelineItems']['edges']
                comments: List[IssueComment] = []
                for node in nodes:
                    comment_node = node.get('node', {})
                    if comment_node.get('__typename') == 'IssueComment':
                        comment = IssueComment(
                            createdAt=comment_node['createdAt'],
                            author=comment_node['author']['login'],
                            body=comment_node['body'],
                            summary='',
                            url=comment_node['url'],
                            authorAssociation=comment_node['authorAssociation']
                        )
                        comments.append(comment)
                issue = Issue(
                    title=issue_data['title'],
                    url=issue_url,
                    comments=comments
                )
                logger.info("Parsed issue data with comments from URL: %s", issue_url)
                return issue
            except json.JSONDecodeError as e:
                logger.error("JSON decoding error on issue page: %s, error: %s", issue_url, e)
                raise ValueError("Error decoding JSON content from issue page.") from e

    logger.warning("React app embedded data not found in issue page: %s", issue_url)
    return "React app data not found in the issue page."
```

***End of full file content with modifications***