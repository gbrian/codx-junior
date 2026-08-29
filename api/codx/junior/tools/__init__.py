"""
Tools module for codx-junior API.

This module aggregates all available tools for chat and project interactions.
Tools are organized as callable functions with associated metadata for
integration with language models and the API.

Tool Scope Levels:
    - "global": Tools always included in conversations (e.g., code_block_generator)
    - "chat": Tools available based on conversation context and selection
    - "profile": Tools available based on user profile or role

Tool Response Types:
    - str: Traditional single-string response (used for LLM context)
    - ToolResponse: Dual-return object for tools that need to produce both
                    user-facing content and LLM feedback

Made with ❤️ by codx-junior
"""

import logging
from typing import Optional, Dict, Union

# Import tools
from .fetch_webpage import fetch_webpage
from .project_tools import project_search, project_read_file, project_write_file
from .code_writer import code_writer
from .code_block_generator import code_block_generator
from .generate_tasks_tool import generate_tasks_tool
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Export ToolResponse for external use
__all__ = [
    "TOOLS",
    "ToolResponse",
    "fetch_webpage",
    "project_search",
    "project_read_file",
    "project_write_file",
    "code_writer",
    "code_block_generator",
    "generate_tasks_tool",
    "test_tool",
]


def test_tool() -> str:
    """Test tool for debugging purposes.

    Returns:
        str: A simple test message.

    Made with ❤️ by codx-junior
    """
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
        "settings": {"async": False, "scope": "chat"},
        "tool_call": fetch_webpage
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
        "settings": {"async": False, "project_settings": True, "scope": "chat"},
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
        "settings": {"async": False, "project_settings": True, "scope": "chat"},
        "tool_call": project_read_file
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "generate_tasks_tool",
                "description": "Generate sub-tasks from the current chat by analyzing its context and splitting it into actionable tasks. Each sub-task becomes a separate chat connected to the parent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instructions": {
                            "type": "string",
                            "description": "Optional additional instructions to guide the AI in creating sub-tasks (e.g., 'Focus on frontend tasks' or 'Split by component')."
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": {
            "async": False,
            "scope": "chat",
            "dual_response": True,
        },
        "tool_call": generate_tasks_tool
    }
]

# Documentation advice
# Don't document **kwargs parameters. They are internal.

# Made with ❤️ by codx-junior