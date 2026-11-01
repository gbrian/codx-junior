"""
Profile knowledge search tool (read-only) for codx-junior.

Gives every profile participating in a chat a way to **consult what it has
learned** for the current project: guidelines, conventions and reference
documents kept under the profile ``knowledge`` folders.

Storage (see :mod:`codx.junior.profiles.profile_knowledge`):

    codx/junior/profiles/<Name>/knowledge/**     built-in base profile
    <project .codx>/profiles/<Name>/knowledge/** one folder per project level

Each folder is indexed in its own ``KnowledgeDB`` collection, so a search covers
the base profile and every project level of the inheritance chain, and every
match reports where it came from.

The search itself is implemented by the ``search`` action of
:func:`codx.junior.tools.profile_learning_tools.profile_learning`; this module
only exposes it as a read-only tool, so the variant offered to users without
knowledge administration rights cannot write anything.

Writing knowledge is done through ``profile_learning`` (``remember``,
``write_file``, ...), which enforces the project-admin / project-knowledge-admin
/ codx-junior-admin permission.

The tool is NOT part of the profile definition: the agent
(:class:`codx.junior.ai.smol.smol_agent.SmolAgent`) injects it into the request
whenever profiles take part in the turn, and it is never persisted into the
``.profile`` JSON.

Made with ❤️ by codx-junior
"""

import logging
from typing import Optional

from .model import ToolResponse
from .profile_learning_tools import (
    ACTION_SEARCH,
    DEFAULT_LIMIT,
    profile_learning,
)

logger = logging.getLogger(__name__)


def profile_knowledge_search(
    query: str,
    profile_name: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    **kwargs
) -> ToolResponse:
    """
    Search what the profiles have learned for the current project.

    Read-only: delegates to the ``search`` action of
    :func:`~codx.junior.tools.profile_learning_tools.profile_learning`.

    Args:
        query: Topic or question to look for in the profile knowledge.
        profile_name: Profile whose knowledge is searched. When omitted, every
            profile with knowledge in this project or its parents is searched.
        limit: Maximum number of matches returned (1-50).
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse: matches (user) and machine-readable results (model).

    Example:
        >>> profile_knowledge_search("angular signals",
        ...                          profile_name="software_developer")
    """
    return profile_learning(
        action=ACTION_SEARCH,
        profile_name=profile_name,
        query=query,
        limit=limit,
        **kwargs
    )


# Tool JSON definition
PROFILE_KNOWLEDGE_SEARCH_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "profile_knowledge_search",
        "description": (
            "Search what the profiles have learned for the current project: "
            "guidelines, conventions, decisions and reference documents kept per "
            "profile and per project level. The search covers the base profile and "
            "every parent project level, and each result reports which profile and "
            "level it comes from. "
            "\n\nUse it proactively, before answering anything that depends on "
            "project-specific conventions ('our guidelines', 'how do we do X here', "
            "'what we agreed'), and whenever the user refers to project docs for "
            "this profile. "
            "\nRead-only: with knowledge administration rights the profile can also "
            "apply a learned rule or write reference material."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Topic, question or keywords to look for in the profile "
                        "knowledge."
                    )
                },
                "profile_name": {
                    "type": "string",
                    "description": (
                        "Profile whose knowledge is searched "
                        "(e.g. 'software_developer'). When omitted, every profile "
                        "with knowledge is searched."
                    )
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        f"Maximum number of matches returned (default "
                        f"{DEFAULT_LIMIT}, max 50)."
                    ),
                    "default": DEFAULT_LIMIT
                }
            },
            "required": ["query"]
        }
    }
}

# Made with ❤️ by codx-junior