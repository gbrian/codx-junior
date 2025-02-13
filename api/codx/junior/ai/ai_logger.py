import logging

# Set up logging
logger = logging.getLogger(__name__)

class AILogger:
    @classmethod
    def info(cls, message):
        logger.info(message)

    @classmethod
    def error(cls, message):
        logger.error(message)

    @classmethod
    def exception(cls, message):
        logger.exception(message)