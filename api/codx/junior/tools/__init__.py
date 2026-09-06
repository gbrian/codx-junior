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
from .project_structure import project_structure
from .code_writer import code_writer
from .code_block_generator import code_block_generator
from .generate_tasks_tool import generate_tasks_tool
from .apply_file_changes import apply_file_changes
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
    "project_structure",
    "code_writer",
    "code_block_generator",
    "generate_tasks_tool",
    "apply_file_changes",
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
                "description": (
                    "Search for documents within a project using one or more search queries. "
                    "BULK OPERATION: To reduce tool calls, provide multiple queries at once "
                    "as a list instead of making separate calls. "
                    "Example: search=[\"authentication\", \"user session\"] instead of two separate calls."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": ["string", "array"],
                            "description": (
                                "Single search query (string) or list of search queries (array of strings). "
                                "Combining multiple related queries in one call is more efficient."
                            )
                        },
                        "validation": {
                            "type": "string",
                            "description": (
                                "Optional text used to validate and filter search results. "
                                "Helps extract only important content from large documents."
                            )
                        }
                    },
                    "required": ["search"]
                }
            }
        },
        "settings": {"async": False, "project_settings": True, "scope": "chat", "dual_response": True},
        "tool_call": project_search
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_read_file",
                "description": (
                    "Read project file content from one or multiple file paths. "
                    "BULK OPERATION: To reduce tool calls, read multiple related files at once "
                    "by providing a list of paths instead of making separate calls. "
                    "Example: file_path=[\"src/main.py\", \"config/settings.py\"] "
                    "instead of two separate calls. "
                    "Invalid or missing files are returned as error blocks."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": ["string", "array"],
                            "description": (
                                "Single file path (string) or list of file paths (array of strings). "
                                "Supports relative or absolute paths and glob patterns. "
                                "Reading multiple files in one call is more efficient."
                            )
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        "settings": {"async": False, "project_settings": True, "scope": "chat", "dual_response": True},
        "tool_call": project_read_file
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_write_file",
                "description": (
                    "Write content to a project file. Creates the file or directory if it doesn't exist. "
                    "Currently supports writing a single file per call."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative or absolute path to the file to write."
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file."
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        },
        "settings": {"async": False, "project_settings": True, "scope": "chat", "dual_response": True},
        "tool_call": project_write_file
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "apply_file_changes",
                "description": (
                    "Safely apply a batch of exact search-and-replace edits to one existing text file. "
                    "Each search string must match exactly once in the progressively updated file. "
                    "All changes are validated before the file is written; if any change conflicts, "
                    "the file remains unchanged. Include enough surrounding context in each search "
                    "string to make it unique. Do NOT rely on indentation preservation—include the "
                    "exact indentation explicitly in both search and replace strings."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative or absolute path to the file to modify."
                        },
                        "changes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "search": {
                                        "type": "string",
                                        "description": "Exact text pattern to find (must match exactly once in the file)"
                                    },
                                    "replace": {
                                        "type": "string",
                                        "description": "Text to replace with (include exact indentation and formatting)"
                                    }
                                },
                                "required": ["search", "replace"]
                            },
                            "description": "List of changes to apply, each with 'search' and 'replace' keys"
                        }
                    },
                    "required": ["file_path", "changes"]
                }
            }
        },
        "settings": {"async": False, "project_settings": True, "scope": "chat", "dual_response": True},
        "tool_call": apply_file_changes
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_structure",
                "description": "Get the project structure with files and folders, excluding invalid files. Returns a tree-like representation of the project organization.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_details": {
                            "type": "boolean",
                            "description": "If true, includes additional metadata like file counts and folder statistics.",
                            "default": False
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum folder depth to traverse. Leave null for no limit.",
                            "default": None
                        },
                        "include_file_sizes": {
                            "type": "boolean",
                            "description": "If true, includes file sizes in bytes for each file.",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": {"async": False, "project_settings": True, "scope": "chat"},
        "tool_call": project_structure
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

# Made with ❤️ by codx-junior