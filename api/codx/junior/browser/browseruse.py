import logging

from browser_use import Agent

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai.ai import AI

logger = logging.getLogger(__name__)

class BrowserUse:
    def __init__(self, settings: CODXJuniorSettings):
        self.session = session
    
    async def run_search(self, task):
        agent = Agent(
            task=task,
            llm=AI(settings=self.settings).get_openai_chat_client())
        result = await agent.run()
        logger.info(f"Browser use response: {result}")