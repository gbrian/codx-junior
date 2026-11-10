"""``fetch_webpage`` pipeline: guarded fetch, extraction, escalation.

The order is deliberate — every step is more expensive and more invasive than
the previous one:

1. **premium provider** (only when explicitly requested);
2. **static fetch + reader-mode extraction** (free, no JavaScript);
3. **rendering** when the page is a skeleton (lite engine, then Chromium);
4. **premium provider** as an automatic fallback (``premium="auto"``).

Steps 1 and 4 never run by default: they send the URL to a third party.

Made with ❤️ by codx-junior
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from codx.junior.web.browser_fetch import fetch_rendered
from codx.junior.web.extract import (
    ExtractedContent,
    bot_wall_reason,
    extract_content,
    is_thin,
    text_from_markdown,
    truncate_markdown,
)
from codx.junior.web.guard import (
    FetchError,
    is_html,
    is_pdf,
    safe_get,
    validate_url,
)
from codx.junior.web.premium import fetch_with_premium
from codx.junior.web.settings import WebSettings, load_web_settings

logger = logging.getLogger(__name__)

#: How the rendering escalation is decided.
RENDER_MODES = ("auto", "always", "never")

#: How the premium providers are used.
PREMIUM_MODES = ("off", "on", "auto")

_TRUE_VALUES = ("1", "true", "yes", "on", "always", "force")
_FALSE_VALUES = ("", "0", "false", "no", "off", "never", "none", "disabled")


@dataclass
class WebPageContent:
    """A fetched page, ready to be handed to the model.

    Attributes:
        url: URL requested by the caller.
        final_url: URL of the document after redirects.
        status: HTTP status of the last answer.
        title: Document title.
        markdown: Reader-mode markdown, capped by ``max_chars``.
        text: Plain text of the markdown (quality checks, search snippets).
        extractor: Pipeline stage that produced the content
            (``trafilatura``, ``chromium+trafilatura``, ``jina-reader``...).
        rendered: True when a browser engine had to render the page.
        premium: True when a managed provider fetched the page.
        truncated: True when the output was cut.
        notes: Human readable remarks (bot wall, failed escalation...).
    """

    url: str
    final_url: str = ""
    status: int = 0
    title: str = ""
    markdown: str = ""
    text: str = ""
    extractor: str = ""
    rendered: bool = False
    premium: bool = False
    truncated: bool = False
    notes: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """True when nothing usable was extracted."""
        return not (self.markdown or "").strip()

    def summary(self) -> str:
        """One line provenance string, e.g. ``trafilatura, js-rendered``."""
        details = [self.extractor or "unknown"]
        if self.rendered:
            details.append("js-rendered")
        if self.premium:
            details.append("premium fetch")
        if self.truncated:
            details.append("truncated")
        return ", ".join(details)


def _as_text_mode(value, modes: tuple, default: str) -> str:
    """Normalize a mode that may arrive as a boolean, a string or ``None``."""
    if value is None:
        return default
    if isinstance(value, bool):
        return modes[-1] if value else modes[0]
    text = str(value).strip().lower()
    if text in modes:
        return text
    if text in _TRUE_VALUES:
        return modes[-1]
    if text in _FALSE_VALUES:
        return modes[0]
    return default


def normalize_render_mode(value) -> str:
    """Normalize the ``render`` argument to ``auto``, ``always`` or ``never``."""
    return _as_text_mode(value, ("never", "auto", "always"), "auto")


def normalize_premium_mode(value) -> str:
    """Normalize the ``premium`` argument to ``off``, ``auto`` or ``on``."""
    return _as_text_mode(value, ("off", "auto", "on"), "off")


def _premium_content(
    url: str,
    settings: WebSettings,
    notes: List[str],
) -> Optional[ExtractedContent]:
    """Fetch ``url`` with the premium provider, recording failures in notes."""
    try:
        content = fetch_with_premium(url, settings=settings)
    except Exception as ex:
        logger.warning("premium fetch failed for %s: %s", url, ex)
        notes.append(f"premium fetch: {ex}")
        return None

    if content is None:
        return None
    if not (content.markdown or "").strip():
        notes.append("premium fetch returned no content")
        return None
    return content


def _finalize(
    target: str,
    content: ExtractedContent,
    final_url: str,
    status: int,
    max_chars: Optional[int],
    settings: WebSettings,
    notes: List[str],
    rendered: bool = False,
    premium: bool = False,
) -> WebPageContent:
    """Build the :class:`WebPageContent` applying the output cap."""
    limit = max_chars if max_chars and max_chars > 0 else settings.max_output_chars
    markdown, truncated = truncate_markdown(content.markdown or content.text or "", limit)
    return WebPageContent(
        url=target,
        final_url=final_url or content.url or target,
        status=status,
        title=content.title or "",
        markdown=markdown,
        text=content.text or text_from_markdown(markdown),
        extractor=content.extractor or "",
        rendered=rendered,
        premium=premium,
        truncated=bool(truncated or content.truncated),
        notes=list(notes),
    )


def _static_content(fetched, include_images: bool) -> ExtractedContent:
    """Extract content from a bounded HTTP answer."""
    if is_html(fetched):
        return extract_content(
            fetched.text, url=fetched.final_url, include_images=include_images
        )

    raw = fetched.text or ""
    return ExtractedContent(
        url=fetched.final_url,
        markdown=raw,
        text=text_from_markdown(raw),
        extractor="raw",
    )


def fetch_page(
    url: str,
    include_images: bool = True,
    max_chars: Optional[int] = None,
    render="auto",
    premium=False,
    headers: Optional[Dict[str, str]] = None,
    allow_private: Optional[bool] = None,
    settings: Optional[WebSettings] = None,
) -> WebPageContent:
    """Fetch a page and return it as markdown for the model.

    Args:
        url: Target URL (``http``/``https``, validated by the guard).
        include_images: Keep image references in the markdown.
        max_chars: Output cap; defaults to ``WebSettings.max_output_chars``.
        render: ``auto`` (render only skeleton pages), ``always`` or ``never``.
        premium: ``off`` (default), ``auto`` (only after everything failed) or
            ``on`` (always use the managed provider).
        headers: Extra HTTP headers for the static request.
        allow_private: Override the SSRF policy (self hosted deployments).
        settings: ``WebSettings`` (read from the current configuration when
            omitted).

    Returns:
        WebPageContent: Markdown plus provenance.

    Raises:
        UnsafeUrlError: The URL is not acceptable (scheme, host, private target).
        FetchError: The server answered with an error and rendering did not help.
        ValueError: The target is not a text document (e.g. a PDF).

    Example:
        >>> page = fetch_page("https://example.com")  # doctest: +SKIP
        >>> page.extractor
        'trafilatura'
    """
    config = settings or load_web_settings()
    render_mode = normalize_render_mode(render)
    premium_mode = normalize_premium_mode(premium)
    allow = config.allow_private_hosts if allow_private is None else bool(allow_private)

    target = validate_url(url, allow_private=allow)
    notes: List[str] = []

    # 1. premium first, only when explicitly requested
    if premium_mode == "on":
        content = _premium_content(target, config, notes)
        if content is not None:
            return _finalize(
                target, content, content.url, 200, max_chars, config, notes, premium=True
            )

    # 2. static fetch + extraction
    fetched = None
    fetch_error: Optional[Exception] = None
    try:
        fetched = safe_get(
            target,
            headers=headers,
            timeout=config.timeout,
            max_bytes=config.max_bytes,
            allow_private=allow,
        )
    except FetchError as ex:
        fetch_error = ex
        notes.append(str(ex))

    content: Optional[ExtractedContent] = None
    html_len = 0
    final_url = target
    status = 0

    if fetched is not None:
        final_url = fetched.final_url or target
        status = fetched.status
        html_len = len(fetched.text or "")
        if is_pdf(fetched):
            raise ValueError(
                f"{final_url} is a PDF; download it and convert it with the document tools"
            )
        content = _static_content(fetched, include_images)
        if fetched.truncated:
            notes.append(f"the answer was cut at {config.max_bytes} bytes")
        wall = bot_wall_reason(fetched.text)
        if wall:
            notes.append(wall)

    # 3. rendering escalation
    thin = content is None or is_thin(content, html_len)
    should_render = render_mode == "always" or (
        render_mode == "auto" and (thin or fetch_error is not None)
    )
    rendered = False
    if should_render and config.browser_escalation:
        rendered_content = fetch_rendered(
            target, settings=config, include_images=include_images, notes=notes
        )
        if rendered_content is not None and (rendered_content.markdown or rendered_content.text):
            content = rendered_content
            rendered = True
            thin = is_thin(content, html_len)
            fetch_error = None

    if content is None:
        raise FetchError(str(fetch_error) if fetch_error else f"No content from {target}")

    # 4. premium as the last resort
    premium_used = False
    if premium_mode == "auto" and thin:
        premium_content = _premium_content(target, config, notes)
        if premium_content is not None:
            content = premium_content
            premium_used = True

    if thin:
        notes.append("the extracted content is very short: the page may need JavaScript or a login")

    return _finalize(
        target,
        content,
        final_url,
        status,
        max_chars,
        config,
        notes,
        rendered=rendered,
        premium=premium_used,
    )