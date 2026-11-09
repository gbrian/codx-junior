"""
Computer session management (browser + desktop).

A **computer session** is a machine the user and the AI share: a Chromium page
(``kind="browser"``), a Linux desktop container, a Windows/macOS VM or a remote
machine reached over VNC/SSH.

Architecture:
    - BrowserSession / ComputerSession: data model for the shared session
    - DockerBrowserManager / DockerComputerManager: container lifecycle
    - Browser: high-level Playwright/CDP automation (browser kind)
    - DesktopRuntime: docker-exec/RFB control (desktop kinds)
    - BrowserManager / ComputerManager: CRUD, chat linking, audit and cost
    - BrowserActivityLog: per-session user/AI audit trail

The browser-prefixed names are kept as aliases for backwards compatibility.
"""

import asyncio
from codx.junior.browser.model import BrowserSession, ComputerSession, SharedFolder
from codx.junior.browser.browser import Browser
from codx.junior.browser.browser_manager import (
    BrowserManager,
    ComputerManager,
    get_browser_manager,
    get_computer_manager,
)
from codx.junior.browser.docker_browser_manager import (
    DockerBrowserManager,
    DockerComputerManager,
)

__all__ = [
    "asyncio",
    "BrowserSession",
    "ComputerSession",
    "SharedFolder",
    "Browser",
    "BrowserManager",
    "ComputerManager",
    "get_browser_manager",
    "get_computer_manager",
    "DockerBrowserManager",
    "DockerComputerManager",
]
