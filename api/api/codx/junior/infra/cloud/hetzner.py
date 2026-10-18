"""
Hetzner Cloud provider (`/api/infra/cloud/*`).

REST API: https://api.hetzner.cloud/v1, bearer token authentication — the
simplest of the three providers, and the reference implementation of the
`CloudProvider` contract.

Credentials
-----------
| key     | type     | where to find it                                  |
| :------ | :------- | :------------------------------------------------ |
| `token` | password | Hetzner Console → project → Security → API tokens  |

Example
-------
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"name":"codx-junior","public_key":"ssh-ed25519 AAAA…"}' \
     https://api.hetzner.cloud/v1/ssh_keys
```
"""

from typing import Any, Dict, List, Optional

from codx.junior.infra.cloud.base import (
    CloudProvider,
    CloudProviderError,
    LogCallback,
    ProvisionedServer,
    http_client,
    request_json,
)
from codx.junior.infra.models import CloudServerRequest, CloudValidateResult

API_URL = "https://api.hetzner.cloud/v1"


class HetznerProvider(CloudProvider):
    """Create/destroy Hetzner Cloud servers."""

    id = "hetzner"
    name = "Hetzner Cloud"
    icon = "fa-server"
    summary = "Cheap EU/US instances, Docker-friendly Ubuntu images."
    ssh_user = "root"
    uploads_key = True

    credentials: List[Dict[str, Any]] = [
        {
            "key": "token",
            "label": "API token",
            "type": "password",
            "required": True,
            "secret": True,
            "placeholder": "••••••••••••",
            "help": "Console → project → Security → API tokens (read & write).",
        }
    ]

    regions = [
        {"value": "nbg1", "label": "Nuremberg, DE"},
        {"value": "fsn1", "label": "Falkenstein, DE"},
        {"value": "hel1", "label": "Helsinki, FI"},
        {"value": "ash", "label": "Ashburn, US"},
        {"value": "hil", "label": "Hillsboro, US"},
    ]

    sizes = [
        {"value": "cax11", "label": "CAX11 · 2 vCPU · 4 GB", "note": "ARM (Ampere)"},
        {"value": "cx22", "label": "CX22 · 2 vCPU · 4 GB"},
        {"value": "cx32", "label": "CX32 · 4 vCPU · 8 GB"},
        {"value": "cpx21", "label": "CPX21 · 3 vCPU · 4 GB"},
        {"value": "cpx31", "label": "CPX31 · 4 vCPU · 8 GB"},
        {"value": "cpx41", "label": "CPX41 · 8 vCPU · 16 GB"},
    ]

    images = [
        {"value": "ubuntu-24.04", "label": "Ubuntu 24.04 LTS"},
        {"value": "ubuntu-22.04", "label": "Ubuntu 22.04 LTS"},
        {"value": "debian-12", "label": "Debian 12"},
    ]

    default_region = "nbg1"
    default_size = "cx22"
    default_image = "ubuntu-24.04"

    # -- helpers -----------------------------------------------------------

    def _headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {(credentials or {}).get('token', '').strip()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _wait_for_ip(
        self, client, headers: Dict[str, str], server_id: int, log: Optional[LogCallback]
    ) -> str:
        """Poll the server until it runs and has a public IPv4 address."""
        for _ in range(60):
            payload = request_json(
                client,
                "GET",
                f"{API_URL}/servers/{server_id}",
                "Reading the server",
                headers=headers,
            )
            server = (payload or {}).get("server") or {}
            ip = (((server.get("public_net") or {}).get("ipv4") or {}).get("ip")) or ""
            if server.get("status") == "running" and ip:
                return str(ip)
            self.emit(log, "info", f"Waiting for server {server_id} ({server.get('status')})…")
            import time

            time.sleep(5)
        raise CloudProviderError(f"Server {server_id} did not publish an IP in time", 502)

    # -- contract ----------------------------------------------------------

    def validate(
        self, credentials: Dict[str, str], region: Optional[str] = None
    ) -> CloudValidateResult:
        """Check the token against `GET /servers`."""
        self.require_credentials(credentials)
        headers = self._headers(credentials)
        with http_client() as client:
            payload = request_json(
                client,
                "GET",
                f"{API_URL}/servers?per_page=1",
                "Validating the Hetzner token",
                headers=headers,
            )
        count = len((payload or {}).get("servers") or [])
        return CloudValidateResult(
            ok=True,
            account=None,
            message=f"Token valid ({count} server(s) visible).",
        )

    def create_server(
        self,
        request: CloudServerRequest,
        public_key: str,
        log: Optional[LogCallback] = None,
    ) -> ProvisionedServer:
        """Register the SSH key, create the server and wait for its IPv4."""
        self.require_credentials(request.credentials)
        if not public_key:
            raise CloudProviderError("A public SSH key is required", 422)

        headers = self._headers(request.credentials)
        region = self.resolve_region(request.region)
        size = self.resolve_size(request.size)
        image = self.resolve_image(request.image)
        name = (request.name or "").strip()
        if not name:
            raise CloudProviderError("A server name is required", 422)

        with http_client() as client:
            key_payload = request_json(
                client,
                "POST",
                f"{API_URL}/ssh_keys",
                "Registering the SSH key",
                headers=headers,
                json={
                    "name": f"codx-junior-{name}"[:63],
                    "public_key": public_key,
                },
            )
            key_id = ((key_payload or {}).get("ssh_key") or {}).get("id")

            self.emit(log, "info", f"Creating server '{name}' ({size} @ {region})…")
            created = request_json(
                client,
                "POST",
                f"{API_URL}/servers",
                "Creating the server",
                headers=headers,
                json={
                    "name": name,
                    "server_type": size,
                    "image": image,
                    "location": region,
                    "start": True,
                    **({"ssh_keys": [key_id]} if key_id else {}),
                    "labels": {"managed-by": "codx-junior"},
                },
            )
            server = (created or {}).get("server") or {}
            server_id = server.get("id")
            if not server_id:
                raise CloudProviderError("Hetzner did not return a server id", 502)

            ip = self._wait_for_ip(client, headers, server_id, log)

        self.emit(log, "info", f"Server {server_id} is running at {ip}")
        return ProvisionedServer(
            server_id=str(server_id),
            ip=ip,
            hostname=name,
            details={"region": region, "size": size, "image": image},
        )

    def destroy_server(self, server_id: str, credentials: Dict[str, str]) -> None:
        """Delete the server (idempotent: a missing server is a success)."""
        self.require_credentials(credentials)
        with http_client() as client:
            try:
                request_json(
                    client,
                    "DELETE",
                    f"{API_URL}/servers/{server_id}",
                    "Deleting the server",
                    headers=self._headers(credentials),
                )
            except CloudProviderError as ex:
                if "not found" not in ex.message.lower():
                    raise

# Made with ❤️ by codx-junior