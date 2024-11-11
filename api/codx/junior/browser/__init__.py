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


from langchain.output_parsers import PydanticOutputParser

class Browser:
    def __init__(self, session: CODXJuniorSession):
        self.session = session

    def start_firefox(self):
        options = FirefoxOptions()
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")
        start_firefox(options=options)
        return get_driver()

    def start_chrome(self):
        options = ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        start_chrome(headless=True, options=options)
        return get_driver()

    def new_session(self):
        try:
            exec_command("ps aux | grep chrome | awk ' { print $2 } ' | xargs kill -9")
        except:
            pass
        logger.info(f"Start new browser request")
        return self.start_firefox()

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

    def parse_response(self, response):
        content = response.replace("```json", "").replace("```", "")
        try:
            return json.loads(content)
        except:
            pass
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
        
        
        task = self.parse_response(last_user_message)
        messages = chat.messages
        prompt = f"""
        Profile: {profile}
        Current Page HTML: {self.get_current_page()}
        Last User Request: {last_user_message}
        """

        while True:
            if not maxIterations:
                break
            maxIterations -= 1
            if not task:
                # Call AI for navigation instructions
                messages = self.session.get_ai().chat(prompt=prompt)
                chat.messages.append(messages[-1])
                task = self.parse_response(messages[-1].content)
                logger.info(f"""
                AI RESPONSE: {messages[-1].content}

                TASK: {task}
                """)
            
            logger.info(f"Browser request {prompt}")
            
            errors = []
            read_and_ask_ai_again = False
            if task:
                if task.get("response"):
                    chat.messages.append(AIMessage(content=task["response"]))
                    break
                for instruction in task["instructions"]:
                    if "read_page_content" in instruction:
                        read_and_ask_ai_again = True
                        break
                    if 'execute_script' in instruction:
                        instruction = f"driver.{instruction}"
                    try:
                        eval(instruction)
                        if "go_to" in instruction:
                            read_and_ask_ai_again = True
                            break
                    except Exception as ex:
                        error = f"Error processing {instruction}: {ex}"
                        logger.exception(error)
                        errors.append(error)
                if errors:
                    chat.messages.append(AIMessage(content="\n".join(errors)))

                if read_and_ask_ai_again:
                    prompt = f"""
                    {profile}
                    
                    PAGE CONTENT: ```html
                    {self.get_current_page()}
                    ```
                    
                    CONTINUE PROCESSING USER REQUEST:
                    {last_user_message}
                    """
                    task = None
                    
                    continue
                # Done
                break


    def take_screenshot(self, name):
        return None
