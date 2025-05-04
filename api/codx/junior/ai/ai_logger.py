import os
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class AILogger:
    def __init__(self, settings):
        self.settings = settings
        self.log_file = f"{self.settings.codx_path}/logs/ai.md"
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    def write_log(self, content):
        with open(self.log_file, 'a') as f:
            f.write(f'[{datetime.now():%Y-%m-%d %H:%M:%S%z}] {content}\n')

    def info(self, message):
        self.write_log(message)

    def debug(self, message):
        self.write_log(message)

    def error(self, message):
        self.write_log(message)

    def exception(self, message):
        self.write_log(message)
