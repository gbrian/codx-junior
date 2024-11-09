import logging

from helium import *

from selenium.webdriver import ChromeOptions

from codx.junior.engine import CODXJuniorSession
from codx.junior.model import Chat
from codx.junior.utils import exec_command

logger = logging.getLogger(__name__)


from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List, Dict, Any

class Instruction(BaseModel):
    instruction: str
    args: List[Any]

class TaskModel(BaseModel):
    task: str
    instructions: List[Instruction]

# Create the PydanticOutputParser
TaskModelParser = PydanticOutputParser(pydantic_object=TaskModel)

class Browser:
    def __init__(self, session: CODXJuniorSession):
        self.session = session

    def new_session(self):
        try:
            exec_command('kill $(pgrep -f "google-chrome")')
        except:
            pass
        logger.info(f"Start new browser request")
        
        options = ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        start_chrome(options=options)

    def get_current_page(self):
        try:
            return get_driver().page_source
        except:
            return ""

    def chat_with_browser(self, chat: Chat):
        logger.info(f"New browser request")
        self.new_session()

        maxIterations = 5
        profile = self.session.get_profile_manager().read_profile("browser").content
        driver = get_driver()
        last_user_message = chat.messages[-1].content
        
        maxIterations -= 1
        # Prepare prompt
        url = driver.current_url
        current_page_content = self.get_current_page()
        

        prompt = f"""
        Profile: {profile}
        Current Page HTML: {current_page_content}
        Last User Request: {last_user_message}
        """
        logger.info(f"Browser request {prompt}")
        task = None
        messages = chat.messages
        json_obj = None
        try:
            if "```json" in last_user_message:
                json_obj = last_user_message.split("```json")[1]
                json_obj = json_obj.split("```")[0]
                task = TaskModelParser.invoke(json_obj)
        except Exception as ex:
            logger.error(f"No tasks found {json_obj} - {ex}")
            return
            pass
        if not task:
            # Call AI for navigation instructions
            messages = self.session.get_ai().chat(prompt=prompt)
            task = TaskModelParser.invoke(messages[-1].content)
        
        def func_not_found():
            return None
        logger.info(f"TASK: {task}")
        return
        for instruction in task.instructions:
            cmd = instruction.instruction
            args = instruction.args
            try:
                eval(f"{cmd}({','.join(args)})")
            except Exception as ex:
                logger.error(f"Error processing {cmd}({args}): {ex}")
        
        return
        prompt = f"""
        Given this web page content
        ```html
        {self.get_current_page()}
        ```
        Answer user question: {last_user_message}"""
        messages = self.session.get_ai().chat(messages=messages, prompt=prompt)
        chat.messages.append(messages[-1])


    def take_screenshot(self, name):
        return None
