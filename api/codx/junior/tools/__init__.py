import logging
from typing import Optional, Dict

# Import tools
from .fetch_webpage import fetch_webpage

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def tool_read_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()

def test_tool():
    return "test ok!"

# Define TOOLS
TOOLS = [
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "use to read the full content of a file reference.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute file path",
                        }
                    },
                    "required": ["file_path"],
                },
            }
        },
        "settings": {"async": False},
        "tool_call": tool_read_file
    },
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
        "settings": {"async": True},
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
    }
]
