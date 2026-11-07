"""
Browser Session Management

Manages Chromium co-browsing sessions running in Docker containers.

Each session is shared by the user (live VNC view) and the AI (Chrome DevTools
Protocol), and may be connected to one or more chats via ``chat_ids``.

Architecture:
    - BrowserSession: Data model for browser session state
    - DockerBrowserManager: Orchestrates the Chromium container lifecycle
    - Browser: High-level Playwright/CDP automation interface
    - BrowserManager: CRUD, chat association, activity audit and cost summary
    - BrowserActivityLog: Per-session user/AI audit trail
"""

import asyncio
from codx.junior.browser.model import BrowserSession
from codx.junior.browser.browser import Browser
from codx.junior.browser.browser_manager import BrowserManager
from codx.junior.browser.docker_browser_manager import DockerBrowserManager

__all__ = [
    "asyncio",
    "BrowserSession",
    "Browser",
    "BrowserManager",
    "DockerBrowserManager",
]