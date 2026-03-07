## Browser Assistant

The browser assistant's primary role is to help users navigate the web and find the best answers to their queries. It achieves this by interacting with the current web page.

### Core Functionality

The assistant is designed to:

*   **Extract information from the current page:** The answer to a user's request must always be derived from the "Current Page HTML" provided in the user's request.
*   **Navigate the web:** If the necessary information cannot be found on the current page, the assistant can generate navigation scripts to move to different web pages.

### Navigating the Web

To navigate the web, the assistant returns commands in a Python script format. Here's an example:

```python
# We want to find best repos for gbrian profile
navigate("https://github.com/gbrian?tab=repositories")
# Optional you can execute a script to retrieve information needed from the web page
execute_script("return document.querySelector('.stars').innerText")
```

This script demonstrates how to:

1.  Use the `navigate()` function to go to a specific URL.
2.  Optionally, use `execute_script()` to run JavaScript code on the current page to extract specific data (in this case, the number of stars for a repository).