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
from .create_task_tool import create_task, CREATE_TASK_TOOL_JSON
from .process_task_tool import process_task, PROCESS_TASK_TOOL_JSON
from .apply_file_changes import apply_file_changes
from .git_tools import get_file_last_version
from .image_tools import explain_image, generate_image
from .tutorial_tools import (
    tutorial_definition,
    create_chapter,
    modify_chapter,
    delete_chapter,
)
from .model import ToolResponse, ToolSettings

# Configure logging
logger = logging.getLogger(__name__)

# Export public API
__all__ = [
    "TOOLS",
    "ToolResponse",
    "ToolSettings",
    "fetch_webpage",
    "project_search",
    "project_read_file",
    "project_write_file",
    "project_structure",
    "code_writer",
    "code_block_generator",
    "create_task",
    "process_task",
    "apply_file_changes",
    "explain_image",
    "generate_image",
    "tutorial_definition",
    "create_chapter",
    "modify_chapter",
    "delete_chapter",
    "get_file_last_version",
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
        "settings": ToolSettings(scope="chat").dict(),
        "tags": ["content", "web", "research", "external-data"],
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
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["project", "search", "navigation", "discovery"],
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
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["project", "file-operations", "read", "content-access"],
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
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["project", "file-operations", "write", "create", "modification"],
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
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["project", "file-operations", "edit", "modification", "advanced"],
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
        "settings": ToolSettings(project_settings=True, scope="chat").dict(),
        "tags": ["project", "navigation", "structure", "overview"],
        "tool_call": project_structure
    },
    {
        "tool_json": CREATE_TASK_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["task-management", "creation", "workflow"],
        "tool_call": create_task
    },
    {
        "tool_json": PROCESS_TASK_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["task-management", "processing", "workflow"],
        "tool_call": process_task
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "explain_image",
                "description": "Provide a detailed analysis and description of an image using Vision API. Analyzes visual content, composition, colors, text, and context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_base64": {
                            "type": "string",
                            "description": "Base64-encoded image content (PNG, JPG, etc.). Can include or exclude 'data:image/...' prefix."
                        }
                    },
                    "required": ["image_base64"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, scope="chat").dict(),
        "tags": ["content", "image", "analysis", "vision"],
        "tool_call": explain_image
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": "Generate an image from a text prompt using DALL-E. Creates and stores the image in the project, returning the relative URL path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Text description of the image to generate (max 4000 characters)"
                        },
                        "size": {
                            "type": "string",
                            "description": "Image dimensions: 256x256, 512x512, 1024x1024, 1024x1792, or 1792x1024 (default: 1024x1024)"
                        },
                        "quality": {
                            "type": "string",
                            "description": "Image quality: 'standard' or 'hd' (default: standard)"
                        }
                    },
                    "required": ["prompt"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, scope="chat").dict(),
        "tags": ["content", "image", "generation", "creative"],
        "tool_call": generate_image
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "code_writer",
                "description": "Generate and write code based on requirements and context.",
                "parameters": {
                    "type": "object"
                }
            }
        },
        "settings": ToolSettings(project_settings=True, scope="chat").dict(),
        "tags": ["code", "generation", "writing"],
        "tool_call": code_writer
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "tutorial_definition",
                "description": "Get the complete tutorial definition as JSON, including all chapters and nested content in hierarchical order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tutorial_id": {
                            "type": "string",
                            "description": "ID of the root tutorial chat (mode='tutorial')"
                        }
                    },
                    "required": ["tutorial_id"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, scope="chat").dict(),
        "tags": ["tutorial", "organization", "retrieval", "structure"],
        "tool_call": tutorial_definition
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "create_chapter",
                "description": "Create a new chapter (child chat) within a tutorial.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tutorial_id": {
                            "type": "string",
                            "description": "ID of the parent tutorial or chapter"
                        },
                        "name": {
                            "type": "string",
                            "description": "Chapter title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Chapter description (optional)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Initial message content (optional)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorizing the chapter"
                        }
                    },
                    "required": ["tutorial_id", "name"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["tutorial", "organization", "creation", "modification"],
        "tool_call": create_chapter
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "modify_chapter",
                "description": "Modify a chapter's content, metadata, or structure (title, description, tags, messages).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chapter_id": {
                            "type": "string",
                            "description": "ID of the chapter to modify"
                        },
                        "name": {
                            "type": "string",
                            "description": "New chapter title (optional)"
                        },
                        "description": {
                            "type": "string",
                            "description": "New chapter description (optional)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New tags (optional)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Message content to append (optional)"
                        }
                    },
                    "required": ["chapter_id"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["tutorial", "organization", "modification"],
        "tool_call": modify_chapter
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "delete_chapter",
                "description": "Delete a chapter from the tutorial. The main tutorial root (mode='tutorial' with no parent) cannot be deleted.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chapter_id": {
                            "type": "string",
                            "description": "ID of the chapter to delete"
                        }
                    },
                    "required": ["chapter_id"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["tutorial", "organization", "deletion", "modification"],
        "tool_call": delete_chapter
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "get_file_last_version",
                "description": (
                    "Retrieve a previous version of a file from git history using depth-based navigation. "
                    "Navigate through commits without needing commit IDs: depth=0 gets the previous version, "
                    "depth=1 gets version from 2 commits ago, etc. "
                    "Useful for PR reviews, understanding changes, and forensic debugging."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative or absolute path to the file to retrieve from history."
                        },
                        "depth": {
                            "type": "integer",
                            "description": (
                                "How many commits back to navigate (0 = previous version, 1 = two commits back, etc). "
                                "Default is 0. Must be >= 0 and <= 50."
                            ),
                            "default": 0,
                            "minimum": 0,
                            "maximum": 50
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        "settings": ToolSettings(session=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "version-control", "history", "file-operations"],
        "tool_call": get_file_last_version
    }
]

# Made with ❤️ by codx-junior