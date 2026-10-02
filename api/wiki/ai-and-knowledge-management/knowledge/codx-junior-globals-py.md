This document defines global variables and constants for the `codx-api` project, primarily related to background processing, application commands, and code splitting.

### Global Variables and Constants

*   `HOST_USER`: Stores the username of the host system, defaulting to the current user if the `HOST_USER` environment variable is not set.
*   `MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS`: Defines the maximum time in seconds (3600 seconds or 1 hour) after which file changes will not be processed.
*   `MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS`: Defines the maximum time in seconds (180 seconds or 3 minutes) after which file mentions will not be processed.
*   `CODX_JUNIOR_API_BACKGROUND`: Retrieves the value of the `CODX_JUNIOR_API_BACKGROUND` environment variable, likely to control background processing.
*   `AGENT_DONE_WORD`: A special string (`$$@@AGENT_DONE@@$$$`) used to signal the completion of an agent's task.

### Application Definitions

*   `APPS`: A list of dictionaries, each describing an application. Currently, only "chrome" is defined with its icon and a brief description.
*   `APPS_COMMANDS`: A dictionary mapping application names to their respective command-line arguments. For "chrome", the command is `google-chrome --no-sandbox --no-default-browser-check`.

### Code Splitting and Language Parsing

*   `CURRENT_SPLITTER_LANGUAGES`: A list of lowercase language identifiers derived from `langchain_text_splitters.Language`. This is used for code splitting functionalities.
*   `LANGUAGE_PARSER_MAPPING`: A dictionary that maps certain language identifiers to others. For example, "ts" (TypeScript) is mapped to "js" (JavaScript), and "cs" (C#) is mapped to "csharp". This is likely used to unify or standardize language processing for code splitting.

```python /codx/junior/globals.py
import os
import subprocess
import logging

HOST_USER = os.environ.get("HOST_USER") or os.environ.get("USER") 

"""Changed files older than MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS won't be processed"""
MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS = 60 * 60

MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS = 3 * 60

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

logger = logging.getLogger(__name__)

APPS = [
    {
        "name": "chrome",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Google_Chrome_icon_%28February_2022%29.svg/768px-Google_Chrome_icon_%28February_2022%29.svg.png",
        "description": "Google chrome engine",
    }
]

APPS_COMMANDS = {
    "chrome": "google-chrome --no-sandbox --no-default-browser-check"
}

AGENT_DONE_WORD = "$$@@AGENT_DONE@@$$$"

from langchain_text_splitters import Language

CURRENT_SPLITTER_LANGUAGES = [lang.lower() for lang in dir(Language)]
LANGUAGE_PARSER_MAPPING = {
    "ts": "js",
    "cs": "csharp"
}
```