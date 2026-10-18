"""
Shared contract of the cloud provisioning engine.

Every provider exposes
----------------------
* a **catalog** (`catalog()`) the wizard renders itself from: credential
  fields, regions, sizes and images. Adding a provider therefore needs no
  front-end change.
* `validate()` – checks transient credentials without storing them.
* `create_server()` – one blocking call that returns the instance id and its
  public IP.
* `destroy_server()` – releases the instance.

Errors are `CloudProviderError`: a missing/invalid credential is reported with
`status_code = 422` (the caller must fix the form), a remote failure with `502`.
Nothing is ever logged or cached from `credentials`.

Example
-------
```python
from codx.junior.infra.cloud import get_provider

provider = get_provider("hetzner")
print([field.key for field in provider.catalog().credentials])  # ['token']
print(provider.validate({"token": "…"}))                      # CloudValidateResult(ok=True, …)
```
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx

from codx.junior.infra.models import (
    CloudCredentialField,
    CloudOption,
    CloudProvider as CloudProviderModel,
    CloudServerRequest,
    CloudValidateResult,
)

logger = logging.getLogger(__name__)

DEFAULT_HTTP_TIMEOUT = float(60)
DEFAULT_SSH_USER = "root"

# (level, message) -> written to the provisioning journal
LogCallback = Callable[[str, str], None]


class CloudProviderError(RuntimeError):
    """A provisioning step failed.

    Attributes:
        status_code: HTTP status the router should answer with. `422` means the
            request/credentials are wrong, `502` a remote failure.
    """

    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class CloudProviderNotFound(CloudProviderError):
    """The requested provider id is not registered."""

    def __init__(self, provider: str):
        super().__init__(f"Unknown cloud provider '{provider}'", 404)
        self.provider = provider


@dataclass
class ProvisionedServer:
    """Result of a successful `create_server()` call."""

    server_id: str
    ip: str = ""
    hostname: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


# ── HTTP helpers ──────────────────────────────────────────────────────────────


def http_client(timeout: float = DEFAULT_HTTP_TIMEOUT) -> httpx.Client:
    """Create an httpx client with sane defaults for provider REST APIs."""
    return httpx.Client(timeout=timeout, follow_redirects=True)


def error_text(response: httpx.Response) -> str:
    """Extract a short, human readable error out of a provider response."""
    try:
        payload = response.json()
    except ValueError:
        return (response.text or "").strip()[:400] or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])[:400]
        if isinstance(error, str):
            return error[:400]
        for key in ("message", "Message", "detail", "code"):
            if payload.get(key):
                return str(payload[key])[:400]
    return str(payload)[:400]


def request_json(
    client: httpx.Client,
    method: str,
    url: str,
    action: str,
    **kwargs: Any,
) -> Any:
    """
    Perform a provider call and decode the JSON answer.

    Args:
        client: The httpx client to use.
        method: HTTP verb.
        url: Absolute URL.
        action: Human readable action, used in error messages.
        **kwargs: Forwarded to ``httpx.Client.request``.

    Returns:
        The decoded payload (``{}`` for empty bodies).

    Raises:
        CloudProviderError: Transport error (`502`) or non-2xx answer
            (`422` for 400/401/403, `502` otherwise).
    """
    try:
        response = client.request(method, url, **kwargs)
    except httpx.HTTPError as ex:
        raise CloudProviderError(f"{action} failed: {ex}", 502) from ex

    if response.status_code >= 400:
        detail = error_text(response)
        status = 422 if response.status_code in (400, 401, 403) else 502
        raise CloudProviderError(f"{action} failed: {detail}", status)

    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        return {}


# ── Provider contract ─────────────────────────────────────────────────────────


class CloudProvider:
    """Base class of a provisioning provider (see module docstring)."""

    id: str = ""
    name: str = ""
    icon: str = "fa-cloud"
    summary: str = ""
    ssh_user: str = DEFAULT_SSH_USER
    uploads_key: bool = True

    regions: List[Dict[str, str]] = []
    sizes: List[Dict[str, str]] = []
    images: List[Dict[str, str]] = []
    credentials: List[Dict[str, Any]] = []

    default_region: str = ""
    default_size: str = ""
    default_image: str = ""

    # -- catalog -----------------------------------------------------------

    def catalog(self) -> CloudProviderModel:
        """Return everything the wizard needs to render this provider."""
        return CloudProviderModel(
            id=self.id,
            name=self.name,
            icon=self.icon,
            summary=self.summary,
            credentials=[CloudCredentialField(**item) for item in self.credentials],
            regions=[CloudOption(**item) for item in self.regions],
            sizes=[CloudOption(**item) for item in self.sizes],
            images=[CloudOption(**item) for item in self.images],
            default_region=self.default_region or self._first("regions"),
            default_size=self.default_size or self._first("sizes"),
            default_image=self.default_image or self._first("images"),
            ssh_user=self.ssh_user,
            uploads_key=self.uploads_key,
        )

    def _first(self, attribute: str) -> str:
        """First value of a catalog list (used as default)."""
        values = getattr(self, attribute) or []
        return str(values[0].get("value") or "") if values else ""

    # -- operations --------------------------------------------------------

    def validate(
        self, credentials: Dict[str, str], region: Optional[str] = None
    ) -> CloudValidateResult:
        """Check transient credentials. Never stores or logs them."""
        raise NotImplementedError

    def create_server(
        self,
        request: CloudServerRequest,
        public_key: str,
        log: Optional[LogCallback] = None,
    ) -> ProvisionedServer:
        """Create one instance and return its id + public IP."""
        raise NotImplementedError

    def destroy_server(self, server_id: str, credentials: Dict[str, str]) -> None:
        """Terminate an instance."""
        raise NotImplementedError

    # -- validation helpers ------------------------------------------------

    def require_credentials(self, credentials: Optional[Dict[str, str]]) -> None:
        """
        Ensure every required credential field is present.

        Raises:
            CloudProviderError: ``422`` listing the missing keys.
        """
        values = credentials or {}
        missing = [
            field["key"]
            for field in self.credentials
            if field.get("required", True) and not str(values.get(field["key"]) or "").strip()
        ]
        if missing:
            raise CloudProviderError(
                f"{self.name}: missing credentials: {', '.join(missing)}", 422
            )

    def resolve_region(self, region: Optional[str]) -> str:
        """Return the requested region, or the provider default."""
        return (region or self.default_region or self._first("regions")).strip()

    def resolve_size(self, size: Optional[str]) -> str:
        """Return the requested size, or the provider default."""
        return (size or self.default_size or self._first("sizes")).strip()

    def resolve_image(self, image: Optional[str]) -> str:
        """Return the requested image alias, or the provider default."""
        return (image or self.default_image or self._first("images")).strip()

    @staticmethod
    def emit(log: Optional[LogCallback], level: str, message: str) -> None:
        """Push a line to the provisioning journal (no-op without callback)."""
        logger.info("[cloud] %s", message)
        if log is not None:
            log(level, message)

# Made with ❤️ by codx-junior