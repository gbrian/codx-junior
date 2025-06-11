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