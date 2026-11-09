"""Resolution of the web fetch / search configuration.

Three sources are merged, in this order:

1. ``integrations[]`` of the global settings — the generic list that also hosts
   Slack/WhatsApp credentials.  Each entry is a mapping (or a pydantic model)
   shaped like ``{"name": "searxng", "url": "http://searxng:8080",
   "api_key": "...", "enabled": true, "options": {...}}``;
2. environment variables (``CODX_SEARXNG_URL``, ``BRAVE_API_KEY``, ...);
3. built-in defaults: DuckDuckGo search only, no premium fetch and no lite
   engine.

Nothing here is required for the tools to work: an empty configuration keeps the
previous behaviour (plain HTTP fetch + DuckDuckGo search) and simply adds the
guards and the reader-mode extraction.

Made with ❤️ by codx-junior
"""

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Search providers understood by :mod:`codx.junior.web.search_backends`.
SEARCH_PROVIDERS = ("searxng", "brave", "tavily", "ddgs")

#: Managed fetch providers understood by :mod:`codx.junior.web.premium`.
PREMIUM_PROVIDERS = ("jina", "firecrawl")

#: Alternative headless engines understood by :mod:`codx.junior.browser.lite_engine`.
LITE_ENGINES = ("lightpanda", "obscura")

#: Every integration name the web stack consumes.
CONFIGURABLE = SEARCH_PROVIDERS + PREMIUM_PROVIDERS + LITE_ENGINES

DEFAULT_MAX_BYTES = 3 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_OUTPUT_CHARS = 60_000
DEFAULT_SEARCH_TIMEOUT_SECONDS = 12.0
CACHE_TTL_SECONDS = 120.0

JINA_BASE_URL = "https://r.jina.ai"
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev"

_DISABLED_VALUES = ("0", "false", "no", "off", "none", "disabled")


@dataclass
class IntegrationConfig:
    """One configured web integration.

    Attributes:
        name: Integration name (``searxng``, ``brave``, ``tavily``, ``ddgs``,
            ``jina``, ``firecrawl``, ``lightpanda``, ``obscura``).
        enabled: False entries are ignored.
        url: Base URL for HTTP providers or binary path for CLI engines.
        api_key: Token used by the provider (empty when not needed).
        timeout: Per request timeout in seconds.
        options: Provider specific options (language, search_depth, args...).
    """

    name: str
    enabled: bool = True
    url: str = ""
    api_key: str = ""
    timeout: float = 20.0
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebSettings:
    """Resolved configuration of the web tools.

    Attributes:
        allow_private_hosts: Allow private / loopback fetch targets.
        max_bytes: Body size cap for outbound requests.
        timeout: Wall-clock budget of a single fetch.
        max_output_chars: Default markdown cap when the tool gets no max_length.
        browser_escalation: Allow Chromium rendering when extraction is empty.
        search_timeout: Budget of a search call.
        lite_engine: Optional CLI engine (Lightpanda / Obscura).
        premium: Optional managed fetch provider (Jina Reader / Firecrawl).
        search_backends: Ordered search providers.
    """

    allow_private_hosts: bool = False
    max_bytes: int = DEFAULT_MAX_BYTES
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS
    browser_escalation: bool = True
    search_timeout: float = DEFAULT_SEARCH_TIMEOUT_SECONDS
    lite_engine: Optional[IntegrationConfig] = None
    premium: Optional[IntegrationConfig] = None
    search_backends: List[IntegrationConfig] = field(
        default_factory=lambda: [IntegrationConfig(name="ddgs")]
    )


_cached_settings: Optional[WebSettings] = None
_cached_at: float = 0.0


def _env(name: str) -> str:
    """Return a stripped environment value ('' when unset)."""
    return (os.environ.get(name) or "").strip()


def _env_flag(name: str, default: bool) -> bool:
    """Return a boolean environment flag."""
    value = _env(name).lower()
    if not value:
        return default
    return value not in _DISABLED_VALUES


def _env_int(name: str, default: int) -> int:
    """Return an integer environment value, or ``default``."""
    try:
        return int(_env(name))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    """Return a float environment value, or ``default``."""
    try:
        return float(_env(name))
    except (TypeError, ValueError):
        return default


def _as_mapping(entry: Any) -> Dict[str, Any]:
    """Normalize a settings entry (dict or pydantic model) into a dict."""
    if isinstance(entry, dict):
        return dict(entry)

    for attribute in ("model_dump", "dict"):
        method = getattr(entry, attribute, None)
        if callable(method):
            try:
                data = method()
                if isinstance(data, dict):
                    return data
            except Exception:  # pragma: no cover - defensive
                pass

    return {}


def _integration_config(entry: Any) -> Optional[IntegrationConfig]:
    """Build an :class:`IntegrationConfig` from a raw settings entry."""
    data = _as_mapping(entry)
    name = str(
        data.get("name") or data.get("type") or data.get("provider") or ""
    ).strip().lower()
    if not name:
        return None

    enabled = data.get("enabled", True)
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() not in _DISABLED_VALUES

    options = data.get("options") or {}
    if not isinstance(options, dict):
        options = {}

    url = str(
        data.get("url") or data.get("base_url") or data.get("endpoint")
        or data.get("binary") or ""
    ).strip()
    api_key = str(data.get("api_key") or data.get("token") or data.get("key") or "").strip()

    try:
        timeout = float(data.get("timeout") or 20.0)
    except (TypeError, ValueError):
        timeout = 20.0

    return IntegrationConfig(
        name=name,
        enabled=bool(enabled),
        url=url,
        api_key=api_key,
        timeout=timeout,
        options=options,
    )


def _global_integrations() -> List[Any]:
    """Read ``integrations[]`` from the global settings (never raises)."""
    try:
        from codx.junior.global_settings import read_global_settings

        settings = read_global_settings()
    except Exception as ex:  # settings not loadable (tests, CLI...)
        logger.debug("global settings unavailable: %s", ex)
        return []

    raw = getattr(settings, "integrations", None)
    if isinstance(raw, dict):
        raw = raw.get("integrations") or raw.get("items") or []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return []


def _apply_env(configs: Dict[str, IntegrationConfig], order: List[str]) -> None:
    """Add the integrations that are only declared through environment variables."""

    def add(config: IntegrationConfig) -> None:
        if config.name in configs:
            return
        configs[config.name] = config
        order.append(config.name)

    searxng_url = _env("CODX_SEARXNG_URL") or _env("SEARXNG_URL")
    if searxng_url:
        add(IntegrationConfig(name="searxng", url=searxng_url))

    brave_key = (
        _env("CODX_BRAVE_API_KEY") or _env("BRAVE_API_KEY") or _env("BRAVE_SEARCH_API_KEY")
    )
    if brave_key:
        add(IntegrationConfig(name="brave", url=_env("CODX_BRAVE_URL"), api_key=brave_key))

    tavily_key = _env("CODX_TAVILY_API_KEY") or _env("TAVILY_API_KEY")
    if tavily_key:
        add(IntegrationConfig(name="tavily", url=_env("CODX_TAVILY_URL"), api_key=tavily_key))

    jina_url = _env("CODX_JINA_READER_URL") or _env("JINA_READER_URL")
    jina_key = _env("CODX_JINA_API_KEY") or _env("JINA_API_KEY")
    if jina_url or jina_key:
        add(IntegrationConfig(name="jina", url=jina_url or JINA_BASE_URL, api_key=jina_key))

    firecrawl_url = _env("CODX_FIRECRAWL_URL") or _env("FIRECRAWL_URL")
    firecrawl_key = _env("CODX_FIRECRAWL_API_KEY") or _env("FIRECRAWL_API_KEY")
    if firecrawl_url or firecrawl_key:
        add(IntegrationConfig(
            name="firecrawl",
            url=firecrawl_url or FIRECRAWL_BASE_URL,
            api_key=firecrawl_key,
        ))

    for name, variable in (("lightpanda", "CODX_LIGHTPANDA_BIN"),
                           ("obscura", "CODX_OBSCURA_BIN")):
        binary = _env(variable)
        if binary:
            add(IntegrationConfig(name=name, url=binary))


def _resolve_lite_engine(configs: Dict[str, IntegrationConfig]) -> Optional[IntegrationConfig]:
    """Pick the CLI engine to use for JavaScript escalation (opt-in)."""
    requested = _env("CODX_WEB_LITE_ENGINE").lower()
    if requested in _DISABLED_VALUES:
        return None
    if requested in LITE_ENGINES:
        return configs.get(requested) or IntegrationConfig(
            name=requested, url=shutil.which(requested) or requested
        )
    return next((configs[name] for name in LITE_ENGINES if name in configs), None)


def _resolve_premium(configs: Dict[str, IntegrationConfig]) -> Optional[IntegrationConfig]:
    """Pick the managed fetch provider (off unless explicitly enabled)."""
    requested = _env("CODX_WEB_PREMIUM_PROVIDER").lower()
    if requested in _DISABLED_VALUES:
        return None
    if requested in PREMIUM_PROVIDERS:
        default_url = JINA_BASE_URL if requested == "jina" else FIRECRAWL_BASE_URL
        return configs.get(requested) or IntegrationConfig(name=requested, url=default_url)
    return next((configs[name] for name in PREMIUM_PROVIDERS if name in configs), None)


def _resolve_search_backends(
    configs: Dict[str, IntegrationConfig],
    order: List[str],
) -> List[IntegrationConfig]:
    """Return the ordered search providers (DuckDuckGo last by default)."""
    requested = [
        name.strip().lower()
        for name in (_env("CODX_WEB_SEARCH_BACKENDS") or "").split(",")
        if name.strip()
    ]
    names = requested or [name for name in order if name in SEARCH_PROVIDERS]

    if _env_flag("CODX_WEB_SEARCH_DDGS", True):
        names.append("ddgs")

    names = [name for name in dict.fromkeys(names) if name in SEARCH_PROVIDERS]
    if not names:
        names = ["ddgs"]

    return [configs.get(name) or IntegrationConfig(name=name) for name in names]


def _build() -> WebSettings:
    """Build the settings from the global settings + environment."""
    configs: Dict[str, IntegrationConfig] = {}
    order: List[str] = []

    for entry in _global_integrations():
        config = _integration_config(entry)
        if not config or not config.enabled or config.name not in CONFIGURABLE:
            continue
        if config.name not in configs:
            order.append(config.name)
        configs[config.name] = config

    _apply_env(configs, order)

    return WebSettings(
        allow_private_hosts=_env_flag("CODX_WEB_FETCH_ALLOW_PRIVATE_HOSTS", False),
        max_bytes=_env_int("CODX_WEB_FETCH_MAX_BYTES", DEFAULT_MAX_BYTES),
        timeout=_env_float("CODX_WEB_FETCH_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        max_output_chars=_env_int(
            "CODX_WEB_FETCH_MAX_OUTPUT_CHARS", DEFAULT_MAX_OUTPUT_CHARS
        ),
        browser_escalation=_env_flag("CODX_WEB_FETCH_BROWSER_ESCALATION", True),
        search_timeout=_env_float(
            "CODX_WEB_SEARCH_TIMEOUT_SECONDS", DEFAULT_SEARCH_TIMEOUT_SECONDS
        ),
        lite_engine=_resolve_lite_engine(configs),
        premium=_resolve_premium(configs),
        search_backends=_resolve_search_backends(configs, order),
    )


def load_web_settings(refresh: bool = False) -> WebSettings:
    """Return the resolved web settings (cached for a couple of minutes).

    Args:
        refresh: Ignore the cache and rebuild from the sources.

    Returns:
        WebSettings: Resolved configuration; defaults are returned when the
        global settings cannot be read (the tools must never fail on settings).

    Example:
        >>> load_web_settings().search_backends[0].name
        'ddgs'
    """
    global _cached_settings, _cached_at

    now = time.monotonic()
    if not refresh and _cached_settings and now - _cached_at < CACHE_TTL_SECONDS:
        return _cached_settings

    try:
        resolved = _build()
    except Exception as ex:  # pragma: no cover - defensive
        logger.warning("web settings could not be resolved, using defaults: %s", ex)
        resolved = WebSettings()

    _cached_settings = resolved
    _cached_at = now
    return resolved


def reset_cache() -> None:
    """Drop the cached settings (used by tests and after a settings update)."""
    global _cached_settings, _cached_at
    _cached_settings = None
    _cached_at = 0.0
