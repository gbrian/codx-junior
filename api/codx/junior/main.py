import sys
import re
import logging

from codx.junior.app import app

logging.basicConfig(level = logging.DEBUG, format = '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s')
logging.getLogger(__name__).info("Change logging formater")

app = app