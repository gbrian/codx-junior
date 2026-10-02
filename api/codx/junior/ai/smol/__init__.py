"""
SmolAgent package — a small, async-only, easy-to-maintain OpenAI chat agent.

Public API:
    * :class:`SmolAgent` — main chat agent with streaming and tool support.
    * :class:`ToolLoopError` — raised when a stuck tool-call loop is detected.
"""
from codx.junior.ai.smol.smol_agent import SmolAgent
from codx.junior.ai.smol.loop_guard import ToolLoopError

__all__ = ["SmolAgent", "ToolLoopError"]

# Made with ❤️ by codx-junior