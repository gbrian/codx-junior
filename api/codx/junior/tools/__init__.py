import logging
from typing import Optional, Dict

# Import tools
from .fetch_webpage import fetch_webpage
from .project_tools import project_search, project_read_file, project_write_file
from .code_writer import code_writer

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_tool():
    return "test ok!"

# Define TOOLS
TOOLS = [
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "fetch_webpage",
                "description": "Fetch a webpage and convert it to markdown format.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL of the webpage to fetch"
                        },
                        "include_images": {
                            "type": "boolean",
                            "description": "Whether to include image references in the markdown"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum length of the output markdown"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP headers for the request"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        "settings": { "async": False },
        "tool_call": fetch_webpage
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool that returns 'test ok!'",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        "settings": {"async": False},
        "tool_call": test_tool
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_search",
                "description": "Search for documents within a project using the provided search string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": "The search query string used to find relevant documents."
                        },
                        "validation": {
                            "type": "string",
                            "description": "An optional brief text used to validate the content found by the search. This text will help reducing large documents and extracting only important content. "
                        }
                    },
                    "required": ["search"]
                }
            }
        },
        "settings": {"async": False, "project_settings": True},
        "tool_call": project_search
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_read_file",
                "description": "Allows to read project's file content from a relative or absolute file path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative or absolute path to the file to read."
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        "settings": { "async": False, "project_settings": True },
        "tool_call": project_read_file
    }
]

# Documentation advice
# Don't document **kwargs parameters. They are internal.