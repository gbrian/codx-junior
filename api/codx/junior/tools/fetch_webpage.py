import logging
from typing import Optional, Dict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import html2text

# Configure logging
logger = logging.getLogger(__name__)

def fetch_webpage(
    url: str, include_images: bool = True, max_length: Optional[int] = None, headers: Optional[Dict[str, str]] = None
) -> str:
    """Fetch a webpage and convert it to markdown format.

    Args:
        url: The URL of the webpage to fetch
        include_images: Whether to include image references in the markdown
        max_length: Maximum length of the output markdown (if None, no limit)
        headers: Optional HTTP headers for the request

    Returns:
        str: Markdown version of the webpage content

    Raises:
        ValueError: If the URL is invalid or the page can't be fetched
    """
    # Use default headers if none provided
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        logger.debug(f"Fetching URL: {url} with headers: {headers}")
        
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")
        logger.debug("HTML content parsed successfully")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        logger.debug("Script and style elements removed")

        # Convert relative URLs to absolute
        for tag in soup.find_all(["a", "img"]):
            if tag.get("href"):
                tag["href"] = urljoin(url, tag["href"])
            if tag.get("src"):
                tag["src"] = urljoin(url, tag["src"])
        logger.debug("Relative URLs converted to absolute")

        # Configure HTML to Markdown converter
        h2t = html2text.HTML2Text()
        h2t.body_width = 0  # No line wrapping
        h2t.ignore_images = not include_images
        h2t.ignore_emphasis = False
        h2t.ignore_links = False
        h2t.ignore_tables = False

        # Convert to markdown
        markdown = h2t.handle(str(soup))
        logger.debug("Converted HTML to Markdown")

        # Trim if max_length is specified
        if max_length and len(markdown) > max_length:
            markdown = markdown[:max_length] + "\n...(truncated)"
            logger.debug(f"Markdown content truncated to {max_length} characters")

        return markdown.strip()

    except requests.RequestException as e:
        logger.error(f"Request error when fetching webpage: {e}")
        raise ValueError(f"Failed to fetch webpage: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error processing webpage: {e}")
        raise ValueError(f"Error processing webpage: {str(e)}") from e
