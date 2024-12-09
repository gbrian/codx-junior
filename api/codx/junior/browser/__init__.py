import logging
import json
import time

from helium import *

from selenium import *
from selenium.webdriver import ChromeOptions, FirefoxOptions

from codx.junior.engine import CODXJuniorSession
from codx.junior.model import Chat
from codx.junior.utils import exec_command
from langchain.schema import AIMessage, HumanMessage

from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)

def start_firefox_browser():
    options = FirefoxOptions()
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    start_firefox(options=options)

def start_chrome_browser():
    global drive
    options = ChromeOptions()
    options.add_argument('--no-sandbox')
    #options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-fullscreen')
    start_chrome(headless=False, options=options)

def start_broswser():
    try:
        start_chrome_browser()
        go_to("https://www.google.com")
    except Exception as ex:
        logger.exception(f"Error starting browser {ex}")