# [[{"id": "15bc1694-828e-4c6a-bbfe-253775fbd6ff", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "profiles": ["software_developer"], "users": ["admin"], "name": "Github issues search", "description": "The conversation involved updating a Python script that searches for GitHub \"help wanted\" issues, addressing how to handle missing JSON data in responses. The script was modified to return the full response text when the expected data is not present. Unit tests were provided to validate the script's functionality under different scenarios. Additionally, guidelines for maintaining code quality and project management practices, such as version control, documentation, and CI/CD integration, were discussed to ensure project maintainability. The focus was on writing clean, readable, and maintainable code while following agile methodologies.", "created_at": "2025-05-26 13:36:35.282005", "updated_at": "2025-05-28T07:41:36.049854", "mode": "task", "kanban_id": "", "column_id": "", "board": "codx-junior-1.0", "column": "Ideas", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/.codx/tasks/codx-junior-1.0/Ideas/github-issues-search.15bc1694-828e-4c6a-bbfe-253775fbd6ff.md", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "5749383d-8eee-45c5-995d-d59c55c989dc", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-26 13:36:35.280194", "updated_at": "2025-05-26 13:36:35.280229", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": []}]]
@software_developer convert this curl into a python requests.
Extract the line starting by `<script type="application/json" data-target="react-app.embeddedData">`
This is a script with a JSON inside, extract the JSON as "data" and return data["results"] 
## [[{"doc_id": "524cc779-621d-4a3d-abae-61626c6ca4a9", "role": "assistant", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-26 13:36:35.280194", "updated_at": "2025-05-26 13:36:35.280229", "images": [], "files": [], "meta_data": {"time_taken": 15.29552698135376, "first_chunk_time_taken": 3.460822105407715, "model": "gpt-4o"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
To convert a `curl` command into a Python `requests` script, we can use the `requests` library to mimic the HTTP request. After fetching the webpage, we will parse the HTML content to extract the specific line that contains the JSON data and retrieve the required information. We'll then incorporate best practices such as separating concerns, writing clean code, and adding unit tests.

Let's start with a simple implementation to achieve the desired functionality, followed by unit tests using the `unittest` framework.

### Python script using requests

```python
import requests
from bs4 import BeautifulSoup
import json

def fetch_json_results(url):
    # Perform an HTTP GET request to the specified URL
    response = requests.get(url)

    # Check if the request was successful
    response.raise_for_status()

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the script tag with the desired JSON
    script_tag = soup.find('script', type='application/json', attrs={'data-target': 'react-app.embeddedData'})
    if not script_tag:
        raise ValueError("Script tag with JSON data not found.")

    # Extract the JSON content from the script tag
    try:
        json_data = json.loads(script_tag.string)
    except json.JSONDecodeError as e:
        raise ValueError("Error decoding JSON content.") from e

    # Return the specific results from the JSON data
    return json_data.get("results", [])

# Example usage
# url = "https://example.com/your-page"
# results = fetch_json_results(url)
# print(results)
```

### Unit tests for the `fetch_json_results` function

```python
import unittest
from unittest.mock import patch, Mock

class TestFetchJsonResults(unittest.TestCase):

    @patch('requests.get')
    def test_fetch_json_results_success(self, mock_get):
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <head></head>
            <body>
                <script type="application/json" data-target="react-app.embeddedData">
                {"results": ["result1", "result2"]}
                </script>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        # Execute function and assertion
        url = "https://example.com/test"
        results = fetch_json_results(url)
        self.assertIn("result1", results)
        self.assertIn("result2", results)

    @patch('requests.get')
    def test_fetch_json_results_no_script_tag(self, mock_get):
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><head></head><body></body></html>"
        mock_get.return_value = mock_response

        # Execute function and assertion
        url = "https://example.com/test"
        with self.assertRaises(ValueError):
            fetch_json_results(url)

    @patch('requests.get')
    def test_fetch_json_results_json_decode_error(self, mock_get):
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <head></head>
            <body>
                <script type="application/json" data-target="react-app.embeddedData">
                invalid json
                </script>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        # Execute function and assertion
        url = "https://example.com/test"
        with self.assertRaises(ValueError):
            fetch_json_results(url)

if __name__ == '__main__':
    unittest.main()
```

### Best Practices and Documentation

1. **Readability and Maintainability**: Each function is small, focused, and named in a way that describes its purpose.
2. **Error Handling**: Proper handling of network errors and JSON decoding errors.
3. **Testing**: The unit tests cover the primary function and check various scenarios such as the presence of a script tag and invalid JSON.
4. **Documentation**: Code comments provide clarity on each step of the process.
5. **Agile and Version Control**: Regular commits with descriptive messages enhance traceability, while user stories and sprints can help organize tasks.

Integrate this script into your version control system, document changes, and adhere to agile practices to maintain and improve the project effectively.
## [[{"doc_id": "ea5d44e2-f983-4620-91f8-40799c5f6d2d", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-26 13:36:35.280194", "updated_at": "2025-05-26 13:36:35.280229", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": []}]]
No need for beaifulsoup, just get the body as lines, find the line and make the replace needed
## [[{"doc_id": "34bc424e-c76f-4ba4-9a11-4866783936ac", "role": "assistant", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-26 13:36:35.280194", "updated_at": "2025-05-26 13:36:35.280229", "images": [], "files": [], "meta_data": {"time_taken": 17.41980528831482, "first_chunk_time_taken": 1.7673659324645996, "model": "gpt-4o"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
Certainly! I'll provide a more straightforward approach to parse the HTML content without using BeautifulSoup by reading the body as lines, finding the specific line with the JSON data, and handling the data extraction. We'll also incorporate unit tests and emphasize clean, maintainable code that can be managed effectively using version control, and communicate the importance of best practices throughout the process.

### Python Script using `requests`

First, ensure you have the `requests` library installed:

```bash
pip install requests
```

### Implementation

```python
import requests
import json

def fetch_json_results(url):
    """
    Fetch JSON results from a specified URL and return the 'results' key.
    
    :param url: URL of the webpage containing the JSON in a script tag.
    :return: Data contained in the 'results' key of the JSON.
    :raises: ValueError if the script tag or JSON is not properly formatted.
    """
    # Perform an HTTP GET request to the specified URL
    response = requests.get(url)
    response.raise_for_status()  # Raise an error on a failed request

    # Retrieve and process the webpage content line-by-line
    for line in response.iter_lines(decode_unicode=True):
        # Identify the line with the JSON data
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            # Clean up the line to extract JSON content
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                raise ValueError("Error decoding JSON content.") from e

            # Return the 'results' key from the JSON data
            return json_data.get("results", [])

    # Raise an error if the desired script tag was not found
    raise ValueError("Script tag containing JSON data not found.")

# Example Usage
# url = "https://example.com/your-page"
# results = fetch_json_results(url)
# print(results)
```

### Unit Tests

```python
import unittest
from unittest.mock import patch, Mock

class TestFetchJsonResults(unittest.TestCase):

    @patch('requests.get')
    def test_fetch_json_results_success(self, mock_get):
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'{"results": ["result1", "result2"]}',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        # Execute function and assert result
        url = "https://example.com/test"
        results = fetch_json_results(url)
        self.assertEqual(results, ["result1", "result2"])

    @patch('requests.get')
    def test_fetch_json_results_no_script_tag(self, mock_get):
        # Setup mock response with no target script tag
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body></body></html>',
        ]
        mock_get.return_value = mock_response

        # Asserting that ValueError is raised
        url = "https://example.com/test"
        with self.assertRaises(ValueError):
            fetch_json_results(url)

    @patch('requests.get')
    def test_fetch_json_results_json_decode_error(self, mock_get):
        # Setup mock response with invalid JSON data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'invalid json',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        # Asserting that ValueError is raised
        url = "https://example.com/test"
        with self.assertRaises(ValueError):
            fetch_json_results(url)

if __name__ == '__main__':
    unittest.main()
```

### Best Practices and Task Management

1. **Version Control with Git**:
   - Use `git init` to initialize git in your project.
   - Use `git add`, `git commit`, and `git push` to manage your code versions.
   - Ensure that commit messages are descriptive, such as "Add JSON extraction functionality" or "Fix JSON decode error handling".

2. **Agile Methodologies**:
   - Use tools like Jira, Trello, or Azure Boards to create user stories and sprints.
   - Break down tasks into manageable pieces for iterative development.
   - Hold regular review and planning meetings to adjust priorities.

3. **Code Documentation**:
   - The code is documented with comments and docstrings.
   - Maintain automatically generated documentation through tools like Sphinx or MkDocs.

4. **Continuous Integration**:
   - Set up a CI/CD pipeline using services like GitHub Actions, Travis CI, or Jenkins to automate testing and deployment.

By following these practices, you'll be better equipped to maintain and scale your project efficiently.
## [[{"doc_id": "17685351-0746-47a2-972a-0f24a8078124", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-26 13:36:35.280194", "updated_at": "2025-05-26 13:36:35.280229", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": []}]]
Function will be called "search_github_issues" and url will be "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc'"


## [[{"doc_id": "7d322a9c-e1c2-4e60-81dc-4770a21ab131", "role": "assistant", "task_item": "analysis", "hide": true, "improvement": false, "created_at": "2025-05-26 13:36:35.280194", "updated_at": "2025-05-26 13:36:35.280229", "images": [], "files": [], "meta_data": {"time_taken": 19.50488805770874, "first_chunk_time_taken": 2.043765068054199, "model": "gpt-4o"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
Certainly! Here's the updated document incorporating the user's comments.

---

Certainly! I'll provide a more straightforward approach to parse the HTML content without using BeautifulSoup by reading the body as lines, finding the specific line with the JSON data, and handling the data extraction. We'll also incorporate unit tests and emphasize clean, maintainable code that can be managed effectively using version control, and communicate the importance of best practices throughout the process.

### Python Script using `requests`

First, ensure you have the `requests` library installed:

```bash
pip install requests
```

### Implementation

```python
import requests
import json

def search_github_issues():
    """
    Search GitHub issues and return the 'results' key from the JSON in the script tag.

    :return: Data contained in the 'results' key of the JSON.
    :raises: ValueError if the script tag or JSON is not properly formatted.
    """
    url = "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc"

    # Perform an HTTP GET request to the specified URL
    response = requests.get(url)
    response.raise_for_status()  # Raise an error on a failed request

    # Retrieve and process the webpage content line-by-line
    for line in response.iter_lines(decode_unicode=True):
        # Identify the line with the JSON data
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            # Clean up the line to extract JSON content
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                raise ValueError("Error decoding JSON content.") from e

            # Return the 'results' key from the JSON data
            return json_data.get("results", [])

    # Raise an error if the desired script tag was not found
    raise ValueError("Script tag containing JSON data not found.")
```

### Unit Tests

```python
import unittest
from unittest.mock import patch, Mock

class TestSearchGitHubIssues(unittest.TestCase):

    @patch('requests.get')
    def test_search_github_issues_success(self, mock_get):
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'{"results": ["issue1", "issue2"]}',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        # Execute function and assert result
        results = search_github_issues()
        self.assertEqual(results, ["issue1", "issue2"])

    @patch('requests.get')
    def test_search_github_issues_no_script_tag(self, mock_get):
        # Setup mock response with no target script tag
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body></body></html>',
        ]
        mock_get.return_value = mock_response

        # Asserting that ValueError is raised
        with self.assertRaises(ValueError):
            search_github_issues()

    @patch('requests.get')
    def test_search_github_issues_json_decode_error(self, mock_get):
        # Setup mock response with invalid JSON data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'invalid json',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        # Asserting that ValueError is raised
        with self.assertRaises(ValueError):
            search_github_issues()

if __name__ == '__main__':
    unittest.main()
```

### Best Practices and Task Management

1. **Version Control with Git**:
   - Use `git init` to initialize git in your project.
   - Use `git add`, `git commit`, and `git push` to manage your code versions.
   - Ensure that commit messages are descriptive, such as "Add JSON extraction functionality" or "Fix JSON decode error handling".

2. **Agile Methodologies**:
   - Use tools like Jira, Trello, or Azure Boards to create user stories and sprints.
   - Break down tasks into manageable pieces for iterative development.
   - Hold regular review and planning meetings to adjust priorities.

3. **Code Documentation**:
   - The code is documented with comments and docstrings.
   - Maintain automatically generated documentation through tools like Sphinx or MkDocs.

4. **Continuous Integration**:
   - Set up a CI/CD pipeline using services like GitHub Actions, Travis CI, or Jenkins to automate testing and deployment.

By following these practices, you'll be better equipped to maintain and scale your project efficiently.


## [[{"doc_id": "728f28fe-fc86-4b29-afe9-4a82eaec253d", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-28 07:26:25.612748", "updated_at": "2025-05-28 07:26:25.612780", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": []}]]
Make sure to add the headers from the original "curl" example
## [[{"doc_id": "37800e3a-e88d-4f2b-9f26-5fbef93fa0fc", "role": "assistant", "task_item": "analysis", "hide": true, "improvement": false, "created_at": "2025-05-28 07:26:25.612748", "updated_at": "2025-05-28 07:26:25.612780", "images": [], "files": [], "meta_data": {"time_taken": 20.689549446105957, "first_chunk_time_taken": 2.8486430644989014, "model": "gpt-4o"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
Certainly! Below is the updated document that includes setting HTTP headers for requests, following the best practices, using version control, writing unit tests, and documenting code changes effectively.

---

# GitHub Issues Search Script

This document details a Python script that searches GitHub for "help wanted" issues using specific HTTP request headers. The code is accompanied by unit tests for verification and adheres to coding best practices.

## Python Script using `requests`

First, ensure you have the `requests` library installed:

```bash
pip install requests
```

### Implementation

```python
import requests
import json

def search_github_issues():
    """
    Search GitHub issues and return the 'results' key from the JSON in the script tag.

    :return: Data contained in the 'results' key of the JSON.
    :raises: ValueError if the script tag or JSON is not properly formatted.
    """
    url = "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc"
    headers = {
        "User-Agent": "YourAppName/1.0",
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error on a failed request

    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                raise ValueError("Error decoding JSON content.") from e

            return json_data.get("results", [])

    raise ValueError("Script tag containing JSON data not found.")
```

### Unit Tests

```python
import unittest
from unittest.mock import patch, Mock

class TestSearchGitHubIssues(unittest.TestCase):

    @patch('requests.get')
    def test_search_github_issues_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'{"results": ["issue1", "issue2"]}',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        results = search_github_issues()
        self.assertEqual(results, ["issue1", "issue2"])

    @patch('requests.get')
    def test_search_github_issues_no_script_tag(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body></body></html>',
        ]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            search_github_issues()

    @patch('requests.get')
    def test_search_github_issues_json_decode_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'invalid json',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            search_github_issues()

if __name__ == '__main__':
    unittest.main()
```

## Best Practices and Task Management

1. **Version Control with Git**:
   - Initialize your git repository using `git init`.
   - Use `git add`, `git commit`, and `git push` regularly to track changes.
   - Write descriptive commit messages: "Add header support for HTTP requests" or "Improve JSON error handling".

2. **Agile Methodologies**:
   - Use tools like Jira, Trello, or Azure Boards for task tracking and creating sprints.
   - Break tasks into small, manageable pieces and prioritize them accordingly.
   - Conduct regular sprint planning and review meetings to adapt to changes.

3. **Code Documentation**:
   - Document code with meaningful comments and helpful docstrings.
   - Use tools like Sphinx or MkDocs for automatic documentation generation to keep documentation up-to-date.

4. **Continuous Integration and Deployment (CI/CD)**:
   - Set up CI/CD pipelines using GitHub Actions, Travis CI, or Jenkins to ensure code quality through automatic testing and streamlined deployment.

By following these practices, the project will be well-maintained, ensuring a higher standard of code quality and better task management.
## [[{"doc_id": "38ae5b79-5299-429e-8583-cd9964d8d39f", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-28 07:26:25.612748", "updated_at": "2025-05-28 07:26:25.612780", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": []}]]
Use this headers:

-H 'accept: */*' \
  -H 'accept-language: en-GB,en;q=0.9,en-US;q=0.8' \
  -H 'cache-control: no-cache' \
  -H 'pragma: no-cache' \
  -H 'priority: u=1, i' \
  -H 'referer: https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc' \
  -H 'sec-ch-ua: "Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Chrome OS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
## [[{"doc_id": "c8bf93c0-3c6d-4aae-b99f-9403128372af", "role": "assistant", "task_item": "analysis", "hide": true, "improvement": false, "created_at": "2025-05-28 07:26:25.612748", "updated_at": "2025-05-28 07:26:25.612780", "images": [], "files": [], "meta_data": {"time_taken": 14.678072214126587, "first_chunk_time_taken": 2.067732095718384, "model": "gpt-4o"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
# GitHub Issues Search Script

This document provides a Python script that searches GitHub for "help wanted" issues using specific HTTP request headers. The code is supported by unit tests to ensure functionality and follows coding best practices for maintainability and readability.

## Python Script using `requests`

First, ensure you have the `requests` library installed:

```bash
pip install requests
```

### Implementation

```python
import requests
import json

def search_github_issues():
    """
    Search GitHub issues and return the 'results' key from the JSON in the script tag.

    :return: Data contained in the 'results' key of the JSON.
    :raises: ValueError if the script tag or JSON is not properly formatted.
    """
    url = "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Priority": "u=1, i",
        "Referer": url,
        "Sec-CH-UA": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Chrome OS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error on a failed request

    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                raise ValueError("Error decoding JSON content.") from e

            return json_data.get("results", [])

    raise ValueError("Script tag containing JSON data not found.")
```

### Unit Tests

```python
import unittest
from unittest.mock import patch, Mock

class TestSearchGitHubIssues(unittest.TestCase):

    @patch('requests.get')
    def test_search_github_issues_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'{"results": ["issue1", "issue2"]}',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        results = search_github_issues()
        self.assertEqual(results, ["issue1", "issue2"])

    @patch('requests.get')
    def test_search_github_issues_no_script_tag(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body></body></html>',
        ]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            search_github_issues()

    @patch('requests.get')
    def test_search_github_issues_json_decode_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'invalid json',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            search_github_issues()

if __name__ == '__main__':
    unittest.main()
```

## Best Practices and Task Management

1. **Version Control with Git**:
   - Initialize your git repository using `git init`.
   - Use `git add`, `git commit`, and `git push` regularly to track changes.
   - Write descriptive commit messages: "Add header support for HTTP requests" or "Improve JSON error handling".

2. **Agile Methodologies**:
   - Use tools like Jira, Trello, or Azure Boards for task tracking and creating sprints.
   - Break tasks into small, manageable pieces and prioritize them accordingly.
   - Conduct regular sprint planning and review meetings to adapt to changes.

3. **Code Documentation**:
   - Document code with meaningful comments and helpful docstrings.
   - Use tools like Sphinx or MkDocs for automatic documentation generation to keep documentation up-to-date.

4. **Continuous Integration and Deployment (CI/CD)**:
   - Set up CI/CD pipelines using GitHub Actions, Travis CI, or Jenkins to ensure code quality through automatic testing and streamlined deployment.

By following these practices, the project will be well-maintained, ensuring a higher standard of code quality and better task management.
## [[{"doc_id": "d8e9b818-eac5-4be7-9f84-4a788cd2151d", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-28 07:33:15.943393", "updated_at": "2025-05-28 07:33:15.943427", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": []}]]
if "react-app.embeddedData" is not present in the response, return the full response text
## [[{"doc_id": "8f227b45-d95f-498c-99c0-38d657169e37", "role": "assistant", "task_item": "analysis", "hide": false, "improvement": false, "created_at": "2025-05-28 07:33:15.943393", "updated_at": "2025-05-28 07:33:15.943427", "images": [], "files": [], "meta_data": {"time_taken": 6.788257837295532, "first_chunk_time_taken": 2.0567867755889893, "model": "gpt-4o"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
# GitHub Issues Search Script

This document provides a Python script that searches GitHub for "help wanted" issues using specific HTTP request headers. The code is supported by unit tests to ensure functionality and follows coding best practices for maintainability and readability.

## Python Script using `requests`

First, ensure you have the `requests` library installed:

```bash
pip install requests
```

### Implementation

```python
import requests
import json

def search_github_issues():
    """
    Searches GitHub for issues labeled as "help wanted".

    :return: Data contained in the 'results' key of the JSON if available, otherwise the full response text.
    :raises: ValueError if the JSON cannot be decoded.
    """
    url = "https://github.com/search?q=help+wanted&type=issues&s=updated&o=desc"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Priority": "u=1, i",
        "Referer": url,
        "Sec-CH-UA": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Chrome OS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error on a failed request

    for line in response.iter_lines(decode_unicode=True):
        if '<script type="application/json" data-target="react-app.embeddedData">' in line:
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            
            try:
                json_data = json.loads(json_text)
                return json_data.get("results", [])
            except json.JSONDecodeError as e:
                raise ValueError("Error decoding JSON content.") from e

    # If the JSON data is not found, return the full response content
    return response.text
```

### Unit Tests

```python
import unittest
from unittest.mock import patch, Mock

class TestSearchGitHubIssues(unittest.TestCase):

    @patch('requests.get')
    def test_search_github_issues_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'{"results": ["issue1", "issue2"]}',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        results = search_github_issues()
        self.assertEqual(results, ["issue1", "issue2"])

    @patch('requests.get')
    def test_search_github_issues_no_script_tag(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><head></head><body>No relevant script tag found</body></html>'
        mock_response.iter_lines.return_value = mock_response.text.splitlines()
        mock_get.return_value = mock_response

        results = search_github_issues()
        self.assertEqual(results, mock_response.text)

    @patch('requests.get')
    def test_search_github_issues_json_decode_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'<html><head></head><body>',
            b'<script type="application/json" data-target="react-app.embeddedData">',
            b'invalid json',
            b'</script>',
            b'</body></html>',
        ]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            search_github_issues()

if __name__ == '__main__':
    unittest.main()
```

## Best Practices and Task Management

1. **Version Control with Git**:
   - Initialize your git repository using `git init`.
   - Use `git add`, `git commit`, and `git push` regularly to track changes.
   - Write descriptive commit messages: "Add error handling for missing JSON data" or "Update HTTP headers for GitHub search".

2. **Agile Methodologies**:
   - Use tools like Jira, Trello, or Azure Boards for task tracking and creating sprints.
   - Break tasks into small, manageable pieces and prioritize them accordingly.
   - Conduct regular sprint planning and review meetings to adapt to changes.

3. **Code Documentation**:
   - Document code with meaningful comments and helpful docstrings.
   - Use tools like Sphinx or MkDocs for automatic documentation generation to keep documentation up-to-date.

4. **Continuous Integration and Deployment (CI/CD)**:
   - Set up CI/CD pipelines using GitHub Actions, Travis CI, or Jenkins to ensure code quality through automatic testing and streamlined deployment.

By following these practices, the project will be well-maintained, ensuring a higher standard of code quality and better task management.