"""SSRF, size and deadline guards for model driven web access.

``fetch_webpage`` is callable by an LLM, so the URL it receives is untrusted:
without explicit checks a prompt (or a poisoned page) can make the backend read
``http://169.254.169.254/latest/meta-data``, the Docker socket through a local
HTTP API or any service of the internal network.  This module is the only
place where outbound HTTP for the web tools is validated:

* scheme allow-list (``http`` / ``https`` only);
* DNS resolution plus private / reserved address rejection, re-checked on
  every redirect hop (a public URL must not bounce to ``127.0.0.1``);
* bounded body size and a wall-clock deadline;
* a small, honest set of request headers.

Made with ❤️ by codx-junior
"""

import ipaddress
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

logger = logging.getLogger(__name__)

#: Schemes accepted for outbound requests.
ALLOWED_SCHEMES = ("http", "https")

#: Maximum number of redirect hops followed before giving up.
MAX_REDIRECTS = 5

#: Size of the chunks read from the socket.
CHUNK_SIZE = 64 * 1024

#: Default body limit (3 MB is far more than any readable article).
DEFAULT_MAX_BYTES = 3 * 1024 * 1024

#: Default wall-clock budget for the whole request, redirects included.
DEFAULT_TIMEOUT_SECONDS = 15.0

#: Hostnames that never resolve to a legitimate public site.
BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "metadata",
    "metadata.google.internal",
    "instance-data",
})

#: Suffixes that only exist inside a private network.
BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa")

#: Reserved IPv4 ranges: private, loopback, link-local (cloud metadata),
#: carrier grade NAT, documentation and multicast space.
_BLOCKED_V4 = tuple(
    ipaddress.ip_network(network)
    for network in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
    )
)

#: Reserved IPv6 ranges: unspecified, loopback, ULA, link-local, multicast,
#: documentation and NAT64 space.
_BLOCKED_V6 = tuple(
    ipaddress.ip_network(network)
    for network in (
        "::/128",
        "::1/128",
        "64:ff9b::/96",
        "100::/64",
        "2001:db8::/32",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
    )
)

#: Headers sent when the caller does not provide its own.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


class UnsafeUrlError(ValueError):
    """Raised when a URL is not acceptable for an outbound request."""


class FetchError(ValueError):
    """Raised when the remote server answers with an error status."""


@dataclass
class FetchedPage:
    """Result of a guarded HTTP request.

    Attributes:
        url: URL originally requested.
        final_url: URL after following redirects.
        status: HTTP status code.
        content_type: ``Content-Type`` header (may be empty).
        text: Decoded body, already bounded by ``max_bytes``.
        bytes_read: Number of body bytes actually read.
        truncated: True when the body was cut by the size cap or the deadline.
        redirects: URLs followed, in order.
    """

    url: str
    final_url: str
    status: int
    content_type: str = ""
    text: str = ""
    bytes_read: int = 0
    truncated: bool = False
    redirects: List[str] = field(default_factory=list)


def is_public_ip(value: str) -> bool:
    """Return True when ``value`` is a routable, non reserved IP address.

    Args:
        value: IPv4 or IPv6 address as text.

    Returns:
        bool: False for private, loopback, link-local, multicast, reserved and
        unspecified addresses (IPv4-mapped IPv6 included).

    Example:
        >>> is_public_ip("169.254.169.254")
        False
        >>> is_public_ip("93.184.216.34")
        True
    """
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False

    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return False

    blocked = _BLOCKED_V4 if isinstance(address, ipaddress.IPv4Address) else _BLOCKED_V6
    return not any(address.version == net.version and address in net for net in blocked)


def resolve_host(host: str, port: Optional[int] = None) -> List[str]:
    """Resolve ``host`` to every address the name points to.

    Args:
        host: Hostname or literal IP.
        port: Optional port used for the lookup.

    Returns:
        List[str]: Resolved addresses (a literal IP is returned as is).

    Raises:
        UnsafeUrlError: If the name cannot be resolved.
    """
    try:
        ipaddress.ip_address(host)
        return [host]
    except ValueError:
        pass

    try:
        info = socket.getaddrinfo(host, port or 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as ex:
        raise UnsafeUrlError(f"Could not resolve host '{host}': {ex}") from ex

    addresses = []
    for entry in info:
        address = entry[4][0]
        if address not in addresses:
            addresses.append(address)
    return addresses


def _assert_public_host(host: str, port: Optional[int]) -> None:
    """Raise :class:`UnsafeUrlError` unless ``host`` is a public destination."""
    name = (host or "").strip().lower().rstrip(".")
    if not name:
        raise UnsafeUrlError("The URL has no host")

    if name in BLOCKED_HOSTNAMES or name.endswith(BLOCKED_HOST_SUFFIXES):
        raise UnsafeUrlError(f"Requests to '{name}' are not allowed")

    for address in resolve_host(name, port):
        if not is_public_ip(address):
            raise UnsafeUrlError(
                f"Refusing to fetch '{name}': it resolves to the non public address {address}"
            )


def validate_url(url: str, allow_private: bool = False) -> str:
    """Validate and normalize a URL before an outbound request.

    Args:
        url: Candidate URL.
        allow_private: Accept private / loopback destinations (self hosted
            development only, controlled by the deployment).

    Returns:
        str: Normalized URL without fragment.

    Raises:
        UnsafeUrlError: Invalid scheme, missing host or non public target.

    Example:
        >>> validate_url("https://example.com/a#x")
        'https://example.com/a'
    """
    candidate = (url or "").strip()
    if not candidate:
        raise UnsafeUrlError("The URL is empty")

    parts = urlsplit(candidate)
    scheme = (parts.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(
            f"Unsupported URL scheme '{parts.scheme or '(none)'}': only http and https are allowed"
        )

    host = parts.hostname
    if not host:
        raise UnsafeUrlError(f"The URL has no host: {candidate}")

    try:
        port = parts.port
    except ValueError as ex:
        raise UnsafeUrlError(f"Invalid port in URL '{candidate}': {ex}") from ex

    if not allow_private:
        _assert_public_host(host, port)

    path = parts.path or "/"
    return urlunsplit((scheme, parts.netloc, path, parts.query, ""))


def _decode(raw: bytes, encoding: Optional[str]) -> str:
    """Decode a body with the declared encoding and sane fallbacks."""
    for candidate in (encoding, "utf-8"):
        if not candidate:
            continue
        try:
            return raw.decode(candidate).lstrip("\ufeff")
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def _read_body(response: requests.Response, max_bytes: int, deadline: float) -> tuple:
    """Read at most ``max_bytes`` from a streamed response.

    Returns:
        tuple: ``(body, truncated)``.
    """
    chunks: List[bytes] = []
    total = 0
    truncated = False

    for chunk in response.iter_content(CHUNK_SIZE):
        if not chunk:
            continue
        remaining = max_bytes - total
        if remaining <= 0:
            truncated = True
            break
        if len(chunk) > remaining:
            chunks.append(chunk[:remaining])
            total += remaining
            truncated = True
            break
        chunks.append(chunk)
        total += len(chunk)
        if time.monotonic() > deadline:
            truncated = True
            break

    return b"".join(chunks), truncated


def safe_get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    allow_private: bool = False,
    session: Optional[requests.Session] = None,
) -> FetchedPage:
    """Perform a guarded GET request.

    Redirects are followed manually so each hop is validated again, the body is
    read up to ``max_bytes`` and the whole call is bounded by ``timeout``.

    Args:
        url: Target URL (validated by :func:`validate_url`).
        headers: Extra headers merged over :data:`DEFAULT_HEADERS`.
        timeout: Wall-clock budget in seconds for the whole request.
        max_bytes: Maximum number of body bytes read.
        allow_private: Allow private / loopback destinations.
        session: Optional ``requests.Session`` (one is created and closed if
            omitted).

    Returns:
        FetchedPage: Decoded, bounded response.

    Raises:
        UnsafeUrlError: Unsafe or unresolvable URL, or too many redirects.
        FetchError: The server answered with a 4xx/5xx status.

    Example:
        >>> page = safe_get("https://example.com")  # doctest: +SKIP
        >>> page.status
        200
    """
    own_session = session is None
    client = session or requests.Session()
    deadline = time.monotonic() + max(float(timeout or 0.1), 0.1)

    request_headers = dict(DEFAULT_HEADERS)
    request_headers.update(headers or {})

    current = validate_url(url, allow_private=allow_private)
    redirects: List[str] = []

    try:
        for _ in range(MAX_REDIRECTS + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise UnsafeUrlError(f"Timed out after {timeout}s fetching {current}")

            response = client.get(
                current,
                headers=request_headers,
                stream=True,
                allow_redirects=False,
                timeout=(min(remaining, 10.0), remaining),
            )
            try:
                if response.is_redirect:
                    location = response.headers.get("Location")
                    if not location:
                        break
                    current = validate_url(urljoin(current, location), allow_private=allow_private)
                    redirects.append(current)
                    continue

                body, truncated = _read_body(response, max_bytes, deadline)
                status = response.status_code
                if status >= 400:
                    raise FetchError(f"HTTP {status} for {current}")

                return FetchedPage(
                    url=url,
                    final_url=current,
                    status=status,
                    content_type=response.headers.get("Content-Type", "") or "",
                    text=_decode(body, response.encoding),
                    bytes_read=len(body),
                    truncated=truncated,
                    redirects=redirects,
                )
            finally:
                response.close()

        raise UnsafeUrlError(f"Too many redirects (>{MAX_REDIRECTS}) for {url}")
    finally:
        if own_session:
            client.close()


def is_html(page: FetchedPage) -> bool:
    """Return True when the fetched body looks like an HTML document."""
    content_type = (page.content_type or "").lower()
    if "html" in content_type or "xml" in content_type:
        return True
    if content_type and "text/plain" not in content_type:
        return False

    head = (page.text or "").lstrip()[:200].lower()
    return head.startswith("<!doctype html") or head.startswith("<html")


def is_pdf(page: FetchedPage) -> bool:
    """Return True when the body is a PDF document."""
    return "application/pdf" in (page.content_type or "").lower()
