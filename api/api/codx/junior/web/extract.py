"""Reader-mode extraction: HTML -> markdown for the model.

Extraction is a chain and every link is optional, so a missing dependency or an
unsupported page degrades instead of failing:

1. ``trafilatura`` — best precision: removes navigation, footers, comments and
   related links, and also returns title / author / date metadata;
2. ``readability-lxml`` — used when trafilatura is not installed or finds
   nothing usable;
3. a conservative BeautifulSoup + html2text pass that only strips the obvious
   boilerplate.

The first extractor whose result looks like real content wins; otherwise the
longest candidate is returned. Nothing here performs HTTP requests.

Made with ❤️ by codx-junior
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

#: Below this many characters of text a page is considered a skeleton (a SPA
#: shell, a consent wall or a bot challenge) and rendering may be attempted.
MIN_CONTENT_CHARS = 300

#: Documents larger than this are truncated before parsing: a 50 MB page brings
#: no extra text and only burns CPU.
MAX_HTML_CHARS = 5_000_000

#: Tags that never carry article text.
BOILERPLATE_TAGS = (
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "canvas",
    "iframe",
    "form",
    "nav",
    "footer",
    "aside",
)

#: ARIA roles used for page chrome.
BOILERPLATE_ROLES = (
    "navigation",
    "banner",
    "contentinfo",
    "complementary",
    "search",
    "dialog",
)

#: Class/id naming conventions of page chrome (conservative: whole words only).
BOILERPLATE_HINT = re.compile(
    r"(?:^|[-_\s])("
    r"nav|navbar|navigation|menu|sidebar|footer|masthead|cookie|consent|banner|"
    r"advert|advertisement|ads|promo|newsletter|subscribe|related|recommend|"
    r"share|social|comments?|breadcrumbs?|pagination|paywall"
    r")(?:[-_\s]|$)",
    re.IGNORECASE,
)

#: Text that means "the page did not really answer".
BOT_WALL_HINTS = (
    "enable javascript",
    "requires javascript",
    "javascript is disabled",
    "please turn on javascript",
    "checking your browser",
    "just a moment",
    "cf-challenge",
    "captcha",
    "are you a robot",
    "access denied",
)


@dataclass
class ExtractedContent:
    """Readable content extracted from one HTML document.

    Attributes:
        url: Page URL used to resolve relative links.
        title: Document title, when the extractor found one.
        markdown: Reader-mode markdown (the model facing representation).
        text: Plain text used for quality checks and empty-content detection.
        extractor: Name of the extractor that produced the content.
        site_name: Site name reported in the page metadata.
        published: Publication date reported in the page metadata.
        truncated: True when the document was cut by :data:`MAX_HTML_CHARS`.
    """

    url: str = ""
    title: str = ""
    markdown: str = ""
    text: str = ""
    extractor: str = ""
    site_name: str = ""
    published: str = ""
    truncated: bool = False


def text_from_markdown(markdown: str) -> str:
    """Return the plain text of a markdown document.

    Args:
        markdown: Markdown source.

    Returns:
        str: Text with image/link syntax and emphasis markers removed.

    Example:
        >>> text_from_markdown("See [docs](https://x) ![i](a.png) **now**")
        'See docs now'
    """
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", markdown or "")
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_>#]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_markdown(markdown: str) -> str:
    """Normalize line endings, trailing spaces and repeated blank lines."""
    text = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def truncate_markdown(markdown: str, max_chars: Optional[int]) -> tuple:
    """Cap a markdown document at ``max_chars`` characters.

    Args:
        markdown: Markdown source.
        max_chars: Maximum length, ``None`` or ``0`` for no limit.

    Returns:
        tuple: ``(markdown, truncated)``.
    """
    text = markdown or ""
    if not max_chars or max_chars <= 0 or len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def is_thin(content: Optional[ExtractedContent], html_len: int = 0) -> bool:
    """Return True when a page yielded too little text to be usable.

    Args:
        content: Extracted content (``None`` means nothing could be extracted).
        html_len: Length of the source HTML, used to detect a huge shell with
            almost no text (client-side rendering).

    Returns:
        bool: True when the page should be considered a skeleton.
    """
    text = (content.text or "").strip() if content else ""
    if len(text) < MIN_CONTENT_CHARS:
        return True
    if html_len > 20_000 and len(text) < html_len // 200:
        return True
    return False


def bot_wall_reason(html: str) -> Optional[str]:
    """Detect the usual "you are not a browser" interstitials.

    Args:
        html: Raw HTML of the answered page.

    Returns:
        Optional[str]: Human readable reason, or ``None`` when the page looks
        like real content.
    """
    head = (html or "")[:20_000].lower()
    for hint in BOT_WALL_HINTS:
        if hint in head:
            return f"the page looks like a bot/consent wall ('{hint}')"
    return None


def _absolutize(soup: BeautifulSoup, base_url: str) -> None:
    """Turn relative ``href``/``src`` values into absolute URLs."""
    if not base_url:
        return
    from urllib.parse import urljoin

    for tag in soup.find_all(["a", "img"]):
        href = tag.get("href")
        if href:
            tag["href"] = urljoin(base_url, href)
        src = tag.get("src")
        if src:
            tag["src"] = urljoin(base_url, src)


def _decompose(element) -> None:
    """Remove a BeautifulSoup element, ignoring already detached nodes."""
    try:
        element.decompose()
    except Exception:  # pragma: no cover - defensive
        pass


def strip_boilerplate(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove scripts, styles and the usual page chrome from a document."""
    for tag in soup.find_all(BOILERPLATE_TAGS):
        _decompose(tag)

    for role in BOILERPLATE_ROLES:
        for element in soup.find_all(attrs={"role": role}):
            _decompose(element)

    for element in list(soup.find_all(True)):
        if element.name in ("html", "body", "article", "main"):
            continue
        classes = " ".join(element.get("class") or [])
        marker = f"{classes} {element.get('id') or ''}".strip()
        if marker and BOILERPLATE_HINT.search(marker):
            _decompose(element)

    return soup


def html_to_markdown(html: str, base_url: str = "", include_images: bool = True) -> str:
    """Convert an HTML fragment to markdown with html2text."""
    import html2text

    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = not include_images
    converter.ignore_links = False
    converter.ignore_emphasis = False
    converter.ignore_tables = False
    return clean_markdown(converter.handle(html or ""))


def _title_from_html(html: str) -> str:
    """Read ``<title>`` from a raw document (best effort)."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _extract_trafilatura(html: str, url: str, include_images: bool) -> Optional[ExtractedContent]:
    """Extract with trafilatura (reader mode + metadata)."""
    import trafilatura

    markdown = trafilatura.extract(
        html,
        url=url or None,
        output_format="markdown",
        include_images=include_images,
        include_links=True,
        include_tables=True,
        include_comments=False,
        favor_recall=True,
    )
    if not markdown:
        return None

    title = published = site_name = ""
    try:
        metadata = trafilatura.extract_metadata(html, default_url=url or None)
        if metadata:
            title = getattr(metadata, "title", "") or ""
            published = getattr(metadata, "date", "") or ""
            site_name = getattr(metadata, "sitename", "") or ""
    except Exception as ex:  # pragma: no cover - metadata is optional
        logger.debug("trafilatura metadata unavailable for %s: %s", url, ex)

    cleaned = clean_markdown(markdown)
    return ExtractedContent(
        url=url,
        title=title,
        markdown=cleaned,
        text=text_from_markdown(cleaned),
        extractor="trafilatura",
        site_name=site_name,
        published=published,
    )


def _extract_readability(html: str, url: str, include_images: bool) -> Optional[ExtractedContent]:
    """Extract with readability-lxml (Mozilla's reader algorithm)."""
    from readability import Document

    document = Document(html)
    summary = document.summary(html_partial=True)
    if not summary:
        return None

    title = ""
    try:
        title = document.short_title() or document.title() or ""
    except Exception:  # pragma: no cover - defensive
        title = ""

    markdown = html_to_markdown(summary, base_url=url, include_images=include_images)
    if not markdown:
        return None
    return ExtractedContent(
        url=url,
        title=title or "",
        markdown=markdown,
        text=text_from_markdown(markdown),
        extractor="readability",
    )


def _extract_soup(html: str, url: str, include_images: bool) -> Optional[ExtractedContent]:
    """Last resort: strip the obvious chrome and convert the rest."""
    soup = BeautifulSoup((html or "")[:MAX_HTML_CHARS], "html.parser")
    title = _title_from_html(html)
    strip_boilerplate(soup)
    _absolutize(soup, url)
    body = soup.body or soup

    markdown = html_to_markdown(str(body), base_url=url, include_images=include_images)
    if not markdown:
        return None
    return ExtractedContent(
        url=url,
        title=title,
        markdown=markdown,
        text=text_from_markdown(markdown),
        extractor="html2text",
        truncated=len(html or "") > MAX_HTML_CHARS,
    )


#: Extractor chain, most precise first.
EXTRACTORS = (_extract_trafilatura, _extract_readability, _extract_soup)


def extract_content(html: str, url: str = "", include_images: bool = True) -> ExtractedContent:
    """Extract readable content from an HTML document.

    Args:
        html: Raw HTML (already fetched and bounded by
            :func:`codx.junior.web.guard.safe_get`).
        url: Page URL, used to resolve relative links and as metadata default.
        include_images: Keep image references in the markdown.

    Returns:
        ExtractedContent: Always an object; ``markdown``/``text`` are empty when
        nothing could be extracted (callers decide whether to render the page).

    Example:
        >>> extract_content("<html><body><p>hi</p></body></html>").extractor
        'html2text'
    """
    if not html or not html.strip():
        return ExtractedContent(url=url, extractor="empty")

    candidates: List[ExtractedContent] = []
    for extractor in EXTRACTORS:
        try:
            content = extractor(html, url, include_images)
        except Exception as ex:
            logger.debug("%s failed for %s: %s", extractor.__name__, url, ex)
            continue
        if content and (content.markdown or content.text):
            if len(content.text) >= MIN_CONTENT_CHARS:
                return content
            candidates.append(content)

    if not candidates:
        logger.info("No readable content extracted from %s", url or "(no url)")
        return ExtractedContent(url=url, extractor="none")

    best = max(candidates, key=lambda item: len(item.text or ""))
    if not best.title:
        best.title = _title_from_html(html)
    return best