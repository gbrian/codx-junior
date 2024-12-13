import logging
import json
import time

from helium import *

from selenium import *
from selenium.webdriver import ChromeOptions, FirefoxOptions

from codx.junior.engine import CODXJuniorSession
from codx.junior.model import Chat, Message
from codx.junior.utils import exec_command
from langchain.schema import AIMessage, HumanMessage

from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)

# Global instructions
def navigate(url):
    go_to(url)

def execute_script(script):
    return get_driver().execute_script(script)
        
class Browser:
    def __init__(self, session: CODXJuniorSession):
        self.session = session

    def new_session(self):
        logger.info(f"Start new browser request")
        old_driver = get_driver()
        if old_driver:
            driver.session_id = old_driver.session_id
        logger.info(f"[Browser] Create new driver {driver} - old driver: {old_driver}")
        return driver

    def get_session(self):
        driver = None
        try:
            driver = get_driver()
            if driver and driver.current_url:
                return driver
        except Exception as ex:
            logger.exception(f"driver not working! creating new session")
            driver = None
        return driver or self.new_session()

    def clean_html(self, html_doc):
        soup = BeautifulSoup(html_doc, 'html.parser')
        for tag in ['script', 'svg']:
            [t.decompose() for t in  soup.find_all(tag)]
        return md(str(soup))

    def get_current_page(self):
        driver = self.get_session()
        url = driver.current_url
        logger.info(f"get_current_page url: {url}")
        if url:
            try:
                time.sleep(5)
                html_doc = driver.execute_script('return document.body.innerText')
                logger.info(f"get_current_page html: {html_doc[0:100]}")
                html_doc = self.clean_html(html_doc)
                logger.info(f"get_current_page CLEAN html: {html_doc[0:100]}")
                return html_doc
            except Exception as ex:
                logger.exception(f"get_current_page error: {ex}")
                pass
        return ""

    def parse_response_script(self, response):
        fence_start = "```python"
        fence_end = "```"
        if fence_start in response:
            response = response.split(fence_start)[1]
            response = response.split(fence_end)[0]
            return response
        return None

    def get_current_screenshot(slef):
        driver = self.get_session()
        image = driver.get_screenshot_as_png()
        base64_image = base64.b64encode(image)
        return f"data:image/png;base64,{base64_image}"

    def chat_with_browser(self, chat: Chat):
        logger.info(f"New browser request")
        driver = self.get_session()

        maxIterations = 5
        profile = self.session.get_profile_manager().read_profile("browser").content
        last_user_message = chat.messages[-1].content
        
        last_command_output = ""
        messages = [m for m in chat.messages if not m.hide]
        prompt = None
        while True:
            maxIterations -= 1
            
            browser_request =  f"Last User Request: {last_user_message}" if maxIterations \
                else "Ops, seems like we have ran out of attempts to make this work :( Should we ask user for help?" 
                
            prompt = f"""
            Profile: {profile}
            Current Page HTML: {self.get_current_page()}
            {browser_request}
            Last command output: {last_command_output}
            """
            
            logger.info(f"[Browser] agent prompt: {prompt}")
            # Call AI for navigation instructions
            self.session.chat_with_project(chat_mode="chat", chat=chat, use_knowledge=False)
            
            response = chat.messages[-1].content
            logger.info(f"[Browser] agent response: {response}")
            pyscript = self.parse_response_script(response)
            if maxIterations and pyscript:
                try:
                    last_command_output = str(eval(pyscript))
                except Exception as ex:
                    last_command_output = f"ERROR: {ex}"
                continue
            else:
                chat.messages.append(Message(role="assistant", content=f"""About {last_user_message}

                {response}
                """))
                break            


    def take_screenshot(self, name):
        return None
