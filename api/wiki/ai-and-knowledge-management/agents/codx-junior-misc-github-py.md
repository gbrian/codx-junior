# GitHub Agent

This document provides documentation for the GitHub agent, which facilitates interaction with GitHub issues.

## Table of Contents

- [Features](#features)
- [Caching Mechanism](#caching-mechanism)
- [Usage](#usage)
  - [Searching GitHub Issues](#searching-github-issues)
  - [Downloading Issue Information](#downloading-issue-information)
- [Classes](#classes)
  - [IssueComment](#issuecomment)
  - [Issue](#issue)

## Features

The GitHub agent offers the following capabilities:

*   **Search GitHub Issues**: Find open issues across various repositories, with an option to filter by specific queries.
*   **Download Issue Details**: Fetch detailed information about a specific GitHub issue, including its title, URL, and all associated comments.
*   **Caching**: Implements a caching mechanism to store and retrieve previously fetched issue data, reducing redundant API calls and improving performance.

## Caching Mechanism

The agent utilizes a caching system to store results from GitHub API requests. This helps in:

*   **Performance Improvement**: Avoids re-fetching data that has been recently accessed.
*   **Rate Limiting Reduction**: Decreases the number of direct requests to the GitHub API.

### Cache Configuration

*   **Cache Directory**: Cache files are stored in the system's temporary directory under `github_cache`.
*   **Cache Expiration**: Cached data is considered valid for 3 days (259,200 seconds).

### Cache Functions

*   `get_cache_filepath(url: str) -> str`: Generates a safe file path for storing cache data based on a given URL.
*   `load_cache_for_url(url: str) -> Optional[Union[List, str]]`: Attempts to load cached data for a specific URL. Returns the cached data if it's valid and exists, otherwise returns `None`.
*   `save_cache_for_url(url: str, results: Union[List, str]) -> None`: Saves the provided results to a cache file associated with the given URL.

## Usage

### Searching GitHub Issues

The `search_github_issues` function allows you to search for issues on GitHub.

```python
from codx.junior.misc.github import search_github_issues

# Example: Search for issues related to 'codx-junior' in the 'gbrian/codx-junior' repository
issues = search_github_issues(query="repo%3Agbrian%2Fcodx-junior+is%3Aopen+type%3Aissue")

# Example: Search for issues labeled 'help wanted'
help_wanted_issues = search_github_issues(query="label%3A%22help%20wanted%22")

# You can also search issues across multiple repositories (as shown in search_codx_junior_dependencies_project_isssues)
# The search_codx_junior_dependencies_project_isssues function is a convenience wrapper for this.
```

The `search_codx_junior_dependencies_project_isssues` function is a specialized version that searches for the top 2 open issues in a predefined list of repositories.

```python
from codx.junior.misc.github import search_codx_junior_dependencies_project_isssues

# Get the top 2 open issues from several popular repositories
top_issues = search_codx_junior_dependencies_project_isssues()
```

### Downloading Issue Information

The `download_issue_info` function fetches all details for a given GitHub issue URL.

```python
from codx.junior.misc.github import download_issue_info

# Example: Get details for a specific issue
issue_url = "https://github.com/gbrian/codx-junior/issues/1"
issue_details = download_issue_info(issue_url)

if isinstance(issue_details, Issue):
    print(f"Issue Title: {issue_details.title}")
    print(f"Issue URL: {issue_details.url}")
    print(f"Number of comments: {len(issue_details.comments)}")
    for comment in issue_details.comments:
        print(f"- Author: {comment.author}, CreatedAt: {comment.createdAt}")
```

## Classes

### `IssueComment`

Represents a comment on a GitHub issue.

**Attributes:**

*   `createdAt` (str): Timestamp when the comment was created.
*   `author` (str): Username of the comment author.
*   `body` (str): Text content of the comment.
*   `summary` (str): A summary of the comment (currently an empty string, might be used for future enhancements).
*   `url` (str): URL of the comment.
*   `authorAssociation` (str): The author's association with the repository (e.g., 'OWNER', 'COLLABORATOR', 'MEMBER', 'NONE').

### `Issue`

Represents a GitHub issue with its associated comments.

**Attributes:**

*   `title` (str): The title of the GitHub issue.
*   `url` (str): The URL of the GitHub issue.
*   `comments` (List[IssueComment]): A list of `IssueComment` objects associated with this issue.
*   `extra_data` (dict): Contains additional raw data fetched from the GitHub API related to the issue.

```python
import requests
import json
import os
import time
import tempfile
import logging
from urllib.parse import quote_plus
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
        extra_data: dict,
        comments: Optional[List[IssueComment]] = None,
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
        self.extra_data: dict = extra_data


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

def search_codx_junior_dependencies_project_isssues():
    repos = [
      "BerriAI/litellm",
      "ollama/ollama",
      "milvus-io/pymilvus",
      "gbrian/codx-junior",
      "vuejs/vitepress",
      "encode/uvicorn",
      "fastapi/fastapi",
      "axios/axios",
      "vitejs/vite",
      "openai/openai-python"
    ]
    query = lambda r: f"repo%3A{quote_plus(r)}"
    res = []
    for repo in repos:
      try:
        res = res + search_github_issues(query=query(repo))[0:2]
      except:
        pass
    return res

def search_github_issues(query: Optional[str] = None) -> Union[List, str]:
    """
    Search GitHub issues labeled 'help wanted' with per-URL caching.

    :param url: Optional URL to fetch data from; if None, defaults to GitHub search.
    :return: List of results or response text if JSON parsing fails.
    """
    query.replace(" ", "+")
    url = f"https://github.com/search?q={query}+type%3Aissue+is%3Aopen&type=issues&s=updated&o=desc"

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
                results = [r for r in json_data["payload"]["results"] ]
                save_cache_for_url(url, results)
                logger.info("Parsed and cached results for URL: %s", url)
                return results
            except json.JSONDecodeError as e:
                logger.error("JSON decoding error for URL: %s, error: %s", url, e)
                raise ValueError("Error decoding JSON content.") from e

    raise Exception(f"JSON data not found in response for URL: {url}")


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
                comments: List[IssueComment] = [
                  IssueComment(createdAt=issue_data['createdAt'],
                            author=issue_data['author']['login'],
                            body=issue_data['body'],
                            summary='',
                            url=issue_url,
                            authorAssociation='Author')
                ]
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
                    comments=comments,
                    extra_data=issue_json_data
                )
                logger.info("Parsed issue data with comments from URL: %s", issue_url)
                return issue
            except json.JSONDecodeError as e:
                logger.error("JSON decoding error on issue page: %s, error: %s", issue_url, e)
                raise ValueError("Error decoding JSON content from issue page.") from e

    logger.warning("React app embedded data not found in issue page: %s", issue_url)
    return "React app data not found in the issue page."
```