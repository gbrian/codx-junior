import logging
import json
import time
import threading
import os

from helium import *
from selenium import *
from selenium.webdriver import ChromeOptions, FirefoxOptions
from selenium.common.exceptions import WebDriverException

from codx.junior.db import (
    Chat,
)
from codx.junior.utils import exec_command
from langchain.schema import AIMessage, HumanMessage

from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self.user_data_dir_chrome = f"{os.environ['HOME']}/chrome-data"
        os.makedirs(self.user_data_dir_chrome, exist_ok=True)
        
        self.user_data_dir_firefox = f"{os.environ['HOME']}/firefox-data"
        os.makedirs(self.user_data_dir_firefox, exist_ok=True)

        self.driver = None

    def get_driver(self):
        return self.start_browser()

    def run_browser_check(self):
        while True:
            logger.info("run_browser_check")
            if not self.check_browser():
                self.start_browser()
            time.sleep(10)  # Check every 10 seconds

    def start_firefox_browser(self):
        options = FirefoxOptions()
        options.add_argument('--start-fullscreen')
        options.add_argument(f'--user-data-dir={self.user_data_dir_firefox}')
        start_firefox(options=options)

    def start_chrome_browser(self):
        options = ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('-P')
        options.add_argument(f'{os.environ["USER"]}_profile')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        start_chrome(headless=False, options=options)

    def check_browser(self):
        try:
            title = self.driver.title  # Accessing the title to check if the browser is responsive
            logger.info(f"Browser running {title}")
            return True
        except (WebDriverException, Exception):
            logger.info("No browser running, starting new instance")
            return False

    def start_browser(self):
        if not self.check_browser():
            logger.info("Browser is not running or unresponsive; starting a new browser.")
            self.start_chrome_browser()
            # self.start_firefox_browser()
            go_to("https://www.google.com")
            self.driver = get_driver()
        else:
            logger.info("Browser is already running.")
        return self.driver
        

browser_manager = BrowserManager()
def run_browser_manager():
    return
    try:
        browser_manager.start_browser()
    except:
        pass
    #check_browser_thread = threading.Thread(target=browser_manager.run_browser_check)
    #check_browser_thread.daemon = True  # Daemon thread will exit when the program does
    #check_browser_thread.start()