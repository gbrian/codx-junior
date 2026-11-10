"""Web search providers behind the ``web_search`` tool.

Each provider is a small function with the same signature, so the chain can be
reordered or extended from the settings without touching the tool. The chain is
tried in order and the first provider that answers with results wins.

The errors of the providers that did not answer travel with the response: an
empty result set from a misconfigured SearXNG is **not** the same as "this does
not exist", and the model must be able to tell both apart.

Made with ❤️ by codx-junior
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from urllib.parse import urlsplit

import requests

from codx.junior.web.settings import IntegrationConfig, SEARCH_PROVIDERS, load_web_settings

logger = logging.getLogger(__name__)

#: Snippet length handed to the model. Long enough to decide whether a result is
#: worth fetching, short enough to keep several results in context.
DEFAULT_SNIPPET_CHARS = 300

#: Hard cap: more results than this never fit a useful context.
MAX_RESULTS_LIMIT = 20

#: Search types supported by the tool.
SEARCH_TYPES = ("web", "news", "images")

_USER_AGENT = "codx-junior/1.0 (+web_search tool)"

_SEARXNG_CATEGORIES = {"web": "general", "news": "news", "images": "images"}

_BRAVE_PATHS = {
    "web": "/res/v1/web/search",
    "news": "/res/v1/news/search",
    "images": "/res/v1/images/search",
}


class SearchBackendError(RuntimeError):
    """Raised by a provider that cannot answer (missing config or bad reply)."""


@dataclass
class SearchHit:
    """One search result.

    Attributes:
        title: Result title.
        url: Result URL (always present).
        snippet: Short description of the page.
        engine: Engine that produced the result (``google``, ``bing``...).
        published: Publication date, when the backend reports one.
        image_url: Thumbnail/image URL for image searches.
    """

    title: str
    url: str
    snippet: str = ""
    engine: str = ""
    published: str = ""
    image_url: str = ""


@dataclass
class SearchResults:
    """Outcome of one search call.

    Attributes:
        query: Query that was executed.
        search_type: ``web``, ``news`` or ``images``.
        hits: Results of the provider that answered.
        backend: Name of the provider that answered.
        errors: Reasons why the other providers produced nothing.
    """

    query: str
    search_type: str = "web"
    hits: List[SearchHit] = field(default_factory=list)
    backend: str = ""
    errors: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """True when no provider returned a result."""
        return not self.hits


def _trim(text: str, limit: int = DEFAULT_SNIPPET_CHARS) -> str:
    """Collapse whitespace and cap a snippet."""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 1, 1)].rstrip() + "…"


def _domain(url: str) -> str:
    """Return the bare host of a URL ('' when it cannot be parsed)."""
    try:
        return (urlsplit(url).hostname or "").replace("www.", "", 1)
    except ValueError:
        return ""


def _dedupe(hits: List[SearchHit]) -> List[SearchHit]:
    """Keep the first hit per URL."""
    seen = set()
    unique: List[SearchHit] = []
    for hit in hits:
        if not hit.url or hit.url in seen:
            continue
        seen.add(hit.url)
        unique.append(hit)
    return unique


def search_searxng(
    config: IntegrationConfig,
    query: str,
    max_results: int,
    search_type: str,
) -> List[SearchHit]:
    """Query a SearXNG instance through its JSON API."""
    if not config.url:
        raise SearchBackendError("no url configured (set CODX_SEARXNG_URL)")

    params = {
        "q": query,
        "format": "json",
        "categories": _SEARXNG_CATEGORIES.get(search_type, "general"),
        "safesearch": 0,
    }
    extra = (config.options or {}).get("params")
    if isinstance(extra, dict):
        params.update(extra)

    headers = {"Accept": "application/json", "User-Agent": _USER_AGENT}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    response = requests.get(
        f"{config.url.rstrip('/')}/search",
        params=params,
        headers=headers,
        timeout=config.timeout,
    )
    if response.status_code >= 400:
        raise SearchBackendError(f"HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as ex:
        raise SearchBackendError(
            "the instance did not answer with JSON (add 'json' to search.formats in settings.yml)"
        ) from ex

    hits: List[SearchHit] = []
    for item in (payload.get("results") or [])[:max_results]:
        url = item.get("url") or ""
        if not url:
            continue
        hits.append(
            SearchHit(
                title=(item.get("title") or "").strip() or url,
                url=url,
                snippet=_trim(item.get("content") or ""),
                engine=(item.get("engine") or "").strip(),
                published=(item.get("publishedDate") or "").strip(),
                image_url=(item.get("img_src") or item.get("thumbnail") or "").strip(),
            )
        )
    return hits


def search_brave(
    config: IntegrationConfig,
    query: str,
    max_results: int,
    search_type: str,
) -> List[SearchHit]:
    """Query the Brave Search API (web, news or images)."""
    if not config.api_key:
        raise SearchBackendError("missing api key (BRAVE_API_KEY)")

    base = (config.url or "https://api.search.brave.com").rstrip("/")
    params = {"q": query, "count": max_results}
    if search_type == "web":
        params["text_decorations"] = 0

    response = requests.get(
        base + _BRAVE_PATHS[search_type],
        params=params,
        headers={
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
            "X-Subscription-Token": config.api_key,
        },
        timeout=config.timeout,
    )
    if response.status_code >= 400:
        raise SearchBackendError(f"HTTP {response.status_code}")

    payload = response.json() or {}
    if search_type == "web":
        items = ((payload.get("web") or {}).get("results") or [])
    else:
        items = payload.get("results") or []

    hits: List[SearchHit] = []
    for item in items[:max_results]:
        url = item.get("url") or ""
        if not url:
            continue
        hits.append(
            SearchHit(
                title=(item.get("title") or "").strip() or url,
                url=url,
                snippet=_trim(item.get("description") or ""),
                engine="brave",
                published=(item.get("age") or item.get("page_age") or "").strip(),
                image_url=((item.get("thumbnail") or {}).get("src") or ""),
            )
        )
    return hits


def search_tavily(
    config: IntegrationConfig,
    query: str,
    max_results: int,
    search_type: str,
) -> List[SearchHit]:
    """Query the Tavily search API (web and news)."""
    if not config.api_key:
        raise SearchBackendError("missing api key (TAVILY_API_KEY)")
    if search_type == "images":
        raise SearchBackendError("image search is not supported")

    base = (config.url or "https://api.tavily.com").rstrip("/")
    payload = {
        "query": query,
        "max_results": max_results,
        "include_answer": False,
        "search_depth": (config.options or {}).get("search_depth") or "basic",
        "topic": "news" if search_type == "news" else "general",
    }
    response = requests.post(
        f"{base}/search",
        json=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
            "Authorization": f"Bearer {config.api_key}",
        },
        timeout=config.timeout,
    )
    if response.status_code >= 400:
        raise SearchBackendError(f"HTTP {response.status_code}")

    hits: List[SearchHit] = []
    for item in ((response.json() or {}).get("results") or [])[:max_results]:
        url = item.get("url") or ""
        if not url:
            continue
        hits.append(
            SearchHit(
                title=(item.get("title") or "").strip() or url,
                url=url,
                snippet=_trim(item.get("content") or ""),
                engine="tavily",
                published=(item.get("published_date") or "").strip(),
            )
        )
    return hits


def search_ddgs(
    config: IntegrationConfig,
    query: str,
    max_results: int,
    search_type: str,
) -> List[SearchHit]:
    """Query DuckDuckGo through the ``ddgs`` package (no configuration).

    It scrapes the HTML endpoints, so it can legitimately return nothing for a
    valid query: the caller must not read that as "the page does not exist".
    """
    try:
        from ddgs import DDGS
    except ImportError as ex:  # pragma: no cover - dependency is declared
        raise SearchBackendError("the ddgs package is not installed") from ex

    client = DDGS(timeout=int(config.timeout or 10))
    if search_type == "news":
        items = client.news(query, max_results=max_results)
    elif search_type == "images":
        items = client.images(query, max_results=max_results)
    else:
        items = client.text(query, max_results=max_results)

    hits: List[SearchHit] = []
    for item in items or []:
        if search_type == "images":
            url = item.get("url") or ""
            image_url = item.get("image") or ""
            if not (url or image_url):
                continue
            hits.append(
                SearchHit(
                    title=(item.get("title") or "").strip() or "image",
                    url=url or image_url,
                    snippet=_trim(item.get("title") or ""),
                    engine="ddgs",
                    image_url=image_url,
                )
            )
            continue

        url = item.get("href") or item.get("url") or ""
        if not url:
            continue
        hits.append(
            SearchHit(
                title=(item.get("title") or "").strip() or url,
                url=url,
                snippet=_trim(item.get("body") or ""),
                engine=(item.get("source") or "ddgs"),
                published=(item.get("date") or "").strip(),
            )
        )
    return hits


#: Provider name -> implementation.
_BACKENDS: Dict[str, Callable[..., List[SearchHit]]] = {
    "searxng": search_searxng,
    "brave": search_brave,
    "tavily": search_tavily,
    "ddgs": search_ddgs,
}


def _backend_names(backends, settings) -> List[str]:
    """Return the ordered backend names to try."""
    items = backends if backends is not None else settings.search_backends
    names: List[str] = []
    for item in items or []:
        name = item if isinstance(item, str) else getattr(item, "name", "")
        name = (name or "").strip().lower()
        if name and name not in names:
            names.append(name)
    return names


def search_web(
    query: str,
    max_results: int = 5,
    search_type: str = "web",
    backends: Optional[List[str]] = None,
    settings=None,
    provider: Optional[str] = None,
) -> SearchResults:
    """Search the web with the configured provider chain.

    Args:
        query: Search query.
        max_results: Maximum number of results (capped at
            :data:`MAX_RESULTS_LIMIT`).
        search_type: ``web`` (default), ``news`` or ``images``.
        backends: Backend names to try, overriding the configuration.
        settings: ``WebSettings`` (read from the current configuration when
            omitted).
        provider: Force a single backend instead of the chain.

    Returns:
        SearchResults: Hits of the first backend that answered, plus the errors
        of the ones that did not.

    Raises:
        ValueError: Empty query or unsupported search type.

    Example:
        >>> result = search_web("python asyncio", backends=["ddgs"])  # doctest: +SKIP
        >>> result.backend
        'ddgs'
    """
    cleaned = (query or "").strip()
    if not cleaned:
        raise ValueError("The search query cannot be empty")
    if search_type not in SEARCH_TYPES:
        raise ValueError(
            f"Invalid search_type '{search_type}'. Must be one of: {', '.join(SEARCH_TYPES)}"
        )

    config = settings or load_web_settings()
    limit = max(1, min(int(max_results or 5), MAX_RESULTS_LIMIT))

    configured = {backend.name: backend for backend in config.search_backends}
    names = [(provider or "").strip().lower()] if provider else _backend_names(backends, config)

    results = SearchResults(query=cleaned, search_type=search_type)
    for name in names:
        implementation = _BACKENDS.get(name)
        if implementation is None:
            results.errors.append(f"{name}: unknown search backend")
            continue

        backend_config = configured.get(name) or IntegrationConfig(name=name)
        try:
            hits = implementation(backend_config, cleaned, limit, search_type)
        except Exception as ex:
            logger.warning("search backend '%s' failed: %s", name, ex)
            results.errors.append(f"{name}: {ex}")
            continue

        hits = _dedupe(hits)
        if hits:
            results.hits = hits
            results.backend = name
            return results
        results.errors.append(f"{name}: no results")

    return results