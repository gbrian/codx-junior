"""Lite headless engines (Lightpanda, Obscura) behind one adapter.

Both engines render a page with a browser written for automation instead of
Chromium: a few dozen MB of RAM and milliseconds of startup instead of hundreds
of MB and seconds. They are *renderers*, not extractors — the returned document
still goes through :mod:`codx.junior.web.extract`.

Neither ships with codx-junior, so the adapter is opt-in and does nothing when
the binary is missing:

    CODX_WEB_LITE_ENGINE=lightpanda
    CODX_LIGHTPANDA_BIN=/usr/local/bin/lightpanda

Commands are data, exactly like the browser scripts in ``browser/scripts.py``:
the argv is built as a list (never a shell string), so a configured binary path
or argument template cannot inject a command.

Made with ❤️ by codx-junior
"""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: argv template per engine. ``{url}`` and ``{dump}`` are the only placeholders
#: and are substituted without a shell.
DEFAULT_COMMANDS: Dict[str, List[str]] = {
    "lightpanda": ["fetch", "--dump", "{dump}", "--log-level", "error", "{url}"],
    "obscura": ["fetch", "--dump", "{dump}", "{url}"],
}

#: Default per call budget: a lite engine that takes longer than this is worse
#: than the Chromium container it was meant to replace.
DEFAULT_TIMEOUT_SECONDS = 30.0

#: Supported output formats (both engines take the same values).
DUMP_FORMATS = ("markdown", "html", "text")


class LiteEngineError(RuntimeError):
    """Raised when a lite engine is not usable or fails to render a page."""


@dataclass
class LiteEngine:
    """One lite headless engine driven through its CLI.

    Attributes:
        name: Engine name (``lightpanda`` or ``obscura``).
        binary: Binary path (absolute) or name resolved through ``PATH``.
        args: argv template after the binary.
        timeout: Per call timeout in seconds.
    """

    name: str
    binary: str
    args: List[str] = field(default_factory=list)
    timeout: float = DEFAULT_TIMEOUT_SECONDS

    def available(self) -> bool:
        """Return True when the binary can be executed.

        Example:
            >>> LiteEngine(name="lightpanda", binary="lightpanda").available()
            False
        """
        if not self.binary:
            return False
        if os.path.sep in self.binary:
            return os.path.isfile(self.binary) and os.access(self.binary, os.X_OK)
        return shutil.which(self.binary) is not None

    def command(self, url: str, dump: str = "markdown") -> List[str]:
        """Build the argv for one page.

        Args:
            url: Page URL (validated by the caller: the engine gets a safe URL).
            dump: Output format, one of :data:`DUMP_FORMATS`.

        Returns:
            List[str]: Ready to pass to ``subprocess.run``.
        """
        output = dump if dump in DUMP_FORMATS else "markdown"
        return [self.binary] + [
            str(part).replace("{url}", url).replace("{dump}", output) for part in self.args
        ]

    def fetch(self, url: str, dump: str = "markdown", timeout: Optional[float] = None) -> str:
        """Render ``url`` and return the requested representation.

        Args:
            url: Page URL.
            dump: Output format (``markdown``, ``html`` or ``text``).
            timeout: Override the configured timeout.

        Returns:
            str: Standard output of the engine.

        Raises:
            LiteEngineError: The engine is not installed, timed out or failed.
        """
        if not self.available():
            raise LiteEngineError(f"{self.name}: binary '{self.binary}' is not available")

        command = self.command(url, dump=dump)
        budget = float(timeout or self.timeout or DEFAULT_TIMEOUT_SECONDS)
        logger.debug("Running lite engine: %s", " ".join(command))

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=budget,
                check=False,
            )
        except subprocess.TimeoutExpired as ex:
            raise LiteEngineError(f"{self.name}: timed out after {budget}s") from ex
        except OSError as ex:
            raise LiteEngineError(f"{self.name}: could not run '{self.binary}': {ex}") from ex

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            tail = detail[-1] if detail else "no output"
            raise LiteEngineError(f"{self.name}: exit code {result.returncode}: {tail}")

        return (result.stdout or "").strip()


def _option(config: Any, key: str, default: Any = None) -> Any:
    """Read an option from an :class:`IntegrationConfig`-like object."""
    options = getattr(config, "options", None) or {}
    if isinstance(options, dict) and key in options:
        return options[key]
    return default


def load_engine(config: Any = None) -> Optional[LiteEngine]:
    """Resolve the configured lite engine.

    Args:
        config: ``IntegrationConfig`` of the engine (``WebSettings.lite_engine``).
            When omitted the current web settings are read.

    Returns:
        Optional[LiteEngine]: The engine, or ``None`` when none is configured or
        the binary is missing (the caller then falls back to Chromium).
    """
    if config is None:
        from codx.junior.web.settings import load_web_settings

        config = load_web_settings().lite_engine

    if not config or not getattr(config, "enabled", True):
        return None

    name = (getattr(config, "name", "") or "").strip().lower()
    if name not in DEFAULT_COMMANDS:
        return None

    template = _option(config, "args")
    if not isinstance(template, (list, tuple)) or not template:
        template = DEFAULT_COMMANDS[name]

    binary = (
        (getattr(config, "url", "") or "").strip()
        or str(_option(config, "binary", "") or "").strip()
        or name
    )
    try:
        timeout = float(getattr(config, "timeout", 0) or DEFAULT_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_SECONDS

    engine = LiteEngine(
        name=name,
        binary=binary,
        args=[str(part) for part in template],
        timeout=timeout,
    )
    if not engine.available():
        logger.info("lite engine '%s' configured but '%s' was not found", name, binary)
        return None
    return engine