"""
Browser Session Management

Manages ephemeral browser instances running in Docker containers.
Each browser session is tied to a chat session and persists state in chat.meta_data.

Architecture:
    - BrowserSession: Data model for browser session state
    - DockerFirefoxManager: Orchestrates Docker container lifecycle
    - Browser: High-level browser automation interface
    - BrowserManager: CRUD operations for browser sessions
"""

import asyncio
from codx.junior.browser.model import BrowserSession
from codx.junior.browser.browser import Browser
from codx.junior.browser.browser_manager import BrowserManager

__all__ = [
    "asyncio",
    "BrowserSession",
    "Browser",
    "BrowserManager",
]