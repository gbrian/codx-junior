"""Managed fetch providers: Jina Reader and Firecrawl.

Both do the fetching *for us*: they render the page, clean it and answer with
markdown. That is very effective and it leaks every URL to a third party, so the
feature is off unless the deployment configures a provider
(``integrations[]`` entry or ``CODX_WEB_PREMIUM_PROVIDER``) **and** the caller
asks for it.

The target URL is validated by :mod:`codx.junior.web.guard` before it leaves the
process: a private address must not become a request for the provider either.

Made with ❤️ by codx-junior
"""

import logging
import re
from typing import List, Optional

import requests

from codx.junior.web.extract import ExtractedContent, clean_markdown, text_from_markdown
from codx.junior.web.settings import FIRECRAWL_BASE_URL, JINA_BASE_URL, IntegrationConfig

logger = logging.getLogger(__name__)

#: Providers this module knows how to talk to.
SUPPORTED = ("jina", "firecrawl")

#: Metadata lines that Jina Reader prepends to the markdown.
_JINA_METADATA = re.compile(
    r"^(Title|URL Source|Published Time|Description|Warning|Images):\s*(.*)$",
    re.IGNORECASE,
)

_USER_AGENT = "codx-junior/1.0 (+fetch_webpage tool)"


def _headers(config: IntegrationConfig, accept: str) -> dict:
    """Build the request headers of a provider."""
    headers = {"Accept": accept, "User-Agent": _USER_AGENT}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def _split_jina_body(body: str) -> tuple:
    """Separate the metadata preamble of a Jina Reader answer from the body.

    Returns:
        tuple: ``(metadata, markdown)``.
    """
    lines = (body or "").splitlines()
    metadata = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip().lower().startswith("markdown content:"):
            index += 1
            break
        match = _JINA_METADATA.match(line)
        if not match:
            break
        metadata[match.group(1).lower()] = match.group(2).strip()
        index += 1

    # Drop the blank lines that separate the preamble from the content.
    while index < len(lines) and not lines[index].strip():
        index += 1

    return metadata, clean_markdown("\n".join(lines[index:]))


def fetch_with_jina(url: str, config: IntegrationConfig) -> ExtractedContent:
    """Read ``url`` through Jina Reader (``r.jina.ai/<url>``)."""
    base = (config.url or JINA_BASE_URL).rstrip("/")
    target = f"{base}/{url}"
    response = requests.get(target, headers=_headers(config, "text/markdown"), timeout=config.timeout)
    if response.status_code >= 400:
        raise ValueError(f"jina reader: HTTP {response.status_code}")

    metadata, markdown = _split_jina_body(response.text)
    if not markdown:
        raise ValueError("jina reader: empty answer")

    return ExtractedContent(
        url=url,
        title=metadata.get("title", ""),
        markdown=markdown,
        text=text_from_markdown(markdown),
        extractor="jina-reader",
        site_name="r.jina.ai",
        published=metadata.get("published time", ""),
    )


def fetch_with_firecrawl(url: str, config: IntegrationConfig) -> ExtractedContent:
    """Scrape ``url`` with a Firecrawl instance (cloud or self hosted)."""
    if not config.api_key:
        raise ValueError("firecrawl: an api key is required")

    base = (config.url or FIRECRAWL_BASE_URL).rstrip("/")
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }
    response = requests.post(
        f"{base}/v1/scrape",
        json=payload,
        headers={**_headers(config, "application/json"), "Content-Type": "application/json"},
        timeout=config.timeout,
    )
    if response.status_code >= 400:
        raise ValueError(f"firecrawl: HTTP {response.status_code}")

    data = response.json() or {}
    if not data.get("success", True):
        raise ValueError(f"firecrawl: {data.get('error') or 'request failed'}")

    document = data.get("data") or {}
    markdown = clean_markdown(document.get("markdown") or "")
    if not markdown:
        raise ValueError("firecrawl: empty answer")

    metadata = document.get("metadata") or {}
    return ExtractedContent(
        url=url,
        title=metadata.get("title", "") or "",
        markdown=markdown,
        text=text_from_markdown(markdown),
        extractor="firecrawl",
        site_name=metadata.get("siteName", "") or "",
        published=metadata.get("publishedTime", "") or "",
    )


#: Provider name -> implementation.
_PROVIDERS = {
    "jina": fetch_with_jina,
    "firecrawl": fetch_with_firecrawl,
}


def premium_config(settings=None) -> Optional[IntegrationConfig]:
    """Return the configured premium provider, if any.

    Args:
        settings: ``WebSettings`` (read from the current configuration when
            omitted).

    Returns:
        Optional[IntegrationConfig]: The provider, or ``None`` when premium
        fetching is not configured (the default).
    """
    if settings is None:
        from codx.junior.web.settings import load_web_settings

        settings = load_web_settings()
    config = getattr(settings, "premium", None)
    if not config or not getattr(config, "enabled", True):
        return None
    return config if config.name in _PROVIDERS else None


def available_providers() -> List[str]:
    """Return the premium providers that are configured right now."""
    config = premium_config()
    return [config.name] if config else []


def fetch_with_premium(
    url: str,
    config: Optional[IntegrationConfig] = None,
    settings=None,
) -> Optional[ExtractedContent]:
    """Fetch ``url`` with the configured premium provider.

    Args:
        url: Page URL (already validated by the guard).
        config: Provider to use; defaults to the configured one.
        settings: ``WebSettings`` used to resolve ``config``.

    Returns:
        Optional[ExtractedContent]: Content, or ``None`` when premium fetching
        is not configured.

    Raises:
        ValueError: The provider answered with an error.
    """
    provider = config or premium_config(settings)
    if provider is None:
        return None

    implementation = _PROVIDERS.get(provider.name)
    if implementation is None:
        logger.warning("unknown premium fetch provider '%s'", provider.name)
        return None

    logger.info("Fetching %s with the '%s' premium provider", url, provider.name)
    return implementation(url, provider)