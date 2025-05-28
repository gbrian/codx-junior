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
                results = json_data["payload"]["results"]
                save_cache(results)
                return results
            except json.JSONDecodeError as e:
                raise ValueError("Error decoding JSON content.") from e

    # If the JSON data is not found, return the full response content
    return response.text
