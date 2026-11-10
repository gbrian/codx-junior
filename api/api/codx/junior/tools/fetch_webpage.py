"""``fetch_webpage`` tool: a URL in, markdown out.

The pipeline lives in :mod:`codx.junior.web.fetch` (SSRF/size/deadline guards,
reader-mode extraction, rendering escalation and the optional premium
providers). This module only keeps the tool contract: a markdown string with a
short provenance footer, so the model can cite where the text came from.

Made with ❤️ by codx-junior
"""

import logging
from typing import Dict, Optional, Union

from codx.junior.web.fetch import fetch_page

logger = logging.getLogger(__name__)

#: Maximum number of pipeline remarks appended to the footer.
MAX_NOTES = 3


def fetch_webpage(
    url: str,
    include_images: bool = True,
    max_length: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    render: Union[bool, str, None] = None,
    premium: Union[bool, str, None] = None,
) -> str:
    """Fetch a webpage and convert it to markdown.

    Args:
        url: The URL of the webpage to fetch (``http``/``https`` only; private
            and loopback addresses are refused).
        include_images: Whether to include image references in the markdown.
        max_length: Maximum length of the output markdown. ``None`` uses the
            configured output cap (``CODX_WEB_FETCH_MAX_OUTPUT_CHARS``).
        headers: Optional HTTP headers for the static request.
        render: ``auto`` (default: render only pages that need JavaScript),
            ``always`` or ``never``.
        premium: ``off`` (default), ``auto`` (only when everything else failed)
            or ``on`` (use the configured managed provider first). Requires a
            configured Jina Reader / Firecrawl integration.

    Returns:
        str: Markdown version of the page content, followed by a footer with the
        final URL and how it was obtained.

    Raises:
        ValueError: If the URL is invalid, unsafe, or the page can't be fetched
            or read.
    """
    page = fetch_page(
        url,
        include_images=bool(include_images),
        max_chars=max_length,
        render=render,
        premium=premium,
        headers=headers,
    )

    markdown = (page.markdown or "").strip()
    if not markdown:
        raise ValueError(f"No readable content could be extracted from {page.final_url or url}")

    details = [page.extractor or "unknown", f"{len(markdown)} chars"]
    if page.rendered:
        details.append("js-rendered")
    if page.premium:
        details.append("premium fetch")
    if page.truncated:
        details.append("truncated")

    source = page.final_url or page.url
    lines = ["", "---", f"Source: {source} ({', '.join(details)})"]
    for note in page.notes[:MAX_NOTES]:
        lines.append(f"Note: {note}")

    logger.debug("fetch_webpage %s -> %s", url, page.summary())
    return markdown + "\n".join(lines)