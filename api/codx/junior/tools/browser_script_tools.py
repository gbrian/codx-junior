"""Tools that let a model build and reuse a library of browser scripts.

The recipes themselves live in :mod:`codx.junior.browser.scripts` (per project,
under ``.codx/browser_scripts``).  These tools are the LLM facing layer:

* ``list_browser_scripts``  — check what is already known for a site
* ``get_browser_script``    — load the steps to replay
* ``save_browser_script``   — create/update a recipe (auto versioned)
* ``delete_browser_script`` — soft delete

``BROWSER_SCRIPT_TOOLS`` is ready to be merged into the global tool registry
(``codx/junior/tools/__init__.py``) with the same entry shape as every other
tool: ``{tool_json, settings, tags, tool_call}``.

Dispatch contract (same as ``browser_tools.py``)
------------------------------------------------
The registry marks these tools with ``project_settings=True``, so SmolAgent
calls them with a **``settings`` keyword argument** (a ``CODXJuniorSettings``)
plus ``chat_id``/anything else it decides to inject.  A tool whose signature
does not accept those names fails during dispatch, before its body runs::

    Error executing tool 'save_browser_script':
      save_browser_script() got an unexpected keyword argument 'settings'

Every tool here therefore declares ``settings`` and ``chat_id`` explicitly and
ends with ``**kwargs`` to stay forward compatible — exactly like the tools in
``browser_tools.py``. The injected settings are the *authoritative* source of
the project folder used to locate ``.codx/browser_scripts``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from codx.junior.browser.scripts import (
    BrowserScriptStore,
    STEPS,
    normalize_site,
    parse_steps,
)
from codx.junior.tools.model import ToolResponse

logger = logging.getLogger(__name__)

# Browser tools are async and need the project settings: reuse the exact same
# settings object as the existing browser tools so behaviour stays aligned.
try:  # pragma: no cover - depends on the surrounding registry
    from codx.junior.tools.browser_tools import BROWSER_TOOL_SETTINGS as _BROWSER_SETTINGS
except Exception:  # pragma: no cover
    _BROWSER_SETTINGS = None

#: Registry metadata for every browser script tool. Kept as a private copy of
#: ``BROWSER_TOOL_SETTINGS``: the tools need ``project_settings`` injection, and
#: a missing/renamed import must never downgrade them to a settings-less tool
#: (that would make them silently resolve an unrelated project folder).
BROWSER_SCRIPT_TOOL_SETTINGS: Dict[str, Any] = {
    "async": True,
    "is_async": True,
    "project_settings": True,
    "dual_response": True,
    "scope": "chat",
    # The library is mutated by save/delete: never serve a cached result.
    "cache": False,
}
if isinstance(_BROWSER_SETTINGS, dict):
    BROWSER_SCRIPT_TOOL_SETTINGS.update(_BROWSER_SETTINGS)


# --------------------------------------------------------------------------- #
# project resolution
# --------------------------------------------------------------------------- #
def _settings_value(settings: Any, *names: str) -> Optional[str]:
    """Read the first non-empty attribute/key from the injected settings."""
    if not settings:
        return None
    for name in names:
        try:
            value = settings.get(name) if isinstance(settings, dict) else getattr(settings, name, None)
        except Exception:
            value = None
        if callable(value):
            try:
                value = value()
            except Exception:
                logger.debug("settings.%s() failed", name, exc_info=True)
                value = None
        if value:
            return str(value)
    return None


def resolve_project_path(
    project_id: Optional[str] = None,
    project_path: Optional[str] = None,
    settings: Any = None,
) -> str:
    """Resolve the project folder that owns ``.codx/browser_scripts``.

    Order: explicit ``project_path`` argument, the **injected** ``settings``
    (the dispatcher passes the chat's real ``CODXJuniorSettings``), settings
    looked up by ``project_id``, environment, current working directory.
    """
    if project_path:
        return os.path.abspath(os.path.expanduser(str(project_path)))

    path = _settings_value(settings, "project_path", "get_project_path", "project_folder", "code_path")
    if path:
        return os.path.abspath(os.path.expanduser(path))

    try:  # pragma: no cover - settings are optional in unit tests
        from codx.junior.settings import CODXJuniorSettings

        if project_id:
            try:
                resolved = CODXJuniorSettings.from_project_id(project_id)
                path = _settings_value(resolved, "project_path", "get_project_path")
                if path:
                    return os.path.abspath(os.path.expanduser(path))
            except Exception:
                logger.debug("Could not resolve project_id %s", project_id, exc_info=True)
    except Exception:
        logger.debug("CODXJuniorSettings not available", exc_info=True)

    for key in ("CODX_PROJECT_PATH", "CODX_JUNIOR_PROJECT_PATH", "PROJECT_PATH"):
        value = os.environ.get(key)
        if value:
            return os.path.abspath(os.path.expanduser(value))

    logger.warning(
        "browser scripts: no project path available (settings=%s, project_id=%s); using cwd %s",
        type(settings).__name__ if settings else None,
        project_id,
        os.getcwd(),
    )
    return os.getcwd()


def _store(
    project_id: Optional[str] = None,
    project_path: Optional[str] = None,
    settings: Any = None,
) -> BrowserScriptStore:
    root = resolve_project_path(project_id=project_id, project_path=project_path, settings=settings)
    logger.debug("browser scripts store root: %s", root)
    return BrowserScriptStore(root)


def _response(llm_response: str, user_response: Optional[str] = None) -> ToolResponse:
    return ToolResponse(
        user_response=user_response or llm_response,
        llm_response=llm_response,
    )


# --------------------------------------------------------------------------- #
# tools
# --------------------------------------------------------------------------- #
async def list_browser_scripts(
    query: Optional[str] = None,
    site: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20,
    project_id: Optional[str] = None,
    project_path: Optional[str] = None,
    settings: Any = None,
    chat_id: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """List/inspect the saved scripts (see ``BROWSER_SCRIPT_TOOLS`` schema).

    Args:
        settings: Injected ``CODXJuniorSettings`` (``project_settings=True``).
        chat_id: Injected by SmolAgent; unused, accepted for compatibility.
        **kwargs: Any other injected value.
    """
    store = _store(project_id=project_id, project_path=project_path, settings=settings)
    entries = store.search_scripts(query=query, site=site, tags=tags, limit=limit or 20)
    if not entries:
        return _response(
            "No saved browser scripts matched"
            + (f" for site `{normalize_site(site)}`" if site else "")
            + ".\n\nYou are exploring this site for the first time: browse it normally, then call "
            "`save_browser_script` with the click/type steps that worked so the next visit is fast."
        )
    return _response(
        f"Saved browser scripts ({len(entries)}):\n\n"
        f"{store.to_markdown(entries)}\n\n"
        "Call `get_browser_script` with an id to load the steps and replay them with `browse_action`."
    )


async def get_browser_script(
    script_id: Optional[str] = None,
    title: Optional[str] = None,
    site: Optional[str] = None,
    include_code: bool = True,
    project_id: Optional[str] = None,
    project_path: Optional[str] = None,
    settings: Any = None,
    chat_id: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """Load a saved script by id, or by title (+ site)."""
    store = _store(project_id=project_id, project_path=project_path, settings=settings)
    script = store.get_script(script_id) if script_id else None
    if not script and title:
        script = store.find_script(title=title, site=site)
    if not script:
        candidates = store.search_scripts(site=site, limit=10)
        hint = ""
        if candidates:
            hint = "\n\nAvailable scripts for this site:\n" + store.to_markdown(candidates)
        return _response(f"Browser script not found (`script_id={script_id}`, `title={title}`).{hint}")
    store.mark_used(script.id)
    return _response(store.render_script(script, include_code=include_code))


async def save_browser_script(
    title: str,
    code: Any,
    site: Optional[str] = None,
    description: str = "",
    language: str = STEPS,
    tags: Optional[List[str]] = None,
    script_id: Optional[str] = None,
    project_id: Optional[str] = None,
    project_path: Optional[str] = None,
    settings: Any = None,
    chat_id: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """Create or update a script (same ``script_id``, or same title+site)."""
    store = _store(project_id=project_id, project_path=project_path, settings=settings)
    try:
        script = store.save_script(
            title=title,
            code=code,
            site=site,
            description=description,
            language=language,
            tags=tags,
            script_id=script_id,
        )
    except ValueError as error:
        return _response(f"Invalid browser script: {error}")
    except Exception as error:  # pragma: no cover - defensive
        logger.exception("Could not save browser script")
        return _response(f"Could not save browser script: {error}")
    return _response(
        f"Browser script saved: `{script.title}` ({script.site}, {script.language}, v{script.version}).\n\n"
        f"{store.render_script(script)}\n\n"
        f"Next time, call `get_browser_script` with `script_id=\"{script.id}\"` before exploring the site."
    )


async def delete_browser_script(
    script_id: str = "",
    hard: bool = False,
    project_id: Optional[str] = None,
    project_path: Optional[str] = None,
    settings: Any = None,
    chat_id: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """Delete a script (soft delete: moved to ``.codx/browser_scripts/.trash``)."""
    if not script_id:
        return _response("`script_id` is required to delete a browser script.")
    store = _store(project_id=project_id, project_path=project_path, settings=settings)
    deleted = store.delete_script(script_id, hard=hard)
    if not deleted:
        return _response(f"Browser script `{script_id}` does not exist.")
    if hard:
        return _response(f"Browser script `{script_id}` permanently deleted.")
    return _response(f"Browser script `{script_id}` moved to `.codx/browser_scripts/.trash`.")


async def run_browser_script(
    script_id: Optional[str] = None,
    title: Optional[str] = None,
    site: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    project_id: Optional[str] = None,
    project_path: Optional[str] = None,
    settings: Any = None,
    chat_id: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """Execute a saved script end-to-end on the shared browser.

    This is the fast path for automations: the whole step list runs on the
    session's persistent Playwright connection, in one tool call, instead of the
    model translating each step into a separate ``browse_action``.  The model is
    only needed again if a step fails.
    """
    if not settings:
        return _response(
            "Cannot run a browser script without the project settings. "
            "Open the browser from a chat so the session is available."
        )
    store = _store(project_id=project_id, project_path=project_path, settings=settings)
    script = store.get_script(script_id) if script_id else None
    if not script and title:
        script = store.find_script(title=title, site=site)
    if not script:
        return _response(
            "Browser script not found. Call list_browser_scripts(site=...) first."
        )
    steps = parse_steps(script.code) if script.language == STEPS else []
    if not steps:
        return _response(
            f"Script '{script.title}' has no executable steps (language={script.language}). "
            "Only language='steps' scripts can run."
        )

    try:
        from codx.junior.browser.browser_manager import get_browser_manager
        manager = get_browser_manager(settings)
    except Exception as ex:
        return _response(f"Browser manager unavailable: {ex}")

    session = manager.get_session(session_id) if session_id else None
    if not session and chat_id:
        session = manager.get_session_for_chat(chat_id)
    if not session:
        return _response(
            "No browser session found. Call start_session first, then run the script."
        )
    if session.status != "running":
        try:
            import asyncio
            session = await manager.restart_session(session.id)
        except Exception as ex:
            return _response(f"Session {session.id} is not running and could not be restarted: {ex}")

    import time
    started = time.monotonic()
    try:
        runtime = await manager.get_runtime(session)
        result = await runtime.run_steps(steps, variables or {})
    except Exception as ex:
        # BrowserControlError and step failures both end here.
        manager.log_activity(
            session,
            actor="ai",
            action="run_script",
            chat_id=chat_id,
            params={"script_id": script.id, "title": script.title, "steps": len(steps)},
            success=False,
            error=str(ex),
            duration_ms=(time.monotonic() - started) * 1000,
        )
        return _response(
            f"❌ Script '{script.title}' stopped: {ex}\n\n"
            "Call browser_activity to see the page state, fix the failing step, "
            "and save a new version with save_browser_script(script_id=...)."
        )

    store.mark_used(script.id)
    session = getattr(runtime, "session", None) or session
    manager.log_activity(
        session,
        actor="ai",
        action="run_script",
        chat_id=chat_id,
        params={"script_id": script.id, "title": script.title, "steps": len(steps)},
        url=session.current_url,
        title=session.current_title,
        duration_ms=(time.monotonic() - started) * 1000,
        result={
            "ok": result.get("ok"),
            "failed_step": result.get("failed_step"),
            "ms": result.get("ms"),
        },
    )
    lines = [
        f"- [{step.get('index')}] {'ok' if step.get('ok') else 'FAIL'} {step.get('action')} ({step.get('ms')} ms)"
        for step in (result.get("steps") or [])
    ]
    outputs = result.get("outputs") or {}
    body = (
        f"Script '{script.title}' ({script.site}, v{script.version}) "
        f"{'completed' if result.get('ok') else 'FAILED'} in {result.get('ms')} ms.\n"
        + "\n".join(lines)
    )
    if result.get("error"):
        body += f"\nFailed at step {result.get('failed_step')}: {result.get('error')}"
    if outputs:
        import json
        body += "\nOutputs: " + json.dumps(outputs, ensure_ascii=False, default=str)[:4000]
    return _response(body)


# --------------------------------------------------------------------------- #
# registry entries
# --------------------------------------------------------------------------- #
BROWSER_SCRIPT_TOOLS: List[Dict[str, Any]] = [
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "list_browser_scripts",
                "description": (
                    "List reusable browser scripts (per-site navigation recipes) saved by previous sessions. "
                    "ALWAYS call this before exploring a site: if a recipe exists you can replay it instead of "
                    "re-discovering selectors."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Free text matched against title, description and tags, e.g. 'login'"},
                        "site": {"type": "string", "description": "Domain or URL, e.g. 'github.com'"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Only scripts carrying all these tags"},
                        "limit": {"type": "integer", "description": "Max results (default 20)"},
                    },
                    "required": [],
                },
            },
        },
        "settings": BROWSER_SCRIPT_TOOL_SETTINGS,
        "tags": ["browser", "scripts"],
        "tool_call": list_browser_scripts,
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "get_browser_script",
                "description": (
                    "Load a saved browser script by id (or by title + site). Returns the ordered steps. "
                    "Prefer run_browser_script to execute it in one call; only read the steps when you need to repair them."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_id": {"type": "string", "description": "Script id from list_browser_scripts"},
                        "title": {"type": "string", "description": "Script title, used when script_id is unknown"},
                        "site": {"type": "string", "description": "Domain to disambiguate a title"},
                        "include_code": {"type": "boolean", "description": "Include the script body (default true)"},
                    },
                    "required": [],
                },
            },
        },
        "settings": BROWSER_SCRIPT_TOOL_SETTINGS,
        "tags": ["browser", "scripts"],
        "tool_call": get_browser_script,
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "save_browser_script",
                "description": (
                    "Create or update a reusable browser script for a site. Use language='steps' and pass a JSON "
                    "array of actions (goto/navigate, click, fill/type, press, select, hover, scroll, wait/wait_for, "
                    "extract, assert, screenshot). Use refs from snapshot or stable selectors, and {{name}} for "
                    "variables. Never store passwords/tokens. Saving the same title+site, or passing script_id, "
                    "updates the script in place and bumps its version."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short human title, e.g. 'Login with password'"},
                        "code": {
                            "type": "string",
                            "description": "Script body. For language='steps': a JSON array such as [{\"action\":\"goto\",\"url\":\"https://site/login\"},{\"action\":\"type\",\"selector\":\"#user\",\"text\":\"...\"}]",
                        },
                        "site": {"type": "string", "description": "Domain or URL the script belongs to, e.g. 'github.com'"},
                        "description": {"type": "string", "description": "What the script does / when to use it"},
                        "language": {
                            "type": "string",
                            "enum": ["steps", "javascript"],
                            "description": "steps = deterministic browser actions (preferred); javascript = small in-page helper",
                        },
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Searchable labels, e.g. ['login','auth']"},
                        "script_id": {"type": "string", "description": "Existing script id to update"},
                    },
                    "required": ["title", "code"],
                },
            },
        },
        "settings": BROWSER_SCRIPT_TOOL_SETTINGS,
        "tags": ["browser", "scripts"],
        "tool_call": save_browser_script,
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "run_browser_script",
                "description": (
                    "Run a saved per-site browser script end-to-end in one call. This is the fast, "
                    "deterministic path for automations: all steps execute on the shared browser "
                    "connection and the model only intervenes if a step fails. Pass variables for "
                    "{{name}} placeholders."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_id": {"type": "string", "description": "Script id from list_browser_scripts"},
                        "title": {"type": "string", "description": "Script title when the id is unknown"},
                        "site": {"type": "string", "description": "Domain to disambiguate a title"},
                        "variables": {"type": "object", "description": "Values for {{name}} placeholders (never passwords)"},
                        "session_id": {"type": "string", "description": "Session id (optional; defaults to the chat session)"},
                    },
                    "required": [],
                },
            },
        },
        "settings": BROWSER_SCRIPT_TOOL_SETTINGS,
        "tags": ["browser", "scripts", "automation"],
        "tool_call": run_browser_script,
    },
    {
        "tool_json": {
            "type": "function",
            "function": {
                "name": "delete_browser_script",
                "description": "Soft delete a saved browser script (moved to .codx/browser_scripts/.trash). Use when a recipe is obsolete or wrong.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_id": {"type": "string", "description": "Script id to delete"},
                        "hard": {"type": "boolean", "description": "Delete permanently instead of moving to .trash"},
                    },
                    "required": ["script_id"],
                },
            },
        },
        "settings": BROWSER_SCRIPT_TOOL_SETTINGS,
        "tags": ["browser", "scripts"],
        "tool_call": delete_browser_script,
    },
]

BROWSER_SCRIPT_TOOL_NAMES = [entry["tool_json"]["function"]["name"] for entry in BROWSER_SCRIPT_TOOLS]