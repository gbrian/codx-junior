"""
Browser — high-level Playwright-based browser automation interface.

Wraps Playwright's async API with session management and tool support.
"""

import logging
import base64
from typing import Optional

from codx.junior.browser.model import BrowserSession
from codx.junior.browser.docker_firefox_manager import DockerFirefoxManager

logger = logging.getLogger(__name__)


class Browser:
    """
    High-level browser automation interface using Playwright.

    Manages Playwright context lifecycle and provides methods
    for page interaction (navigate, execute JS, take screenshots, etc.).
    """

    def __init__(self, session: BrowserSession, docker_manager: DockerFirefoxManager):
        """
        Initialize Browser.

        Args:
            session: BrowserSession with container info
            docker_manager: DockerFirefoxManager instance
        """
        self.session = session
        self.docker_manager = docker_manager
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def connect(self) -> None:
        """
        Connect to Firefox via Chrome DevTools Protocol.

        Raises:
            RuntimeError: If connection fails
        """
        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            # Connect to the running Firefox container via CDP
            debug_url = self.session.debug_url
            logger.info("Connecting to browser at: %s", debug_url)

            # Use connect_over_cdp to attach to existing browser
            self.browser = await self.playwright.chromium.connect_over_cdp(debug_url)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            logger.info("Browser connected: session %s", self.session.id[:8])
            self.session.mark_active()

        except Exception as e:
            logger.exception("Failed to connect to browser")
            self.session.status = "error"
            self.session.error = str(e)
            raise RuntimeError(f"Browser connection failed: {e}")

    async def navigate(self, url: str) -> str:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to

        Returns:
            Current page title

        Raises:
            RuntimeError: If page not connected
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            logger.info("Navigating to: %s", url)
            await self.page.goto(url, wait_until="networkidle")
            title = await self.page.title()
            self.session.current_url = url
            self.session.mark_active()
            return title
        except Exception as e:
            logger.exception("Navigation failed")
            raise RuntimeError(f"Navigation to {url} failed: {e}")

    async def execute_script(self, script: str) -> any:
        """
        Execute JavaScript in the page context.

        Args:
            script: JavaScript code to execute

        Returns:
            Result of script execution

        Raises:
            RuntimeError: If page not connected
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            result = await self.page.evaluate(script)
            self.session.mark_active()
            return result
        except Exception as e:
            logger.exception("Script execution failed")
            raise RuntimeError(f"Script execution failed: {e}")

    async def get_screenshot(self) -> str:
        """
        Take a screenshot of the current page.

        Returns:
            Base64-encoded PNG image (data: URI)

        Raises:
            RuntimeError: If page not connected
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            screenshot_bytes = await self.page.screenshot()
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            self.session.mark_active()
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            logger.exception("Screenshot failed")
            raise RuntimeError(f"Screenshot failed: {e}")

    async def get_content(self) -> str:
        """
        Get the current page HTML content.

        Returns:
            HTML string

        Raises:
            RuntimeError: If page not connected
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            content = await self.page.content()
            self.session.mark_active()
            return content
        except Exception as e:
            logger.exception("get_content failed")
            raise RuntimeError(f"get_content failed: {e}")

    async def click(self, selector: str) -> None:
        """
        Click an element.

        Args:
            selector: CSS selector

        Raises:
            RuntimeError: If page not connected or element not found
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            await self.page.click(selector)
            self.session.mark_active()
            logger.debug("Clicked: %s", selector)
        except Exception as e:
            logger.exception("Click failed for selector: %s", selector)
            raise RuntimeError(f"Click on {selector} failed: {e}")

    async def fill(self, selector: str, text: str) -> None:
        """
        Fill a text input.

        Args:
            selector: CSS selector
            text: Text to fill

        Raises:
            RuntimeError: If page not connected or element not found
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            await self.page.fill(selector, text)
            self.session.mark_active()
            logger.debug("Filled %s with text", selector)
        except Exception as e:
            logger.exception("Fill failed for selector: %s", selector)
            raise RuntimeError(f"Fill on {selector} failed: {e}")

    async def wait_for_selector(self, selector: str, timeout: int = 5000) -> None:
        """
        Wait for element to appear.

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds

        Raises:
            RuntimeError: If element doesn't appear
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            logger.exception("Wait for selector failed: %s", selector)
            raise RuntimeError(f"Timeout waiting for {selector}: {e}")

    async def close(self) -> None:
        """
        Close browser context and disconnect.
        """
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed: session %s", self.session.id[:8])
        except Exception as e:
            logger.exception("Error closing browser: %s", e)

    def __repr__(self) -> str:
        return f"Browser(session={self.session.id[:8]}, connected={self.page is not None})"