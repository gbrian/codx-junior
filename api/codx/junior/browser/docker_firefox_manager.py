"""
Backwards-compatible import for the old Firefox-specific manager name.

The browser implementation now uses Chromium (required for Playwright's CDP
automation).  Import :class:`DockerBrowserManager` from
``codx.junior.browser.docker_browser_manager`` in new code; this module keeps
existing imports working.
"""

from codx.junior.browser.docker_browser_manager import (  # noqa: F401
    DockerBrowserManager,
    DockerFirefoxManager,
)

__all__ = ["DockerBrowserManager", "DockerFirefoxManager"]

# Made with ❤️ by codx-junior
