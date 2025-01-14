import logging

from langchain_openai import ChatOpenAI
from browser_use import Agent

from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

async def browse(settings: CODXJuniorSettings, request: str):
    agent = Agent(
        task=request,
        llm=ChatOpenAI(
            model_name=settings.get_ai_model(),
            openai_api_key=settings.get_ai_api_url(),
            openai_api_base=settings.get_ai_api_url()),
    )
    result = await agent.run()
    logger.info(f"results {result}")
    return result
