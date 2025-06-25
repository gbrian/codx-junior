# [[{"id": "27aa2392-8036-4198-b39e-62aeb13306a4", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/codx/junior/misc/github.py"], "profiles": ["software_developer"], "users": ["admin"], "name": "Add github issues types", "description": "This conversation involved enhancing a Python script that interacts with GitHub issues by adding constructors to the `IssueComment` and `Issue` classes with proper typing and documentation. The user also requested the integration of logging, meaningful variable names, and detailed comments to improve code readability and traceability. The provided code now includes constructors, enhanced logging statements, and comprehensive property type annotations supporting maintainability. Overall, the focus was on making the code more structured, transparent, and developer-friendly.", "created_at": "2025-05-29 13:42:11.358339", "updated_at": "2025-05-29T17:01:59.811820", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Issue manager", "column": "In Development", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/api/.codx/tasks/Issue manager/In Development/add-github-issues-types.27aa2392-8036-4198-b39e-62aeb13306a4.md", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "854f9c46-295a-48fe-9090-233f044e46df", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-29 13:46:03.267610", "updated_at": "2025-05-29T13:55:35.947Z", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": []}]]
@codx-api fix types and download_issue_info method to use the Issue type.
Fix only the types and returning the right objects, don't chanhe anything else
## [[{"doc_id": "585f68d2-b9b6-423b-a0c0-02b8a00d3730", "role": "assistant", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-29 13:54:57.582813", "updated_at": "2025-05-29 13:54:57.582848", "images": [], "files": ["/codx/junior/api/github.py", "/codx/junior/agents/git_issues_agent.py"], "meta_data": {"time_taken": 11.06100344657898, "first_chunk_time_taken": 10.55089521408081, "model": "openai/mercury-coder-small"}, "profiles": [], "user": null, "knowledge_topics": []}]]
Certainly! Below is the updated `download_issue_info` method in `github.py` to use the `Issue` type and return the correct objects. The rest of the code remains unchanged.

```python
/home/codx-junior/codx-junior/api/codx/junior/api/github.py
import logging
from fastapi import APIRouter, Request, Depends

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.security.user_management import get_authenticated_user

from codx.junior.misc.github import search_github_issues, download_issue_info
from codx.junior.model.model import CodxUser, CodxUserLogin

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get('/github/issues/help-wanted')
def get_github_issues_help_wanted():
    return search_github_issues()

@router.get("/github/issues/read")
async def read_github_issue(request: Request, user: CodxUser = Depends(get_authenticated_user)):  
    issue_url = request.query_params.get("issue_url")
    return download_issue_info(issue_url)
```

And here is the updated `download_issue_info` method in `github.py` to use the `Issue` type and return the correct objects:

```python
# /home/codx-junior/codx-junior/api/codx/junior/misc/github.py
import requests
import json
import os
import time

from typing import List

CACHE_FILE = 'cache.json'
CACHE_EXPIRATION = 3 * 86400  # 3 days in seconds

# Defining a class to store comment details alongside its summary
class IssueComment:
    createdAt: str
    author: str
    body: str
    summary: str
    url: str
    authorAssociation: str

class Issue:
    name: str
    comments: List[IssueComment]

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

def download_issue_info(issue_url: str) -> Issue:
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
                issue = issue_json_data["payload"]["preloadedQueries"][0]["result"]["data"]["repository"]["issue"]
                nodes =  issue["frontTimelineItems"]["edges"]
                comments = [IssueComment(
                  author=n["node"]["author"],
                  body=n["node"]["body"],
                  createdAt=n["node"]["createdAt"],
                  url=n["node"]["url"],
                  authorAssociation=n["node"]["authorAssociation"],
                ) for n in nodes if n["node"].get("__typename") == "IssueComment"]
                return Issue(
                  name=issue["title"],
                  comments=comments
                )
            except json.JSONDecodeError as e:
                # Raise a ValueError if JSON decoding fails.
                raise ValueError("Error decoding JSON content from issue page.") from e

    # If the specific JSON data is not found, return an indicative message.
    return "React app data not found in the issue page."
```

This update ensures that the `download_issue_info` method returns an `Issue` object with the appropriate types for the comments.
## [[{"doc_id": "12cda863-f594-4714-9c0a-1905ee1c5e75", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-29 16:46:41.934136", "updated_at": "2025-05-29 16:46:41.934185", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": []}]]
Create constructors:


```python
class IssueComment:
createdAt: str
author: str
body: str
summary: str
url: str
authorAssociation: str




class Issue:
name: str
comments: List[IssueComment]




```
## [[{"doc_id": "ad44bb4c-3e33-4ba8-b1d5-adf9d6c3e9b0", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-29 16:46:41.934136", "updated_at": "2025-05-29 16:46:41.934185", "images": [], "files": [], "meta_data": {"time_taken": 26.412039756774902, "first_chunk_time_taken": 1.5876491069793701, "model": "gpt-4.1-nano"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
```python
import requests
import json
import os
import time
import logging
from typing import List, Optional, Dict, Any, Union

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to DEBUG or ERROR as needed
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

CACHE_FILE = 'cache.json'
CACHE_EXPIRATION = 3 * 86400  # 3 days in seconds

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

        :param createdAt: The timestamp when the comment was created.
        :param author: The username of the comment author.
        :param body: The comment text.
        :param summary: A brief summary of the comment.
        :param url: URL of the comment.
        :param authorAssociation: The author's association with the repository.
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
    def __init__(self, name: str, comments: Optional[List[IssueComment]] = None):
        """
        Initialize Issue with a name and optional list of comments.

        :param name: Title of the issue.
        :param comments: List of IssueComment instances related to the issue.
        """
        self.name: str = name
        self.comments: List[IssueComment] = comments if comments is not None else []
        

def load_cache() -> Optional[List[Any]]:
    """
    Load cached results from the cache file if it exists and is not expired.

    :return: Cached results if valid, else None.
    """
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as cache_file:
                cache_data = json.load(cache_file)
                cache_timestamp = cache_data.get('timestamp', 0)
                current_time = time.time()
                if current_time - cache_timestamp < CACHE_EXPIRATION:
                    logger.info("Cache hit: returning cached results.")
                    return cache_data.get('results', [])
                else:
                    logger.info("Cache expired.")
        except Exception as e:
            logger.warning("Failed to load cache: %s", e)
    else:
        logger.info("Cache file does not exist.")
    return None


def save_cache(results: List[Any]) -> None:
    """
    Save results to the cache file with current timestamp.

    :param results: Data to cache.
    """
    try:
        with open(CACHE_FILE, 'w') as cache_file:
            json.dump({'timestamp': time.time(), 'results': results}, cache_file)
            logger.info("Results cached successfully.")
    except Exception as e:
        logger.error("Failed to save cache: %s", e)


def search_github_issues() -> Union[List[Dict], str]:
    """
    Search GitHub for 'help wanted' issues, using cache if available.

    :return: List of issue results or raw response text if JSON not found.
    """
    # Check cache first
    cached_results = load_cache()
    if cached_results is not None:
        return cached_results

    url = "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc"
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/136.0.0.0 Safari/537.36",
    }

    try:
        logger.info("Sending request to GitHub search page.")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info("Received response from GitHub.")
    except requests.RequestException as e:
        logger.error("Request failed: %s", e)
        raise

    # Parse the response for embedded JSON data
    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            logger.info("Found embedded JSON data in response.")
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            try:
                json_data = json.loads(json_text)
                results = json_data["payload"]["results"]
                save_cache(results)
                logger.info("Results extracted and cached.")
                return results
            except json.JSONDecodeError as e:
                logger.error("JSON decoding error: %s", e)
                raise ValueError("Error decoding JSON content.") from e

    # If JSON data not found, return full response content
    logger.warning("Embedded JSON data not found, returning full response text.")
    return response.text


def download_issue_info(issue_url: str) -> Union[Issue, str]:
    """
    Download detailed information about a GitHub issue from its URL.

    :param issue_url: URL of the GitHub issue.
    :return: Issue object with comments or a message if data not found.
    """
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/136.0.0.0 Safari/537.36",
    }

    try:
        logger.info("Requesting issue page from URL: %s", issue_url)
        response = requests.get(issue_url, headers=headers)
        response.raise_for_status()
        logger.info("Received issue page.")
    except requests.RequestException as e:
        logger.error("Failed to fetch issue page: %s", e)
        raise

    # Parse the page for embedded JSON data
    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            logger.info("Found embedded JSON data in issue page.")
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            try:
                issue_json_data = json.loads(json_text)
                issue_data = issue_json_data["payload"]["preloadedQueries"][0]["result"]["data"]["repository"]["issue"]
                nodes = issue_data["frontTimelineItems"]["edges"]
                comments: List[IssueComment] = []

                for node in nodes:
                    comment_node = node.get("node", {})
                    # Only process IssueComment type nodes
                    if comment_node.get("__typename") == "IssueComment":
                        comment = IssueComment(
                            createdAt=comment_node.get("createdAt", ""),
                            author=comment_node.get("author", {}).get("login", ""),
                            body=comment_node.get("body", ""),
                            url=comment_node.get("url", ""),
                            authorAssociation=comment_node.get("authorAssociation", ""),
                            summary=""  # Assuming summary can be derived or left empty
                        )
                        comments.append(comment)

                issue_title = issue_data.get("title", "Untitled Issue")
                logger.info("Extracted %d comments from issue.", len(comments))
                return Issue(name=issue_title, comments=comments)
            except json.JSONDecodeError as e:
                logger.error("JSON decoding error in issue page: %s", e)
                raise ValueError("Error decoding JSON content from issue page.") from e

    # If data not found in the expected script tag
    logger.warning("Embedded JSON data not found in the issue page.")
    return "React app data not found in the issue page."
```