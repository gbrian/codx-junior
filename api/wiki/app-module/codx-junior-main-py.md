# App Module

This document describes the core application module of the codx-api project, focusing on its setup and configuration.

## Logging Configuration

The application utilizes Python's `logging` module for outputting diagnostic information. The configuration sets the logging level to `DEBUG`, meaning all messages from DEBUG, INFO, WARNING, ERROR, and CRITICAL will be displayed. A detailed format is applied to each log message, including the timestamp, log level, logger name, line number, and the message itself. The logs are directed to the standard output (console).

```python /codx/junior/main.py
import logging
logging.basicConfig(
  level = logging.DEBUG,
  format = '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)s]: %(message)s',
  datefmt='%Y-%m-%d %H:%M:%S',
  handlers=[
      logging.StreamHandler(),
  ],
)

import sys
import re

from codx.junior.app import app

logging.getLogger(__name__).info("Change logging formater")

app = app
```

The `logging.getLogger(__name__).info("Change logging formater")` line explicitly indicates a change in the logging formatter's setup within the application.

## Application Instance

The `app` variable is imported from `codx.junior.app` and is the main FastAPI application instance. This instance is then assigned back to the `app` variable, making it the central object for configuring routes, middleware, and other application-level settings.

```python /codx/junior/main.py
from codx.junior.app import app

# ... other imports and logging configuration ...

app = app
```