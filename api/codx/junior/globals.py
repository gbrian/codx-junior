import os
import subprocess
import logging

from codx.junior.settings import CODXJuniorSettings, read_global_settings
from codx.junior.utils.utils import exec_command
from codx.junior.security.user_management import UserSecurityManager
from codx.junior.model.model import CodxUser
from codx.junior.db import Chat


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

def coder_open_file(settings: CODXJuniorSettings, file_name: str):
    logger.info(f"coder_open_file {file_name}")
    os.system(f"code-server -r {file_name}")


def update_engine():
    try:
        command = ["git", "pull"]
        subprocess.run(command)
    except Exception as ex:
        logger.exception(ex)
        return ex