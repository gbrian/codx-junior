"""
Minimal Docker Engine API client used by the infra services.

Why the HTTP API and not the ``docker`` CLI?
--------------------------------------------
codx-junior already shells out to ``sudo docker …`` in ``app.py`` for the log
tail endpoints, but that path is fragile (string formatting, quoting, ``sudo``,
manual parsing) and returns no structured data. The daemon exposes a stable
JSON API on the very same socket, which is what this module speaks.

The client is synchronous on purpose: the router declares ``def`` endpoints so
FastAPI runs them in its worker thread pool and the event loop is never
blocked. Timeouts are short because these calls feed UI views – a hung daemon
must surface as HTTP 503, not as a stuck request.
"""

import json
import logging
import os
from typing import Any, Dict, Iterator, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_SOCKET_PATH = "/var/run/docker.sock"

DEFAULT_ENDPOINT = (
    os.environ.get("DOCKER_HOST")
    or f"unix://{os.environ.get('CODX_JUNIOR_DOCKER_SOCKET', DEFAULT_SOCKET_PATH)}"
)

DEFAULT_TIMEOUT = float(os.environ.get("CODX_JUNIOR_DOCKER_TIMEOUT", "10"))


class DockerUnavailable(RuntimeError):
    """The daemon could not be reached (socket missing, permission denied, …)."""


class DockerAPIError(RuntimeError):
    """The daemon replied with a non-2xx status code."""

    def __init__(self, status_code: int, message: str, path: str = ""):
        self.status_code = status_code
        self.message = message
        self.path = path
        super().__init__(f"{status_code} {path}: {message}")


# ── Endpoint helpers ───────────────────────────────────────────────────────────


def _is_unix_endpoint(endpoint: str) -> bool:
    """Return True for ``unix:///path`` and bare ``/path`` endpoints."""
    return endpoint.startswith("unix://") or endpoint.startswith("/")


def _socket_path(endpoint: str) -> str:
    """Strip the ``unix://`` prefix, leaving a filesystem path."""
    return endpoint[len("unix://"):] if endpoint.startswith("unix://") else endpoint


def _base_url(endpoint: str) -> str:
    """Build the httpx base URL for an endpoint (host part is ignored for unix)."""
    if _is_unix_endpoint(endpoint):
        return "http://docker"
    if endpoint.startswith("tcp://"):
        return "http://" + endpoint[len("tcp://"):]
    return endpoint


def _transport(endpoint: str) -> httpx.BaseTransport:
    """Create the httpx transport matching the endpoint type."""
    if _is_unix_endpoint(endpoint):
        return httpx.HTTPTransport(uds=_socket_path(endpoint))
    return httpx.HTTPTransport()


def demux_frame_stream(raw: bytes) -> str:
    """
    Decode the payload of a Docker container log/attach stream.

    Non-TTY containers send 8-byte framed messages: 1 byte stream type
    (0=stdin, 1=stdout, 2=stderr), 3 zero bytes and a 4-byte big-endian size.
    TTY containers send raw bytes with no framing, so the content is returned
    untouched when the header does not look like a frame.

    Args:
        raw: Raw response body from ``/containers/{id}/logs``.

    Returns:
        The decoded text payload.
    """
    if not raw:
        return ""

    looks_framed = raw[0] in (0, 1, 2) and raw[1:4] == b"\x00\x00\x00"
    if not looks_framed:
        return raw.decode("utf-8", "replace")

    chunks: List[bytes] = []
    offset = 0
    length = len(raw)
    while offset + 8 <= length:
        size = int.from_bytes(raw[offset + 4:offset + 8], "big")
        start = offset + 8
        end = start + size
        if size < 0 or end > length:
            # Unexpected framing: fall back to the raw payload
            return raw.decode("utf-8", "replace")
        chunks.append(raw[start:end])
        offset = end

    return b"".join(chunks).decode("utf-8", "replace")


# ── Client ─────────────────────────────────────────────────────────────────────


class DockerClient:
    """Thin synchronous wrapper around the Docker Engine HTTP API."""

    def __init__(self, endpoint: Optional[str] = None, timeout: Optional[float] = None):
        self.endpoint = endpoint or DEFAULT_ENDPOINT
        self._client = httpx.Client(
            transport=_transport(self.endpoint),
            base_url=_base_url(self.endpoint),
            timeout=timeout or DEFAULT_TIMEOUT,
        )

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "DockerClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        try:
            self._client.close()
        except Exception as ex:  # pragma: no cover - best effort
            logger.debug("Error closing docker client: %s", ex)

    # -- low level ---------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Issue a request against the daemon and translate transport errors.

        Args:
            method: HTTP verb.
            path: Engine API path, e.g. ``/containers/json``.
            params: Optional query parameters.
            json_body: Optional JSON body.

        Returns:
            The successful ``httpx.Response``.

        Raises:
            DockerUnavailable: The daemon cannot be reached.
            DockerAPIError: The daemon answered with a non-2xx status.
        """
        try:
            response = self._client.request(
                method, path, params=params, json=json_body
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, FileNotFoundError,
                PermissionError, OSError) as ex:
            raise DockerUnavailable(
                f"Cannot reach the Docker daemon at {self.endpoint}: {ex}"
            ) from ex
        except httpx.HTTPError as ex:
            raise DockerUnavailable(
                f"Docker request failed ({method} {path}): {ex}"
            ) from ex

        if response.status_code >= 400:
            raise DockerAPIError(
                response.status_code, self._error_message(response), path
            )
        return response

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        """Extract the daemon's ``message`` field, falling back to the body."""
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("message"):
                return str(payload["message"])
        except ValueError:
            pass
        text = (response.text or "").strip()
        return text[:500] or f"HTTP {response.status_code}"

    # -- convenience -------------------------------------------------------

    def get_json(self, path: str, params: Optional[Dict[str, str]] = None) -> Any:
        """Perform a GET and decode the JSON response."""
        response = self.request("GET", path, params=params)
        if not response.content:
            return {}
        return response.json()

    def get_bytes(self, path: str, params: Optional[Dict[str, str]] = None) -> bytes:
        """Perform a GET and return the raw body (log streams, NDJSON)."""
        return self.request("GET", path, params=params).content

    def post(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Perform a POST and decode the JSON response (may be empty)."""
        response = self.request("POST", path, params=params, json_body=json_body)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def delete(
        self, path: str, params: Optional[Dict[str, str]] = None
    ) -> Any:
        """Perform a DELETE and decode the JSON response (may be empty)."""
        response = self.request("DELETE", path, params=params)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def iter_json_lines(
        self, path: str, params: Optional[Dict[str, str]] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Yield decoded objects from a newline-delimited JSON endpoint.

        Used for ``/events``, which is only requested for a closed time window
        so the body is finite and can be read in one go.
        """
        raw = self.get_bytes(path, params=params)
        for line in raw.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                logger.debug("Skipping non-JSON docker event line: %s", line[:120])

# Made with ❤️ by codx-junior