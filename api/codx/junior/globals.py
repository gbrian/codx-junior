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

LOGS_FOLDER = os.environ.get("CODX_JUNIOR_API_LOGS", "/tmp/codx-junior-logs")

# Global path for analytics data, shared across all projects.
# Defaults to /home/codx-junior/analytics when the env var is not set.
ANALYTICS_DATA_PATH = os.environ.get(
    "CODX_JUNIOR_API_ANALYTICS_DATA_PATH",
    "/home/codx-junior/analytics"
)