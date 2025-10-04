import logging
from codx.junior.chat.chat_engine import ChatEngine
from langchain.schema import HumanMessage
from codx.junior.db import Chat
from codx.junior.settings import CODXJuniorSettings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def code_writer(code_text, file_path, language=None, **kwargs):
    """
    Call this function for each new code block to ensure it has the project's best practices.
    Function will return the final code.

    Args:
        code_text (str): The code to which best practices should be applied.
        file_path (str): The path of the file containing the code.
        language (str, optional): The language of the code. Defaults to None.
        **kwargs: Additional keyword arguments that may include:
            - settings (CODXJuniorSettings): Optional settings for configuring the chat engine.
    """
    settings = kwargs.get("settings")
    chat_engine = ChatEngine(settings=settings, event_manager=None)
    
    language = language or "plaintext"
    message_content = f"Apply best practices to this code:\n```{language} {file_path}\n{code_text}\n```"

    chat = Chat(
        file_list=[file_path],
        messages=[HumanMessage(content=message_content)]
    )

    await chat_engine.chat_with_project(chat=chat)
    return chat.messages[-1].content
