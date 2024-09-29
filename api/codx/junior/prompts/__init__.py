from inspect import getcallargs

from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from typing import Union, List

class Prompt():
    _prompt: str
    _parser: PydanticOutputParser

    def __init__(self, prompt: str, parser: PydanticOutputParser):
        self._prompt = prompt
        self._parser = parser

    def get_prompt(self):
        return self._prompt.format(getcallargs(self.get_prompt, *args, **kwargs))
    
    def get_output(self, response):
        return self._parser.invoke(response)

class AICodeChunk(BaseModel):
    file: str = Field(description="/tah/to/bookingUtils.js")
    language: str = Field(description="js")
    code: str = Field(description="function getBookingId (booking: Booking) {\n\treturn booking.id\n\t\n}")
    className: str = Field(description="Empty string if this function is global, or class name")
    keywords: str = Field(description="A CSV list of keywords like: class,method,static,book_method,some_multiple_keys")
    documentation: str = Field(description="Allows to retrieve booking's id. A Booking instance is requitred.")
    
class AICodeToChunksValidateResponse(BaseModel):
    chunks: List[AICodeChunk] = Field(description="List of code changes")

class CodeToChunksPrompt(Prompt):
    def __init__(self):
        parser = PydanticOutputParser(pydantic_object=AICodeToChunksValidateResponse)
        super().__init__(
          prompt="""## TASK
          - We need to split the code file into small chunks to be used by our code search engine.
          - Our code search engine will help users to find related pieces of code that can help them with their tasks.
          - We must be able to recreate the file back from its pieces, make sure all code lines are present in the chunks.
          - Our code search engine will answer questions using the user's request code language like:
              * Q: How can I retrieve the booking information? Code language: python
                A: To retrieve a booing information you can call the API end point GET `/api/booking/booking/:id`  
                Here's an example in python

                ```python
                import requests
                requests.get('/api/booking/booking/19897')
                ```
                REFERENCES:
                * /file/path/to/existing/code.js
                * /file/path/to/existing/wiki.md

          ## OUTPUT FORMAT
          {format_instructions}

          ## CODE FILE
          Path: {source}
          ```{language}
          {page_content}
          ``` 
          """,
          parser=parser)
        # Singleton
        CodeToChunksPrompt.__new__ = lambda _: self

    def get_prompt(self, source: str, language: str, page_content: str):
        return self._prompt.format(
          source=source,
          language=language,
          page_content=page_content,
          format_instructions=self._parser.get_format_instructions()
        )
