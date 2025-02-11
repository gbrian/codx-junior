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

from codx.junior.browser import browser_manager

logger = logging.getLogger(__name__)

# Global instructions
def navigate(url):
    go_to(url)

def execute_script(script):
    return browser_manager.get_driver().execute_script(script)
        
class Browser:
    def __init__(self, session: CODXJuniorSession):
        self.session = session

    def get_session(self):
        return browser_manager.get_driver()

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
            last_output = ""
            if last_command_output:
                last_output = f"### Last command output:\n{last_command_output}"

            maxIterations -= 1
            
            browser_request =  f"Last User Request: {last_user_message}" if maxIterations \
                else "Ops, seems like we have ran out of attempts to make this work :( Should we ask user for help?" 
                
            prompt = f"""{profile}
            ## Current Page HTML
            {self.get_current_page()}
            
            {last_output}
            
            ## User request 
            {browser_request}
            """
            
            logger.info(f"[Browser] agent prompt: {prompt}")
            browser_request_message = Message(role="assistant",
                                            task_item="browser",
                                            content=prompt)

            chat.messages.append(browser_request_message)
            # Call AI for navigation instructions
            self.session.chat_with_project(chat_mode="chat", chat=chat, disable_knowledge=False)
            browser_request_message.hide = True

            response = chat.messages[-1].content
            logger.info(f"[Browser] agent response: {response}")
            pyscript = self.parse_response_script(response)
            if maxIterations and pyscript:
                try:
                    last_command_output = str(eval(pyscript))
                except Exception as ex:
                    last_command_output = f"ERROR: {ex}"
                chat.messages.append(
                    Message(role="assistant",
                            task_item="browser",
                            hide=True,
                            content=f"Browser automation: \n```\n{pyscript}\n```\n\nresult: {last_command_output}"
                    ))    
                continue
            else:
                chat.messages.append(
                    Message(role="assistant", task_item="browser", content=response))
                break            


    def take_screenshot(self, name):
        return None
