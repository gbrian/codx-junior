"""
Backward-compatible engine module for codx-junior.
All functionality has been moved to the codx.junior.engine package.
This module re-exports CODXJuniorSession to avoid breaking existing imports.

Made with ❤️ by codx-junior
"""

# Re-export the main session class for backward compatibility
from codx.junior.engine.session import CODXJuniorSession  # noqa: F401
from codx.junior.engine.session import GLOBAL_CHAT_INSTRUCTIONS  # noqa: F401

__all__ = ["CODXJuniorSession", "GLOBAL_CHAT_INSTRUCTIONS"]