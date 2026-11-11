"""
Tools module for codx-junior API.

This module aggregates all available tools for chat and project interactions.
Tools are organized as callable functions with associated metadata for
integration with language models and the API.

Tool Scope Levels:
    - "global": Tools always included in conversations
    - "chat": Tools available based on conversation context and selection

Tool Response Types:
    - str: Traditional single-string response (used for LLM context)
    - ToolResponse: Dual-return object for tools that need to produce both
                    user-facing content and LLM feedback

Glob Patterns:
    Glob patterns are only supported by search tools that return file paths
    (e.g. ``project_search``). Reading tools always use literal paths.
    Glob wildcards are:
        - ``*``   matches any characters within a single path segment
        - ``?``   matches a single character
        - ``[abc]`` matches one character from the set
        - ``**``  matches across multiple directories (recursive)
    Example: ``web/src/components/**/*.vue``.

Made with ❤️ by codx-junior
"""

import logging
from typing import Optional, Dict, Union

# Import tools
from .fetch_webpage import fetch_webpage
from .doc_converter_tools import (
    doc_converter,
    markdown_to_pdf,
    markdown_to_docx,
    html_to_markdown,
    html_to_pdf,
    html_slides_to_pdf,
    DOC_CONVERTER_TOOL_JSON,
)
from .project_tools import (
    project_search,
    project_grep,
    project_glob,
    project_read_file,
    project_write_file,
    project_changes,
)
from .atlas_tools import (
    project_map,
    project_locate,
    project_trace,
    project_impact,
    project_health,
    PROJECT_MAP_TOOL_JSON,
    PROJECT_LOCATE_TOOL_JSON,
    PROJECT_TRACE_TOOL_JSON,
    PROJECT_IMPACT_TOOL_JSON,
    PROJECT_HEALTH_TOOL_JSON,
)
from .project_structure import (
    project_structure,
    read_folder,
    PROJECT_STRUCTURE_TOOL_JSON,
    READ_FOLDER_TOOL_JSON,
)
from .codx_tools import search_codx, SEARCH_CODX_TOOL_JSON
from .code_writer import code_writer
from .create_task_tool import create_task, CREATE_TASK_TOOL_JSON
from .process_task_tool import process_task, PROCESS_TASK_TOOL_JSON
from .orchestration_tools import (
    orchestrator,
    delegate,
    ORCHESTRATOR_TOOL_JSON,
    DELEGATE_TOOL_JSON,
)
from .apply_file_changes import apply_file_changes
from .git_tools import (
    get_file_last_version,
    create_pr_branch,
    close_pr,
    abandon_pr,
    restore_changes,
)
from .repository_tools import (
    repository_overview,
    repository_status,
    repository_branches,
    repository_log,
    repository_compare,
    repository_commit_message,
)
from .image_tools import explain_image, generate_image
from .profile_tools import (
    profile_management,
    list_profiles,
    list_profiles_summary,
    get_profile,
    create_profile,
    update_profile,
    delete_profile,
    PROFILE_MANAGEMENT_TOOL_JSON,
    PROFILE_LIST_TOOL_JSON,
    PROFILE_LIST_SUMMARY_TOOL_JSON,
    PROFILE_GET_TOOL_JSON,
    PROFILE_CREATE_TOOL_JSON,
    PROFILE_UPDATE_TOOL_JSON,
    PROFILE_DELETE_TOOL_JSON,
)
from .profile_learning_tools import (
    profile_learning,
    PROFILE_LEARNING_TOOL_JSON,
)
from .profile_knowledge_tools import (
    profile_knowledge_search,
    PROFILE_KNOWLEDGE_SEARCH_TOOL_JSON,
)
from .team_tools import (
    team_management,
    team_context,
    TEAM_MANAGEMENT_TOOL_JSON,
    TEAM_CONTEXT_TOOL_JSON,
)
from .company_tools import (
    company_management,
    COMPANY_MANAGEMENT_TOOL_JSON,
)
from .project_manager_tools import project_manager, PROJECT_MANAGER_TOOL_JSON
from .tutorial_tools import (
    tutorial_definition,
    create_chapter,
    modify_chapter,
    delete_chapter,
)
from .docker_tools import (
    docker_ps,
    docker_logs,
    docker_stats,
    docker_inspect,
    docker_images,
    docker_run,
    docker_start,
    docker_stop,
    docker_restart,
    docker_compose_run,
    docker_compose_start,
    docker_compose_stop,
    docker_compose_restart,
    docker_container,
    docker_compose_service,
    docker_exec,
    DOCKER_PS_TOOL_JSON,
    DOCKER_LOGS_TOOL_JSON,
    DOCKER_STATS_TOOL_JSON,
    DOCKER_INSPECT_TOOL_JSON,
    DOCKER_IMAGES_TOOL_JSON,
    DOCKER_RUN_TOOL_JSON,
    DOCKER_START_TOOL_JSON,
    DOCKER_STOP_TOOL_JSON,
    DOCKER_RESTART_TOOL_JSON,
    DOCKER_COMPOSE_RUN_TOOL_JSON,
    DOCKER_COMPOSE_START_TOOL_JSON,
    DOCKER_COMPOSE_STOP_TOOL_JSON,
    DOCKER_COMPOSE_RESTART_TOOL_JSON,
    DOCKER_CONTAINER_TOOL_JSON,
    DOCKER_COMPOSE_SERVICE_TOOL_JSON,
    DOCKER_EXEC_TOOL_JSON,
)
from .duckduckgo_search import duckduckgo_search, DUCKDUCKGO_SEARCH_TOOL_JSON
from .browser_tools import (
    start_session,
    browse_action,
    get_screenshot,
    get_source_code,
    browser_activity,
    finish_session,
    browser_status,
    browser_control,
    START_SESSION_TOOL_JSON,
    BROWSE_ACTION_TOOL_JSON,
    GET_SCREENSHOT_TOOL_JSON,
    GET_SOURCE_CODE_TOOL_JSON,
    BROWSER_ACTIVITY_TOOL_JSON,
    FINISH_SESSION_TOOL_JSON,
    BROWSER_STATUS_TOOL_JSON,
    BROWSER_CONTROL_TOOL_JSON,
    BROWSER_TOOL_SETTINGS,
)
from .browser_script_tools import (
    list_browser_scripts,
    get_browser_script,
    save_browser_script,
    run_browser_script,
    delete_browser_script,
    BROWSER_SCRIPT_TOOLS,
    BROWSER_SCRIPT_TOOL_NAMES,
)
from .computer_tools import (
    start_computer,
    computer_action,
    computer_screenshot,
    computer_status,
    computer_control,
    computer_activity,
    finish_computer,
    save_computer,
    START_COMPUTER_TOOL_JSON,
    COMPUTER_ACTION_TOOL_JSON,
    COMPUTER_SCREENSHOT_TOOL_JSON,
    COMPUTER_STATUS_TOOL_JSON,
    COMPUTER_CONTROL_TOOL_JSON,
    COMPUTER_ACTIVITY_TOOL_JSON,
    FINISH_COMPUTER_TOOL_JSON,
    SAVE_COMPUTER_TOOL_JSON,
    COMPUTER_TOOL_SETTINGS,
)
from .model import ToolResponse, ToolSettings

# Configure logging
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Tool allowlist sentinels
# -----------------------------------------------------------------------------
# A profile whose ``tools`` allowlist contains this marker is granted EVERY
# chat-scoped tool registered in the runtime (the "codx-junior" harness profile
# uses it). The marker is expanded where the request tools are decided
# (:class:`codx.junior.ai.smol.smol_agent.SmolAgent`), so it never reaches the
# provider. Validators accept it as a tool name so a profile saved with it
# keeps working.
ALL_TOOLS_MARKER = "*"

# Tools that are NEVER granted by an allowlist, even with the marker: they are
# injected per run by the agent, which is the only component that knows whether
# the user may teach a profile (write access) or must only read knowledge.
PROFILE_MANAGED_TOOL_NAMES = frozenset({
    "profile_learning",
    "profile_knowledge",
    "profile_knowledge_search",
})


def all_tool_names() -> frozenset:
    """Return the names of every tool registered in the runtime."""
    return frozenset(tool["tool_json"]["function"]["name"] for tool in TOOLS)


def expand_tool_allowlist(selected) -> frozenset:
    """
    Expand a tool-name allowlist (e.g. ``Profile.tools``) into a name set.

    * ``ALL_TOOLS_MARKER`` ("*") grants every registered tool.
    * ``PROFILE_MANAGED_TOOL_NAMES`` are never granted by an allowlist: they
      are injected per run by the agent, which is the only component that
      knows whether the user may teach a profile (write access) or must only
      read knowledge.

    Args:
        selected: Iterable of tool names (may contain the marker).

    Returns:
        Frozen set of concrete tool names.
    """
    names = {str(name) for name in (selected or []) if name}
    if ALL_TOOLS_MARKER in names:
        names.discard(ALL_TOOLS_MARKER)
        names.update(all_tool_names() - PROFILE_MANAGED_TOOL_NAMES)
    return frozenset(names)


# Export public API
__all__ = [
    "TOOLS",
    "ALL_TOOLS_MARKER",
    "PROFILE_MANAGED_TOOL_NAMES",
    "all_tool_names",
    "expand_tool_allowlist",
    "ToolResponse",
    "ToolSettings",
    "fetch_webpage",
    "doc_converter",
    "markdown_to_pdf",
    "markdown_to_docx",
    "html_to_markdown",
    "html_to_pdf",
    "html_slides_to_pdf",
    "project_map",
    "project_locate",
    "project_trace",
    "project_impact",
    "project_health",
    "project_search",
    "project_grep",
    "project_glob",
    "project_read_file",
    "project_write_file",
    "project_changes",
    "project_structure",
    "read_folder",
    "search_codx",
    "code_writer",
    "create_task",
    "process_task",
    "orchestrator",
    "delegate",
    "apply_file_changes",
    "profile_management",
    "list_profiles",
    "list_profiles_summary",
    "get_profile",
    "create_profile",
    "update_profile",
    "delete_profile",
    "profile_learning",
    "profile_knowledge_search",
    "team_management",
    "team_context",
    "company_management",
    "project_manager",
    "explain_image",
    "generate_image",
    "tutorial_definition",
    "create_chapter",
    "modify_chapter",
    "delete_chapter",
    "get_file_last_version",
    "create_pr_branch",
    "close_pr",
    "abandon_pr",
    "restore_changes",
    "repository_overview",
    "repository_status",
    "repository_branches",
    "repository_log",
    "repository_compare",
    "repository_commit_message",
    "docker_ps",
    "docker_logs",
    "docker_stats",
    "docker_inspect",
    "docker_images",
    "docker_run",
    "docker_start",
    "docker_stop",
    "docker_restart",
    "docker_compose_run",
    "docker_compose_start",
    "docker_compose_stop",
    "docker_compose_restart",
    "docker_container",
    "docker_compose_service",
    "docker_exec",
    "duckduckgo_search",
    "start_session",
    "browse_action",
    "get_screenshot",
    "get_source_code",
    "browser_activity",
    "finish_session",
    "browser_status",
    "browser_control",
    "list_browser_scripts",
    "get_browser_script",
    "save_browser_script",
    "run_browser_script",
    "delete_browser_script",
    "start_computer",
    "computer_action",
    "computer_screenshot",
    "computer_status",
    "computer_control",
    "computer_activity",
    "finish_computer",
    "BROWSER_SCRIPT_TOOLS",
    "BROWSER_SCRIPT_TOOL_NAMES",
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
        "tool_json": DOC_CONVERTER_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["content", "documents", "conversion", "pdf", "docx", "markdown", "export"],
        "tool_call": doc_converter
    },
    {
        "tool_json": PROJECT_MAP_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "atlas", "map", "orientation", "discovery"],
        "tool_call": project_map
    },
    {
        "tool_json": PROJECT_LOCATE_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "atlas", "search", "locate", "symbols", "content"],
        "tool_call": project_locate
    },
    {
        "tool_json": PROJECT_TRACE_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "atlas", "graph", "trace", "calls", "routes"],
        "tool_call": project_trace
    },
    {
        "tool_json": PROJECT_IMPACT_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "atlas", "graph", "impact", "dependencies", "tests"],
        "tool_call": project_impact
    },
    {
        "tool_json": PROJECT_HEALTH_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "atlas", "health", "freshness", "index"],
        "tool_call": project_health
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_search",
                "description": (
                    "CODEBASE ONLY: `.codx` (tasks, profiles, browser sessions, chats) is "
                    "excluded from this tool — use `search_codx` for the control plane. "
                    "Search for CONCEPTS across the project's knowledge base, and for files "
                    "whose PATH matches each query. It does not return symbol definitions: "
                    "use project_grep for an exact symbol/string/config key and project_glob "
                    "for file paths. The repository's .gitignore and the project's custom "
                    "ignore patterns are honored. A query containing glob wildcards "
                    "('*', '?', '[') is treated as a glob pattern matched against project "
                    "file paths (e.g. '**/*.py'). "
                    "BULK OPERATION: provide multiple related concepts at once as a list "
                    "instead of making separate calls. "
                    "Example: search=[\"authentication\", \"user session\"]."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": ["string", "array"],
                            "description": (
                                "Single concept query (string) or list of concept queries "
                                "(array of strings). Combining multiple related queries in "
                                "one call is more efficient. A query may contain glob "
                                "wildcards to find files by path pattern."
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
                "name": "project_grep",
                "description": (
                    "CODEBASE ONLY: `.codx` (tasks, profiles, browser sessions, chats) is "
                    "excluded — use `search_codx` for the control plane. "
                    "Search the raw text of project files (grep) and return matching lines "
                    "with their line numbers and optional context. Use this instead of "
                    "project_search when you need an exact symbol, string, error message, "
                    "configuration key or regular expression rather than semantic similarity. "
                    "The repository .gitignore and the project's custom ignore patterns are "
                    "honored; binary and very large files are skipped. Narrow the search with "
                    "path/include to keep the response small."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Literal text or regular expression to search for."
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "File or folder to search, relative to the project root. "
                                "Defaults to the project root."
                            ),
                            "default": "."
                        },
                        "include": {
                            "type": ["string", "array"],
                            "description": (
                                "Optional glob filter(s) matched against the path and file "
                                "name, e.g. '*.py', 'src/**/*.ts' or ['*.py', '*.pyi']."
                            )
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Match case when true. Defaults to false.",
                            "default": False
                        },
                        "regex": {
                            "type": "boolean",
                            "description": "Treat pattern as a regular expression. Defaults to false.",
                            "default": False
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Lines of context before and after each match (0-10). Defaults to 2.",
                            "default": 2,
                            "minimum": 0,
                            "maximum": 10
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum matching lines returned (1-1000). Defaults to 100.",
                            "default": 100,
                            "minimum": 1,
                            "maximum": 1000
                        }
                    },
                    "required": ["pattern"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "search", "grep", "content", "regex", "code-navigation"],
        "tool_call": project_grep
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_glob",
                "description": (
                    "CODEBASE ONLY: `.codx` (tasks, profiles, browser sessions, chats) is "
                    "excluded — use `search_codx` for the control plane. "
                    "Find project files by glob pattern and return their paths. This is "
                    "the fast way to discover files: it does not query the knowledge "
                    "base. Standard wildcards are supported (*, ?, [abc] and recursive "
                    "**), and the repository .gitignore plus the project's custom ignore "
                    "patterns are honored. Use it before project_read_file when you know "
                    "the file name pattern but not the exact path."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": ["string", "array"],
                            "description": (
                                "Glob pattern or list of patterns, e.g. '**/*.py', "
                                "'src/**/*.ts' or ['Dockerfile*', 'docker-compose*.yml']."
                            )
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of paths returned (1-1000). Defaults to 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 1000
                        }
                    },
                    "required": ["pattern"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "search", "glob", "files", "navigation", "discovery"],
        "tool_call": project_glob
    },
    {
        "tool_json": SEARCH_CODX_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["codx", "control-plane", "tasks", "profiles", "browser-sessions", "search"],
        "tool_call": search_codx
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_read_file",
                "description": (
                    "Read CODEBASE file content from one or multiple file paths. "
                    "`.codx` files (tasks/profiles/sessions) are not discovered by the "
                    "project_* search tools; locate them with `search_codx` first and pass "
                    "the returned path here only when the exact file is needed. "
                    "Paths are read literally: glob wildcards ('*', '?', '[') are NOT "
                    "interpreted. Use project_grep/project_glob to discover files by "
                    "pattern and then read the returned paths. "
                    "\n\nLarge files are bounded and truncated at a line boundary; the "
                    "response states which lines are shown. DO NOT page through a big "
                    "file to find a symbol: pass pattern=\"setActiveTab\" (literal or "
                    "regex) and only the matching lines plus context are returned. For "
                    "a map of a large file pass outline=true; an outline is also added "
                    "automatically when you request the whole file. Use start_line/"
                    "end_line only when you already know which lines you need, and "
                    "line_numbers to get line numbers. Binary files are rejected instead "
                    "of being dumped into the context. "
                    "\n\nBULK OPERATION: To reduce tool calls, read multiple related files "
                    "at once by providing a list of paths instead of making separate calls. "
                    "Example: file_path=[\"src/main.py\", \"config/settings.py\"]. "
                    "Invalid or missing files are returned as error blocks."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": ["string", "array"],
                            "description": (
                                "Single file path (string) or list of file paths (array of strings). "
                                "Supports relative and absolute paths. Glob wildcards are not "
                                "interpreted. "
                                "Reading multiple files in one call is more efficient."
                            )
                        },
                        "start_line": {
                            "type": "integer",
                            "description": (
                                "First line to return (1-based). Applies to every file in "
                                "a bulk read. Defaults to line 1."
                            ),
                            "minimum": 1
                        },
                        "end_line": {
                            "type": "integer",
                            "description": (
                                "Last line to return (inclusive). Applies to every file in "
                                "a bulk read. Defaults to the last line of each file."
                            ),
                            "minimum": 1
                        },
                        "pattern": {
                            "type": "string",
                            "description": (
                                "Literal text or regular expression to find inside the "
                                "file. Only matching lines (plus context_lines) are "
                                "returned, with line numbers. Use this instead of reading "
                                "a large file page by page."
                            )
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": (
                                "Lines of context around each pattern match (0-10). "
                                "Defaults to 2. Ignored when pattern is not set."
                            ),
                            "default": 2,
                            "minimum": 0,
                            "maximum": 10
                        },
                        "outline": {
                            "type": "boolean",
                            "description": (
                                "If true, prepend a heuristic outline of the file "
                                "declarations (with line numbers) before the content. "
                                "Useful before reading ranges of a large file."
                            ),
                            "default": False
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": (
                                "Maximum characters returned per file. Defaults to 50000 "
                                "and is clamped to 400000."
                            ),
                            "minimum": 200
                        },
                        "line_numbers": {
                            "type": "boolean",
                            "description": (
                                "Prefix every returned line with its 1-based line number. "
                                "Defaults to false."
                            ),
                            "default": False
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
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
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
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
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "file-operations", "edit", "modification", "advanced"],
        "tool_call": apply_file_changes
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "project_changes",
                "description": (
                    "Inspect what changed in the project working tree and compare it with a "
                    "git ref. Use scope='all' for staged + unstaged + untracked changes "
                    "against base (default HEAD), scope='staged' for the next commit, "
                    "scope='unstaged' for modifications not staged yet, or scope='untracked' "
                    "for new files. Optional paths filter the result and include_patch adds "
                    "per-file diffs with context. For a repository-wide snapshot (branches, "
                    "remotes, worktrees) use the repository_* tools instead."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "base": {
                            "type": "string",
                            "description": (
                                "Commit, branch or tag to compare against. Defaults to HEAD."
                            ),
                            "default": "HEAD"
                        },
                        "scope": {
                            "type": "string",
                            "enum": ["all", "staged", "unstaged", "untracked"],
                            "description": "Which changes to show. Defaults to 'all'.",
                            "default": "all"
                        },
                        "paths": {
                            "type": ["string", "array"],
                            "description": (
                                "Optional path or list of paths (file, folder or git "
                                "pathspec) used to filter the changes."
                            )
                        },
                        "include_patch": {
                            "type": "boolean",
                            "description": "Include per-file patches. Defaults to true.",
                            "default": True
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Context lines in each patch (0-10). Defaults to 3.",
                            "default": 3,
                            "minimum": 0,
                            "maximum": 10
                        },
                        "max_files": {
                            "type": "integer",
                            "description": "Maximum files listed and patched (1-200). Defaults to 20.",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 200
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat", cache=False).dict(),
        "tags": ["project", "git", "changes", "diff", "review", "working-tree"],
        "tool_call": project_changes
    },
    {
        "tool_json": PROJECT_STRUCTURE_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, scope="chat").dict(),
        "tags": ["project", "navigation", "structure", "overview"],
        "tool_call": project_structure
    },
    {
        "tool_json": READ_FOLDER_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, scope="chat").dict(),
        "tags": ["project", "navigation", "structure", "folder"],
        "tool_call": read_folder
    },
    {
        "tool_json": CREATE_TASK_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["task-management", "creation", "workflow"],
        "tool_call": create_task
    },
    {
        "tool_json": PROCESS_TASK_TOOL_JSON,
        "settings": {
            "async": True,
            "is_async": True,
            "project_settings": True,
            "scope": "chat",
            "cache": False,
            "dual_response": True,
        },
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
        "settings": {
            "async": True,
            "is_async": True,
            "project_settings": True,
            "scope": "chat",
        },
        "tags": ["content", "image", "analysis", "vision"],
        "tool_call": explain_image
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": (
                    "Generate an image from a text prompt using the configured image model. "
                    "The request is reviewed and adapted into an optimized prompt, then the "
                    "image is created, downloaded and saved in the project. Returns the stored "
                    "image URL/path together with the adapted prompt."
                ),
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
        "settings": {
            "async": True,
            "is_async": True,
            "project_settings": True,
            "scope": "chat",
        },
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
        "tool_json": PROFILE_MANAGEMENT_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["profiles", "profile-management", "crud", "administration", "prompt-engineering"],
        "tool_call": profile_management
    },
    {
        "tool_json": PROFILE_LIST_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["profiles", "profile-management", "read", "list", "permissions"],
        "tool_call": list_profiles
    },
    {
        "tool_json": PROFILE_LIST_SUMMARY_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": [
            "profiles", "profile-management", "read", "list", "summary",
            "selection", "task-management", "permissions"
        ],
        "tool_call": list_profiles_summary
    },
    {
        "tool_json": PROFILE_GET_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["profiles", "profile-management", "read", "inspect", "permissions"],
        "tool_call": get_profile
    },
    {
        "tool_json": PROFILE_CREATE_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["profiles", "profile-management", "write", "create", "permissions"],
        "tool_call": create_profile
    },
    {
        "tool_json": PROFILE_UPDATE_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["profiles", "profile-management", "write", "update", "permissions"],
        "tool_call": update_profile
    },
    {
        "tool_json": PROFILE_DELETE_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["profiles", "profile-management", "write", "delete", "destructive", "permissions"],
        "tool_call": delete_profile
    },
    {
        "tool_json": PROFILE_LEARNING_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, session=True, dual_response=True, scope="chat").dict(),
        "tags": ["profiles", "learning", "knowledge", "memory", "administration"],
        "tool_call": profile_learning
    },
    {
        "tool_json": PROFILE_KNOWLEDGE_SEARCH_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["profiles", "knowledge", "search", "memory", "references"],
        "tool_call": profile_knowledge_search
    },
    {
        "tool_json": TEAM_MANAGEMENT_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["teams", "team-management", "crud", "administration", "orchestration"],
        "tool_call": team_management
    },
    {
        "tool_json": TEAM_CONTEXT_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["teams", "team-context", "composition", "orchestration"],
        "tool_call": team_context
    },
    {
        "tool_json": COMPANY_MANAGEMENT_TOOL_JSON,
        "settings": {
            "session": True,
            "project_settings": True,
            "dual_response": True,
            "scope": "chat",
        },
        "tags": [
            "company",
            "organization",
            "teams",
            "missions",
            "autonomy",
            "administration",
        ],
        "tool_call": company_management
    },
    {
        "tool_json": PROJECT_MANAGER_TOOL_JSON,
        "settings": {
            "async": True,
            "is_async": True,
            "session": True,
            "project_settings": True,
            "dual_response": True,
            "scope": "chat",
        },
        "tags": ["project-management", "tasks", "kanban", "sprint", "workflow", "chat"],
        "tool_call": project_manager
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
        "settings": ToolSettings(session=True, project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "version-control", "history", "file-operations"],
        "tool_call": get_file_last_version
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "create_pr_branch",
                "description": (
                    "Create a local PR branch from the current branch with the changes generated in this chat. "
                    "PRs are reviewed locally by codx-junior, so nothing is pushed to the remote. "
                    "The branch is created from the CURRENT branch unless 'base_branch' is provided. "
                    "When 'files' is provided those contents are written before committing; when omitted the "
                    "changes already present on disk are committed. "
                    "With 'worktree' enabled the branch is created in a separate git worktree, leaving the "
                    "project's working tree and its uncommitted changes untouched. "
                    "On success the chat PR view is updated with status 'open'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "branch_name": {
                            "type": "string",
                            "description": (
                                "Target PR branch name (e.g. 'codx-junior/fix-login'). "
                                "Generated automatically when omitted."
                            )
                        },
                        "base_branch": {
                            "type": "string",
                            "description": (
                                "Base branch to branch off. Defaults to the current branch."
                            )
                        },
                        "commit_message": {
                            "type": "string",
                            "description": "Commit message. Defaults to a generic AI changes message."
                        },
                        "files": {
                            "type": "object",
                            "description": (
                                "Optional map of project-relative file path to full file content. "
                                "Omit it to commit the changes already present in the working tree."
                            ),
                            "additionalProperties": {"type": "string"}
                        },
                        "worktree": {
                            "type": "boolean",
                            "description": (
                                "Create the branch as a git worktree instead of switching the project's "
                                "working tree. Defaults to false."
                            ),
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(session=True, project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "version-control", "branch", "pull-request", "worktree"],
        "tool_call": create_pr_branch
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "close_pr",
                "description": (
                    "Close a local PR by merging its branch changes into the base branch. "
                    "The branch worktree is removed when one exists. Nothing is pushed: PRs are merged locally. "
                    "The branch and base default to the chat PR view, so it can be called without arguments. "
                    "On success the chat PR view is updated with status 'merged'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "branch_name": {
                            "type": "string",
                            "description": (
                                "PR branch to merge. Defaults to the branch stored in the chat PR view."
                            )
                        },
                        "base_branch": {
                            "type": "string",
                            "description": (
                                "Branch to merge into. Defaults to the PR view base branch, "
                                "the current branch, or the repository default branch."
                            )
                        },
                        "commit_message": {
                            "type": "string",
                            "description": "Merge commit message. Defaults to a generated message."
                        },
                        "delete_branch": {
                            "type": "boolean",
                            "description": (
                                "Delete the PR branch after merging. Defaults to false."
                            ),
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(session=True, project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "version-control", "branch", "pull-request", "merge"],
        "tool_call": close_pr
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "abandon_pr",
                "description": (
                    "Abandon a local PR: remove its git worktree (if any) and delete the branch, "
                    "discarding the changes without merging them. "
                    "The branch and base default to the chat PR view, so it can be called without arguments. "
                    "On success the chat PR view is updated with status 'discarded'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "branch_name": {
                            "type": "string",
                            "description": (
                                "PR branch to abandon. Defaults to the branch stored in the chat PR view."
                            )
                        },
                        "base_branch": {
                            "type": "string",
                            "description": (
                                "Branch to return to when the PR branch is checked out. "
                                "Defaults to the PR view base branch or the repository default branch."
                            )
                        },
                        "delete_branch": {
                            "type": "boolean",
                            "description": (
                                "Delete the branch (default: true). Set false to keep the branch "
                                "and only remove its worktree."
                            ),
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(session=True, project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "version-control", "branch", "pull-request", "discard"],
        "tool_call": abandon_pr
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "restore_changes",
                "description": (
                    "Restore changes with `git restore`. Discard working tree changes "
                    "(worktree) and/or unstage staged changes (staged), optionally restoring "
                    "the content from a specific commit, branch or tag (source). "
                    "DESTRUCTIVE: working tree changes are discarded, not stashed. Untracked "
                    "files cannot be restored by git restore."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "File paths to restore. Defaults to every file changed in the "
                                "selected scope(s)."
                            )
                        },
                        "staged": {
                            "type": "boolean",
                            "description": (
                                "Restore staged changes (unstage them). The working tree is left "
                                "untouched unless worktree is also true. Defaults to false."
                            ),
                            "default": False
                        },
                        "worktree": {
                            "type": "boolean",
                            "description": (
                                "Discard working tree changes (restore from the index, or from "
                                "source when given). Defaults to true."
                            ),
                            "default": True
                        },
                        "source": {
                            "type": "string",
                            "description": (
                                "Optional commit, branch or tag to restore the content from "
                                "(`git restore --source`)"
                            )
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(session=True, project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "version-control", "restore", "discard", "unstaged", "working-tree"],
        "tool_call": restore_changes
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "repository_overview",
                "description": (
                    "Snapshot of the git repository in plain language: current and default "
                    "branch, remote and sync state (ahead/behind), how many files are staged "
                    "or not staged, lock and worktree state and the last commits. "
                    "Call it first when the user asks where the repository stands."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "repository", "status", "overview"],
        "tool_call": repository_overview
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "repository_status",
                "description": (
                    "Show what changed in the working tree: which files are staged (included "
                    "in the next commit), which are not staged, which are untracked, with "
                    "per-file line counts. Use it before writing a commit message or when "
                    "the user asks why a file is missing from a commit."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_patch": {
                            "type": "boolean",
                            "description": (
                                "Include the patches (truncated) in the response. "
                                "Defaults to false: use it only when the diff itself matters."
                            ),
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "repository", "changes", "status", "staging"],
        "tool_call": repository_status
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "repository_branches",
                "description": (
                    "List the repository branches (local and remote) with their tip commit, "
                    "flagging the current and the default branch, and list the worktrees. "
                    "Use it to answer which branches exist, which one is main, or where a "
                    "branch is checked out."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_remote": {
                            "type": "boolean",
                            "description": "Include remote-tracking branches (default: true).",
                            "default": True
                        },
                        "limit": {
                            "type": "integer",
                            "description": (
                                "Number of commits read to resolve the branch tips "
                                "(default 200, max 1000). Raise it when a tip shows no subject."
                            ),
                            "default": 200
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "repository", "branches", "worktree"],
        "tool_call": repository_branches
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "repository_log",
                "description": (
                    "Commit history of a branch, or of a single file when 'path' is given "
                    "(follow-renames included). Use it for 'what happened lately?' and for "
                    "'who touched this file and why?'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "branch": {
                            "type": "string",
                            "description": "Branch to read. Defaults to the current branch."
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "Optional file path; when given the history of that file is "
                                "returned instead of the branch history."
                            )
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of commits (default 15, max 100).",
                            "default": 15
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "repository", "history", "commits"],
        "tool_call": repository_log
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "repository_compare",
                "description": (
                    "Compare two references (branches, tags or commits) and return the files "
                    "that `from_ref` adds on top of `to_ref`, their line counts and the commits "
                    "in between. Nothing is fetched and nothing is checked out."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from_ref": {
                            "type": "string",
                            "description": (
                                "Source reference holding the changes "
                                "(e.g. 'feature/login' or a commit hash)."
                            )
                        },
                        "to_ref": {
                            "type": "string",
                            "description": "Base reference (default: HEAD).",
                            "default": "HEAD"
                        },
                        "include_patch": {
                            "type": "boolean",
                            "description": "Include the patch (truncated). Defaults to false.",
                            "default": False
                        },
                        "max_files": {
                            "type": "integer",
                            "description": "Maximum number of files listed (default 30, max 200).",
                            "default": 30
                        }
                    },
                    "required": ["from_ref"]
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "repository", "compare", "diff", "review"],
        "tool_call": repository_compare
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "repository_commit_message",
                "description": (
                    "Build a commit message draft from the staged changes (working tree when "
                    "nothing is staged) following the 50/72 rule: subject of at most 50 "
                    "characters and body lines of at most 72. "
                    "Returns the draft, the files it was built from and the facts/rules needed "
                    "to rewrite the subject with the real intent. It never commits anything."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "enum": ["auto", "staged", "worktree"],
                            "description": (
                                "'staged' (what the next commit contains), 'worktree' "
                                "(everything not committed) or 'auto' (staged when available)."
                            ),
                            "default": "auto"
                        },
                        "hint": {
                            "type": "string",
                            "description": (
                                "Optional user intent (issue reference, reason for the change) "
                                "added as the first body line before rewriting."
                            )
                        },
                        "include_diff": {
                            "type": "boolean",
                            "description": (
                                "Include the patch excerpt used to judge the change "
                                "(default: true)."
                            ),
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        },
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["git", "repository", "commit-message", "conventional-commits"],
        "tool_call": repository_commit_message
    },
    {
        "tool_json": DOCKER_PS_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "devops", "infrastructure"],
        "tool_call": docker_ps
    },
    {
        "tool_json": DOCKER_LOGS_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "logs", "debugging", "devops"],
        "tool_call": docker_logs
    },
    {
        "tool_json": DOCKER_STATS_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "monitoring", "performance", "devops"],
        "tool_call": docker_stats
    },
    {
        "tool_json": DOCKER_INSPECT_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "inspection", "configuration", "devops"],
        "tool_call": docker_inspect
    },
    {
        "tool_json": DOCKER_IMAGES_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "images", "management", "devops"],
        "tool_call": docker_images
    },
    {
        "tool_json": DOCKER_RUN_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "execution", "devops"],
        "tool_call": docker_run
    },
    {
        "tool_json": DOCKER_START_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "lifecycle", "devops"],
        "tool_call": docker_start
    },
    {
        "tool_json": DOCKER_STOP_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "lifecycle", "devops"],
        "tool_call": docker_stop
    },
    {
        "tool_json": DOCKER_RESTART_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "lifecycle", "devops"],
        "tool_call": docker_restart
    },
    {
        "tool_json": DOCKER_COMPOSE_RUN_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "compose", "services", "devops"],
        "tool_call": docker_compose_run
    },
    {
        "tool_json": DOCKER_COMPOSE_START_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "compose", "services", "lifecycle", "devops"],
        "tool_call": docker_compose_start
    },
    {
        "tool_json": DOCKER_COMPOSE_STOP_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "compose", "services", "lifecycle", "devops"],
        "tool_call": docker_compose_stop
    },
    {
        "tool_json": DOCKER_COMPOSE_RESTART_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "compose", "services", "lifecycle", "devops"],
        "tool_call": docker_compose_restart
    },
    {
        "tool_json": DOCKER_CONTAINER_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "unified", "devops", "optimization"],
        "tool_call": docker_container
    },
    {
        "tool_json": DOCKER_EXEC_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "containers", "exec", "runtime", "diagnostics", "devops"],
        "tool_call": docker_exec
    },
    {
        "tool_json": DOCKER_COMPOSE_SERVICE_TOOL_JSON,
        "settings": ToolSettings(project_settings=True, dual_response=True, scope="chat").dict(),
        "tags": ["docker", "compose", "services", "unified", "devops", "optimization"],
        "tool_call": docker_compose_service
    },
    {
        "tool_json": DUCKDUCKGO_SEARCH_TOOL_JSON,
        "settings": ToolSettings(scope="chat", dual_response=True).dict(),
        "tags": ["web", "search", "external-data", "research"],
        "tool_call": duckduckgo_search
    },
    {
        "tool_json": START_SESSION_TOOL_JSON,
        "settings": BROWSER_TOOL_SETTINGS,
        "tags": ["browser", "web", "automation", "session"],
        "tool_call": start_session
    },
    {
        "tool_json": BROWSE_ACTION_TOOL_JSON,
        "settings": BROWSER_TOOL_SETTINGS,
        "tags": ["browser", "web", "automation", "navigation"],
        "tool_call": browse_action
    },
    {
        "tool_json": GET_SCREENSHOT_TOOL_JSON,
        "settings": BROWSER_TOOL_SETTINGS,
        "tags": ["browser", "web", "automation", "vision"],
        "tool_call": get_screenshot
    },
    {
        "tool_json": GET_SOURCE_CODE_TOOL_JSON,
        "settings": BROWSER_TOOL_SETTINGS,
        "tags": ["browser", "web", "automation", "content"],
        "tool_call": get_source_code
    },
    {
        "tool_json": BROWSER_ACTIVITY_TOOL_JSON,
        "settings": BROWSER_TOOL_SETTINGS,
        "tags": ["browser", "web", "automation", "audit", "co-browsing"],
        "tool_call": browser_activity
    },
    {
        "tool_json": FINISH_SESSION_TOOL_JSON,
        "settings": BROWSER_TOOL_SETTINGS,
        "tags": ["browser", "web", "automation", "cleanup"],
        "tool_call": finish_session
    },
    {
        "tool_json": BROWSER_STATUS_TOOL_JSON,
        "settings": BROWSER_TOOL_SETTINGS,
        "tags": ["browser", "web", "co-browsing", "status"],
        "tool_call": browser_status
    },
    {
        "tool_json": BROWSER_CONTROL_TOOL_JSON,
        "settings": BROWSER_TOOL_SETTINGS,
        "tags": ["browser", "web", "co-browsing", "control", "handoff"],
        "tool_call": browser_control
    },
    # -- Orchestration: durable runs and isolated subagents -----------------
    {
        "tool_json": ORCHESTRATOR_TOOL_JSON,
        "settings": {
            # stateful: never cache plan/status/finish results
            "async": True,
            "is_async": True,
            "project_settings": True,
            "session": True,
            "scope": "chat",
            "cache": False,
            "dual_response": True,
        },
        "tags": ["orchestration", "runs", "planning", "kanban", "sprint", "workflow"],
        "tool_call": orchestrator
    },
    {
        "tool_json": DELEGATE_TOOL_JSON,
        "settings": {
            # a delegate call creates cards and runs turns: never cache it
            "async": True,
            "is_async": True,
            "project_settings": True,
            "session": True,
            "scope": "chat",
            "cache": False,
            "dual_response": True,
        },
        "tags": ["orchestration", "delegation", "subagents", "parallel", "kanban"],
        "tool_call": delegate
    },
    # -- Computer sessions: whole desktops/VMs/remote machines ---------------
    {
        "tool_json": START_COMPUTER_TOOL_JSON,
        "settings": COMPUTER_TOOL_SETTINGS,
        "tags": ["computer", "desktop", "linux", "windows", "macos", "vm", "session"],
        "tool_call": start_computer,
    },
    {
        "tool_json": COMPUTER_ACTION_TOOL_JSON,
        "settings": COMPUTER_TOOL_SETTINGS,
        "tags": ["computer", "desktop", "mouse", "keyboard", "ocr", "automation"],
        "tool_call": computer_action,
    },
    {
        "tool_json": COMPUTER_SCREENSHOT_TOOL_JSON,
        "settings": COMPUTER_TOOL_SETTINGS,
        "tags": ["computer", "desktop", "screenshot", "ocr", "vision"],
        "tool_call": computer_screenshot,
    },
    {
        "tool_json": COMPUTER_STATUS_TOOL_JSON,
        "settings": COMPUTER_TOOL_SETTINGS,
        "tags": ["computer", "desktop", "status"],
        "tool_call": computer_status,
    },
    {
        "tool_json": COMPUTER_CONTROL_TOOL_JSON,
        "settings": COMPUTER_TOOL_SETTINGS,
        "tags": ["computer", "desktop", "control", "handoff"],
        "tool_call": computer_control,
    },
    {
        "tool_json": COMPUTER_ACTIVITY_TOOL_JSON,
        "settings": COMPUTER_TOOL_SETTINGS,
        "tags": ["computer", "desktop", "activity", "co-driving"],
        "tool_call": computer_activity,
    },
    {
        "tool_json": SAVE_COMPUTER_TOOL_JSON,
        "settings": COMPUTER_TOOL_SETTINGS,
        "tags": ["computer", "desktop", "library", "snapshot", "reuse"],
        "tool_call": save_computer,
    },
    {
        "tool_json": FINISH_COMPUTER_TOOL_JSON,
        "settings": COMPUTER_TOOL_SETTINGS,
        "tags": ["computer", "desktop", "cleanup"],
        "tool_call": finish_computer,
    },
    # -- Browser scripts: reusable per-site navigation recipes ---------------
    # Source of truth: codx/junior/tools/browser_script_tools.py
    # (list_browser_scripts, get_browser_script, save_browser_script,
    #  delete_browser_script). Spread here so this file never has to be
    # rewritten when the recipe tool set grows.
    *BROWSER_SCRIPT_TOOLS,
]

# Made with ❤️ by codx-junior