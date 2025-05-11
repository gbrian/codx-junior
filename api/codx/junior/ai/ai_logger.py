import os
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class AILogger:
    def __init__(self, settings):
        self.settings = settings
    
    def info(self, message):
        logger.info(message)

    def debug(self, message):
        logger.debug(message)

    def error(self, message):
        logger.error(message)

    def exception(self, message):
        logger.exception(message)
