import os
import logging
from datetime import datetime
from codx.junior.utils.utils import (
  create_file_logger
)

logger = create_file_logger(__name__)

class AILogger:
    def __init__(self, settings):
        self.settings = settings
    
    def info(self, message, *args):
        logger.info(message, *args)

    def debug(self, message, *args):
        logger.debug(message, *args)

    def error(self, message, *args):
        logger.error(message, *args)

    def exception(self, message, *args):
        logger.exception(message, *args)
