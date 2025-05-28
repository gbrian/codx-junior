import requests
import json
import logging

logger = logging.getLogger(__name__)

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

    # Retrieve and process the webpage content line-by-line
    for line in response.iter_lines(decode_unicode=True):
        # Identify the line with the JSON data
        if 'react-app.embeddedData' in line:
            # Clean up the line to extract JSON content
            json_text = line.split('>', 1)[1].rsplit('<', 1)[0].strip()
            
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                raise ValueError("Error decoding JSON content.") from e

            # Return the 'results' key from the JSON data
            return json_data["payload"]["results"]

    # Raise an error if the desired script tag was not found
    raise ValueError("Script tag containing JSON data not found.")
