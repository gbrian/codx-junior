"""Single entry point that plugs the browser script tools into the tool registry.

The global registry lives in ``codx/junior/tools/__init__.py`` and is big; this
module keeps the wiring down to one line there::

    from codx.junior.tools.browser_script_registration import register_browser_script_tools
    ...
    register_browser_script_tools(TOOLS)

Both registry shapes are supported, because codx-junior uses lists of
``{tool_json, settings, tags, tool_call}`` entries in some places and a
``name -> entry`` mapping in others:

* ``MutableSequence`` → append the entries that are not there yet
* ``MutableMapping``  → ``setdefault(name, entry)``

The call is idempotent (safe on module reload / repeated profile builds) and
import-cycled safe: nothing is imported from ``codx.junior.tools`` at import
time.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, List, Optional

from codx.junior.tools.browser_script_tools import (
    BROWSER_SCRIPT_TOOL_NAMES,
    BROWSER_SCRIPT_TOOLS,
)

logger = logging.getLogger(__name__)

__all__ = [
    "register_browser_script_tools",
    "ensure_registered",
    "missing_tool_names",
    "registered_tool_names",
    "BROWSER_SCRIPT_TOOLS",
    "BROWSER_SCRIPT_TOOL_NAMES",
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def tool_name(entry: Any) -> Optional[str]:
    """Return the OpenAI function name of a registry entry (or ``None``)."""
    if isinstance(entry, str):
        return entry
    if not isinstance(entry, dict):
        return None
    function = entry.get("tool_json", entry).get("function") if isinstance(entry.get("tool_json", entry), dict) else None
    if isinstance(function, dict) and function.get("name"):
        return str(function["name"])
    if entry.get("name"):
        return str(entry["name"])
    return None


def _iter_names(registry: Any) -> Iterable[str]:
    if isinstance(registry, dict):
        entries = registry.values()
    elif isinstance(registry, (list, tuple, set)):
        entries = registry
    else:
        return []
    return [name for name in (tool_name(entry) for entry in entries) if name]


def registered_tool_names(registry: Any) -> List[str]:
    """Names of the browser script tools already present in ``registry``."""
    present = set(_iter_names(registry))
    return [name for name in BROWSER_SCRIPT_TOOL_NAMES if name in present]


def missing_tool_names(registry: Any) -> List[str]:
    """Names of the browser script tools *not* present in ``registry``."""
    present = set(_iter_names(registry))
    return [name for name in BROWSER_SCRIPT_TOOL_NAMES if name not in present]


# --------------------------------------------------------------------------- #
# registration
# --------------------------------------------------------------------------- #
def register_browser_script_tools(registry: Any) -> Any:
    """Add the browser script tools to ``registry`` and return it.

    Accepts a list (appended) or a mapping (keyed by tool name). Unknown types
    are returned untouched with a warning, so a registry refactor never breaks
    the browser profile.
    """
    if registry is None:
        logger.warning("register_browser_script_tools called with None registry")
        return registry

    if isinstance(registry, dict):
        for entry in BROWSER_SCRIPT_TOOLS:
            name = tool_name(entry)
            if name and name not in registry:
                registry[name] = entry
        return registry

    if isinstance(registry, list):
        present = set(_iter_names(registry))
        for entry in BROWSER_SCRIPT_TOOLS:
            name = tool_name(entry)
            if name and name not in present:
                registry.append(entry)
                present.add(name)
        return registry

    logger.warning(
        "Unsupported tool registry type %s: browser script tools not registered",
        type(registry).__name__,
    )
    return registry


def ensure_registered(attribute: str = "TOOLS") -> List[str]:
    """Register into ``codx.junior.tools.<attribute>`` if it exists.

    Lazy (imported inside the call) so it can also be used from a FastAPI
    startup hook without circular imports. Returns the names registered now.
    """
    try:  # pragma: no cover - depends on the surrounding package
        from codx.junior import tools as tools_module
    except Exception:
        logger.debug("codx.junior.tools not importable", exc_info=True)
        return []

    registry = getattr(tools_module, attribute, None)
    if registry is None:
        logger.debug("codx.junior.tools has no %s registry", attribute)
        return []

    missing = missing_tool_names(registry)
    if not missing:
        return []
    register_browser_script_tools(registry)
    logger.info("Registered browser script tools: %s", ", ".join(missing))
    return missing