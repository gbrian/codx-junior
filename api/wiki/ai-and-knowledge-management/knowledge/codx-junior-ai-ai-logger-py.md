This document describes a Python class `AILogger` designed for logging within the `codx-api` project.

### AILogger Class

The `AILogger` class provides a simple interface for logging messages with different severity levels. It is initialized with a `settings` object, though the details of this object are not specified in the provided code.

```python
# /codx/junior/ai/ai_logger.py
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
```

#### Methods

*   `__init__(self, settings)`: Constructor for the `AILogger` class.
*   `info(self, message)`: Logs an informational message.
*   `debug(self, message)`: Logs a debug message.
*   `error(self, message)`: Logs an error message.
*   `exception(self, message)`: Logs an exception message, including traceback information.

#### Keywords

The document is associated with the following keywords: `knowledge`, `code splitting`, `document enrichment`, `keyword extraction`.