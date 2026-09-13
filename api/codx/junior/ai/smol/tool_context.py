"""
ToolContext: Shared metadata passed to tools that declare it in their signature.

This class holds contextual information that tools may need across multiple
executions within a conversation, such as:
  - tool_cache: For caching tool results per conversation
  - settings: Project settings (injected when tool declares project_settings)
  - user: Current user information
  - session: Session context
  - Any other shared state tools might need

Tools that want access to this context should declare a parameter with the
same name in their function signature. The ToolContext will be injected
automatically only for those tools.

Example:
    def my_tool(url: str, tool_cache: ToolContext) -> str:
        # Access cached results or other shared state
        if tool_cache:
            ...
        return fetched_content
"""
import asyncio
from typing import Any, Dict, Optional


class ToolContext:
    """
    Holds shared metadata that tools can opt-in to receive.

    Tools that declare `tool_cache`, `settings`, `user`, or `session` as
    a parameter will receive a ToolContext instance with the relevant data.
    Tools that don't declare these parameters will continue to work as before
    (no implicit injection).

    Attributes:
        tool_cache: ToolCache instance for this conversation (may be None)
        settings: CODJuniorSettings instance
        user: CodxUser instance (or None)
        session: Optional session context
        extra: Dictionary for any additional metadata
    """

    def __init__(
        self,
        tool_cache: Optional["ToolCache"] = None,
        settings: Optional[Any] = None,
        user: Optional[Any] = None,
        session: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        self.tool_cache = tool_cache
        self.settings = settings
        self.user = user
        self.session = session
        self.extra: Dict[str, Any] = kwargs

    def get(self, key: str, default: Any = None) -> Any:
        """Get any extra metadata by key."""
        return self.extra.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set any extra metadata by key."""
        self.extra[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in extra metadata."""
        return key in self.extra

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access: context[key]."""
        if key in self.extra:
            return self.extra[key]
        raise KeyError(key)

    def __repr__(self) -> str:
        return f"ToolContext(tool_cache={self.tool_cache is not None}, settings={self.settings is not None})"


# Convenience factory for creating ToolContext from SmolAgent state
def create_tool_context(
    tool_cache: Any,
    settings: Any,
    user: Any,
    session: Optional[Any] = None,
) -> ToolContext:
    """
    Create a ToolContext instance from SmolAgent state.

    Args:
        tool_cache: The ToolCache instance for this conversation
        settings: CODJuniorSettings instance
        user: CodxUser instance
        session: Optional session context

    Returns:
        A ToolContext instance with the provided state.
    """
    return ToolContext(
        tool_cache=tool_cache,
        settings=settings,
        user=user,
        session=session,
    )