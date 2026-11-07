"""Deterministic execution of browser action lists (automations).

The old automation path stored a JSON list of steps and then asked the model to
translate every step into a separate ``browse_action`` call.  That made a
20-step recipe 20 LLM turns, 20 CDP connections and 20 chances to drift.

This module is the execution layer the tools and the script library were
missing: it runs the whole list on the *same* live page, with alias
normalization, variable interpolation, per-step timeouts/retries and a compact
result the model can reason about.

Steps are data, never code.  The vocabulary is shared by:

* ``browse_action(action="batch", steps=[...])`` — ad-hoc sequences;
* ``run_browser_script(script_id=...)`` — saved per-site recipes;
* the recorder (user events become steps).

Supported actions
-----------------
``goto``/``navigate``, ``click``, ``fill``/``type``, ``press``, ``select``,
``hover``, ``scroll``, ``wait``/``wait_for``, ``execute``/``evaluate``,
``extract``, ``assert``, ``reload``, ``back``, ``forward``, ``new_tab``,
``switch_tab``, ``close_tab``, ``screenshot``.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional

from codx.junior.browser import tabs as browser_tabs

logger = logging.getLogger(__name__)

#: Maximum steps accepted in one batch (protects the live browser).
MAX_STEPS = 100

#: Default per-step timeout (ms).
DEFAULT_STEP_TIMEOUT_MS = 15000

#: Aliases accepted for the same action.  The script library historically used
#: the left side while ``browse_action`` used the right side; both now work.
ACTION_ALIASES = {
    "goto": "navigate",
    "open": "navigate",
    "type": "fill",
    "wait_for": "wait",
    "waitfor": "wait",
    "evaluate": "execute",
    "run": "execute",
    "go_back": "back",
    "go_forward": "forward",
    "reload_page": "reload",
    "screenshot_page": "screenshot",
    "open_tab": "new_tab",
    "swap_tab": "switch_tab",
}

#: Actions that do not change the page and therefore do not need the AI lease.
READ_ONLY_ACTIONS = {"text", "links", "snapshot", "tabs", "extract", "assert"}

#: Placeholder syntax: ``{{name}}`` (also supports ``{{ name }}``).
_VAR_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")


class StepError(RuntimeError):
    """A single step failed; carries the index and a compact context."""

    def __init__(self, index: int, action: str, message: str):
        super().__init__(message)
        self.index = index
        self.action = action
        self.message = message


def normalize_action(value: Any) -> str:
    """Return the canonical action name for *value*."""
    action = str(value or "").strip().lower()
    return ACTION_ALIASES.get(action, action)


def normalize_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one step (action alias, target/flat fields, defaults)."""
    if not isinstance(step, dict):
        raise ValueError(f"step must be an object, got {type(step).__name__}")
    step = dict(step)
    action = step.get("action") or step.get("type")
    if not action:
        raise ValueError("step is missing 'action'")
    step["action"] = normalize_action(action)

    # ``target`` can be a string selector or an object with selector/ref/text/
    # role/name/label.  Flatten it into the step for the dispatcher.
    target = step.get("target")
    if isinstance(target, str):
        step.setdefault("selector", target)
    elif isinstance(target, dict):
        for key in ("selector", "ref", "text", "role", "name", "label", "url"):
            if target.get(key) is not None and step.get(key) is None:
                step[key] = target[key]
    return step


def interpolate(value: Any, variables: Optional[Dict[str, Any]]) -> Any:
    """Replace ``{{name}}`` placeholders in strings, recursively."""
    if not variables:
        return value
    if isinstance(value, str):
        def replace(match):
            key = match.group(1)
            if key not in variables:
                raise ValueError(f"missing variable '{key}'")
            return str(variables[key])
        return _VAR_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [interpolate(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: interpolate(item, variables) for key, item in value.items()}
    return value


def _first(step: Dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if step.get(name) is not None:
            return step[name]
    return default


def _timeout(step: Dict[str, Any]) -> int:
    try:
        return max(250, min(int(_first(step, "timeout_ms", "timeout", default=DEFAULT_STEP_TIMEOUT_MS)), 120000))
    except Exception:
        return DEFAULT_STEP_TIMEOUT_MS


async def _click(browser, step):
    if step.get("ref"):
        return await browser.click_ref(step["ref"])
    if step.get("selector"):
        return await browser.click(step["selector"])
    if step.get("role"):
        return await browser.click_role(step["role"], _first(step, "name", "text", default=""))
    if step.get("text"):
        return await browser.click_text(step["text"])
    raise ValueError("click needs target ref, selector, role or text")


async def _fill(browser, step):
    value = _first(step, "value", "text", default="")
    if step.get("ref"):
        return await browser.fill_ref(step["ref"], str(value))
    if step.get("selector"):
        return await browser.fill(step["selector"], str(value))
    if step.get("label"):
        return await browser.fill_label(step["label"], str(value))
    if step.get("role"):
        # A role alone cannot identify an input reliably; require a label/ref.
        raise ValueError("fill needs target ref, selector or label")
    raise ValueError("fill needs target ref, selector or label")


async def _wait(browser, step):
    timeout = _timeout(step)
    if step.get("text"):
        return await browser.wait_for_text(str(step["text"]), timeout=timeout)
    if step.get("selector"):
        return await browser.wait_for_selector(step["selector"], timeout=timeout)
    if step.get("url"):
        # Poll the current URL without adding a new page API.
        deadline = timeout / 1000.0
        elapsed = 0.0
        while elapsed < deadline:
            if step["url"] in (browser.page.url or ""):
                return
            await asyncio.sleep(0.2)
            elapsed += 0.2
        raise TimeoutError(f"URL did not contain {step['url']!r} within {timeout}ms")
    raise ValueError("wait needs target text, selector or url")


async def _extract(browser, step):
    selector = _first(step, "selector", "target", default="")
    if isinstance(selector, dict):
        selector = selector.get("selector", "")
    selector = str(selector or "").replace('"', '\\"')
    if not selector:
        raise ValueError("extract needs a selector")
    attribute = str(step.get("attribute") or "").replace('"', '\\"')
    multiple = bool(step.get("multiple"))
    attr_js = f'el.getAttribute("{attribute}")' if attribute else "null"
    if multiple:
        script = (
            f'return Array.from(document.querySelectorAll("{selector}")).map(el => '
            f'({attr_js}) !== null ? {attr_js} : (el.innerText || el.textContent || "").trim());'
        )
    else:
        script = (
            f'const el = document.querySelector("{selector}"); if (!el) return null; '
            f'return ({attr_js}) !== null ? {attr_js} : (el.innerText || el.textContent || "").trim();'
        )
    return await browser.execute_script(script)


async def _assert(browser, step, outputs):
    expr = str(_first(step, "expression", "expr", "script", default="")).strip()
    if not expr:
        raise ValueError("assert needs an expression")
    # Outputs are injected as a JSON literal so the assertion can use them.
    import json
    literal = json.dumps(outputs or {}, ensure_ascii=False, default=str)
    script = f"const outputs = {literal}; return Boolean({expr});"
    ok = await browser.execute_script(script)
    if not ok:
        raise AssertionError(step.get("message") or f"assertion failed: {expr}")
    return ok


async def run_steps(
    browser,
    steps: List[Dict[str, Any]],
    variables: Optional[Dict[str, Any]] = None,
    *,
    on_step: Optional[Any] = None,
    stop_on_error: bool = True,
) -> Dict[str, Any]:
    """Execute *steps* on *browser* and return a compact result.

    Args:
        browser: Connected :class:`~codx.junior.browser.browser.Browser`.
        steps: Ordered action list (already parsed from the script).
        variables: Values for ``{{name}}`` placeholders.
        on_step: Optional callable(index, step, result, error) for progress.
        stop_on_error: Stop at the first non-optional failure (default True).

    Returns:
        Dict with ``ok``, ``steps`` (per-step timing/result), ``outputs``,
        ``failed_step`` and ``error``.
    """
    if not isinstance(steps, list):
        raise ValueError("steps must be a list")
    if len(steps) > MAX_STEPS:
        raise ValueError(f"too many steps ({len(steps)} > {MAX_STEPS})")

    normalized = [normalize_step(interpolate(step, variables)) for step in steps]
    outputs: Dict[str, Any] = {}
    results: List[Dict[str, Any]] = []
    started = time.monotonic()
    failed_index: Optional[int] = None
    error_message: Optional[str] = None

    for index, step in enumerate(normalized):
        action = step["action"]
        step_started = time.monotonic()
        attempts = max(1, min(int(step.get("retries", 0) or 0) + 1, 5))
        last_error: Optional[Exception] = None
        value = None
        for attempt in range(attempts):
            try:
                if action == "navigate":
                    url = _first(step, "url", "value")
                    if not url:
                        raise ValueError("navigate needs url")
                    value = await browser.navigate(str(url))
                elif action == "click":
                    value = await _click(browser, step)
                elif action == "fill":
                    value = await _fill(browser, step)
                elif action == "press":
                    if not step.get("selector") or not step.get("key"):
                        raise ValueError("press needs selector and key")
                    value = await browser.press(step["selector"], step["key"])
                elif action == "select":
                    if not step.get("selector") or step.get("value") is None:
                        raise ValueError("select needs selector and value")
                    value = await browser.select(step["selector"], step["value"])
                elif action == "hover":
                    if not step.get("selector"):
                        raise ValueError("hover needs selector")
                    value = await browser.hover(step["selector"])
                elif action == "scroll":
                    value = await browser.scroll(int(step.get("x", 0) or 0), int(step.get("y", 0) or 0))
                elif action == "wait":
                    value = await _wait(browser, step)
                elif action == "execute":
                    script = _first(step, "script", "code", "value")
                    if not script:
                        raise ValueError("execute needs script")
                    value = await browser.execute_script(str(script))
                elif action == "extract":
                    value = await _extract(browser, step)
                    name = str(step.get("as") or step.get("name") or f"step_{index}")
                    outputs[name] = value
                elif action == "assert":
                    value = await _assert(browser, step, outputs)
                elif action == "reload":
                    value = await browser.reload()
                elif action == "back":
                    value = await browser.go_back()
                elif action == "forward":
                    value = await browser.go_forward()
                elif action == "new_tab":
                    value = await browser_tabs.open_tab(browser, step.get("url"))
                elif action == "switch_tab":
                    value = await browser_tabs.switch_tab(browser, step.get("index"))
                elif action == "close_tab":
                    value = await browser_tabs.close_tab(browser, step.get("index"))
                elif action == "screenshot":
                    value = await browser.get_screenshot(full_page=bool(step.get("full_page", False)))
                    outputs.setdefault("screenshots", []).append({"index": index, "length": len(value or "")})
                else:
                    raise ValueError(f"unknown action '{action}'")
                last_error = None
                break
            except Exception as ex:
                last_error = ex
                if attempt + 1 < attempts:
                    await asyncio.sleep(min(0.25 * (attempt + 1), 1.0))
        duration = round((time.monotonic() - step_started) * 1000, 1)
        if last_error is not None:
            error_message = str(last_error)
            result = {
                "index": index,
                "action": action,
                "ok": False,
                "ms": duration,
                "error": error_message,
            }
            results.append(result)
            if on_step:
                try:
                    on_step(index, step, result, last_error)
                except Exception:
                    logger.debug("on_step callback failed", exc_info=True)
            if step.get("optional") or not stop_on_error:
                error_message = None
                continue
            failed_index = index
            break
        result = {
            "index": index,
            "action": action,
            "ok": True,
            "ms": duration,
        }
        if action in ("extract", "assert") and step.get("as"):
            result["as"] = step.get("as")
        results.append(result)
        if on_step:
            try:
                on_step(index, step, result, None)
            except Exception:
                logger.debug("on_step callback failed", exc_info=True)

    total_ms = round((time.monotonic() - started) * 1000, 1)
    return {
        "ok": failed_index is None,
        "steps": results,
        "outputs": outputs,
        "failed_step": failed_index,
        "error": error_message,
        "ms": total_ms,
    }
