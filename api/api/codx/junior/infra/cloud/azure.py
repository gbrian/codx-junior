"""
Azure provider (`/api/infra/cloud/*`).

Implementation notes
--------------------
No `azure-mgmt` dependency: the ARM REST API is called directly and OAuth2
(client credentials) provides the bearer token.

Each server gets its **own resource group** (`codx-junior-<name>`), so tearing
it down is a single `DELETE` on that group — no orphaned NICs, disks or IPs.

Credentials
-----------
| key               | type     | where to find it                                |
| :---------------- | :------- | :---------------------------------------------- |
| `tenant_id`       | text     | Entra ID → Overview → Tenant ID                  |
| `client_id`       | text     | App registration → Overview → Application (client) ID |
| `client_secret`   | password | App registration → Certificates & secrets        |
| `subscription_id` | text     | Subscriptions → Overview → Subscription ID       |

The app registration needs the `Contributor` role on the subscription.

Example
-------
```python
from codx.junior.infra.cloud import get_provider

provider = get_provider("azure")
print(provider.validate(credentials, region="westeurope"))
```
"""

import logging
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

logger = logging.getLogger(__name__)

ARM = "https://management.azure.com"

TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

SCOPE = "https://management.azure.com/.default"

API_VERSION = {
    "resource_group": "2021-04-01",
    "virtual_network": "2023-09-01",
    "public_ip": "2023-09-01",
    "network_security_group": "2023-09-01",
    "network_interface": "2023-09-01",
    "virtual_machine": "2024-03-01",
    "subscription": "2022-12-01",
}

IMAGE_CATALOG = {
    "ubuntu-24.04": {
        "publisher": "Canonical",
        "offer": "ubuntu-24_04-lts",
        "sku": "server",
        "version": "latest",
    },
    "ubuntu-22.04": {
        "publisher": "Canonical",
        "offer": "0001-com-ubuntu-server-jammy",
        "sku": "22_04-lts-gen2",
        "version": "latest",
    },
    "debian-12": {
        "publisher": "Debian",
        "offer": "debian-12",
        "sku": "12-gen2",
        "version": "latest",
    },
}


class AzureProvider(CloudProvider):
    """Create/destroy Azure VMs with a dedicated resource group per server."""

    id = "azure"
    name = "Microsoft Azure"
    icon = "fa-cloud"
    summary = "Ubuntu VMs on Azure, one resource group per host for clean teardown."
    ssh_user = "azureuser"
    uploads_key = True

    credentials: List[Dict[str, Any]] = [
        {
            "key": "tenant_id",
            "label": "Tenant id",
            "type": "text",
            "required": True,
            "help": "Entra ID → Overview → Tenant ID.",
        },
        {
            "key": "client_id",
            "label": "Application (client) id",
            "type": "text",
            "required": True,
            "help": "App registration → Overview.",
        },
        {
            "key": "client_secret",
            "label": "Client secret",
            "type": "password",
            "required": True,
            "secret": True,
            "help": "App registration → Certificates & secrets.",
        },
        {
            "key": "subscription_id",
            "label": "Subscription id",
            "type": "text",
            "required": True,
            "help": "Subscriptions → Overview.",
        },
    ]

    regions = [
        {"value": "westeurope", "label": "West Europe"},
        {"value": "northeurope", "label": "North Europe"},
        {"value": "eastus", "label": "East US"},
        {"value": "westus2", "label": "West US 2"},
        {"value": "southeastasia", "label": "Southeast Asia"},
        {"value": "brazilsouth", "label": "Brazil South"},
    ]

    sizes = [
        {"value": "Standard_B1s", "label": "B1s · 1 vCPU · 1 GB", "note": "Burstable"},
        {"value": "Standard_B2s", "label": "B2s · 2 vCPU · 4 GB"},
        {"value": "Standard_B2ms", "label": "B2ms · 2 vCPU · 8 GB"},
        {"value": "Standard_D2s_v5", "label": "D2s v5 · 2 vCPU · 8 GB"},
        {"value": "Standard_D4s_v5", "label": "D4s v5 · 4 vCPU · 16 GB"},
    ]

    images = [
        {"value": "ubuntu-24.04", "label": "Ubuntu 24.04 LTS"},
        {"value": "ubuntu-22.04", "label": "Ubuntu 22.04 LTS"},
        {"value": "debian-12", "label": "Debian 12"},
    ]

    default_region = "westeurope"
    default_size = "Standard_B2s"
    default_image = "ubuntu-24.04"

    # -- auth --------------------------------------------------------------

    def _token(self, credentials: Dict[str, str]) -> str:
        """Fetch an ARM access token with the client-credentials flow."""
        tenant = (credentials.get("tenant_id") or "").strip()
        url = TOKEN_URL.format(tenant=tenant)
        with http_client(60) as client:
            payload = request_json(
                client,
                "POST",
                url,
                "Requesting an Azure token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": (credentials.get("client_id") or "").strip(),
                    "client_secret": (credentials.get("client_secret") or "").strip(),
                    "scope": SCOPE,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        token = (payload or {}).get("access_token")
        if not token:
            raise CloudProviderError("Azure did not return an access token", 422)
        return token

    def _headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token(credentials)}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _resource_group(name: str) -> str:
        """Deterministic resource group name for a server."""
        safe = "".join(char for char in name if char.isalnum() or char in "-_")[:50]
        return f"codx-junior-{safe or 'host'}"

    # -- contract ----------------------------------------------------------

    def validate(
        self, credentials: Dict[str, str], region: Optional[str] = None
    ) -> CloudValidateResult:
        """Check the credentials by reading the subscription."""
        self.require_credentials(credentials)
        subscription = (credentials.get("subscription_id") or "").strip()
        with http_client(60) as client:
            payload = request_json(
                client,
                "GET",
                f"{ARM}/subscriptions/{subscription}"
                f"?api-version={API_VERSION['subscription']}",
                "Reading the subscription",
                headers=self._headers(credentials),
            )
        account = (payload or {}).get("displayName") or subscription
        return CloudValidateResult(
            ok=True, account=str(account), message=f"Connected to '{account}'."
        )

    def create_server(
        self,
        request: CloudServerRequest,
        public_key: str,
        log: Optional[LogCallback] = None,
    ) -> ProvisionedServer:
        """Create the resource group, networking and the VM, then read its IP."""
        self.require_credentials(request.credentials)
        if not public_key:
            raise CloudProviderError("A public SSH key is required", 422)

        credentials = request.credentials
        subscription = (credentials.get("subscription_id") or "").strip()
        name = (request.name or "").strip()
        if not name:
            raise CloudProviderError("A server name is required", 422)

        location = self.resolve_region(request.region)
        size = self.resolve_size(request.size)
        ssh_user = (request.ssh_user or self.ssh_user or "azureuser").strip()
        image_ref = IMAGE_CATALOG.get(self.resolve_image(request.image))
        if not image_ref:
            raise CloudProviderError(
                f"Unsupported Azure image alias '{request.image}'", 422
            )

        group = self._resource_group(name)
        base = f"{ARM}/subscriptions/{subscription}"
        headers = self._headers(credentials)

        with http_client(180) as client:
            self.emit(log, "info", f"Creating resource group '{group}' in {location}…")
            request_json(
                client,
                "PUT",
                f"{base}/resourceGroups/{group}?api-version={API_VERSION['resource_group']}",
                "Creating the resource group",
                headers=headers,
                json={"location": location, "tags": {"managed-by": "codx-junior"}},
            )

            self.emit(log, "info", "Creating the virtual network…")
            request_json(
                client,
                "PUT",
                f"{base}/resourceGroups/{group}/providers/Microsoft.Network"
                f"/virtualNetworks/{name}-vnet?api-version={API_VERSION['virtual_network']}",
                "Creating the virtual network",
                headers=headers,
                json={
                    "location": location,
                    "properties": {
                        "addressSpace": {"addressPrefixes": ["10.0.0.0/16"]},
                        "subnets": [
                            {
                                "name": "default",
                                "properties": {"addressPrefix": "10.0.0.0/24"},
                            }
                        ],
                    },
                },
            )

            self.emit(log, "info", "Reserving a public IP…")
            request_json(
                client,
                "PUT",
                f"{base}/resourceGroups/{group}/providers/Microsoft.Network"
                f"/publicIPAddresses/{name}-pip?api-version={API_VERSION['public_ip']}",
                "Creating the public IP",
                headers=headers,
                json={
                    "location": location,
                    "sku": {"name": "Standard"},
                    "properties": {"publicIPAllocationMethod": "Static"},
                },
            )

            self.emit(log, "info", "Applying the firewall rules…")
            ports = sorted({22, *[int(port) for port in request.open_ports or [] if port]})
            request_json(
                client,
                "PUT",
                f"{base}/resourceGroups/{group}/providers/Microsoft.Network"
                f"/networkSecurityGroups/{name}-nsg"
                f"?api-version={API_VERSION['network_security_group']}",
                "Creating the network security group",
                headers=headers,
                json={
                    "location": location,
                    "properties": {
                        "securityRules": [
                            {
                                "name": f"allow-tcp-{port}",
                                "properties": {
                                    "priority": 1000 + index,
                                    "direction": "Inbound",
                                    "access": "Allow",
                                    "protocol": "Tcp",
                                    "sourcePortRange": "*",
                                    "destinationPortRange": str(port),
                                    "sourceAddressPrefix": "*",
                                    "destinationAddressPrefix": "*",
                                },
                            }
                            for index, port in enumerate(ports)
                        ]
                    },
                },
            )

            self.emit(log, "info", "Creating the network interface…")
            nic_id = (
                f"{base}/resourceGroups/{group}/providers/Microsoft.Network"
                f"/networkInterfaces/{name}-nic"
            )
            request_json(
                client,
                "PUT",
                f"{nic_id}?api-version={API_VERSION['network_interface']}",
                "Creating the network interface",
                headers=headers,
                json={
                    "location": location,
                    "properties": {
                        "ipConfigurations": [
                            {
                                "name": "ipconfig1",
                                "properties": {
                                    "subnet": {
                                        "id": f"{base}/resourceGroups/{group}/providers"
                                        f"/Microsoft.Network/virtualNetworks/{name}-vnet"
                                        f"/subnets/default"
                                    },
                                    "publicIPAddress": {
                                        "id": f"{base}/resourceGroups/{group}/providers"
                                        f"/Microsoft.Network/publicIPAddresses/{name}-pip"
                                    },
                                },
                            }
                        ],
                        "networkSecurityGroup": {
                            "id": f"{base}/resourceGroups/{group}/providers"
                            f"/Microsoft.Network/networkSecurityGroups/{name}-nsg"
                        },
                    },
                },
            )

            self.emit(log, "info", f"Creating the VM '{name}' ({size})…")
            request_json(
                client,
                "PUT",
                f"{base}/resourceGroups/{group}/providers/Microsoft.Compute"
                f"/virtualMachines/{name}?api-version={API_VERSION['virtual_machine']}",
                "Creating the virtual machine",
                headers=headers,
                json={
                    "location": location,
                    "tags": {"managed-by": "codx-junior", **(request.tags or {})},
                    "properties": {
                        "hardwareProfile": {"vmSize": size},
                        "storageProfile": {
                            "imageReference": image_ref,
                            "osDisk": {
                                "createOption": "FromImage",
                                "managedDisk": {
                                    "storageAccountType": "StandardSSD_LRS"
                                },
                            },
                        },
                        "osProfile": {
                            "computerName": name[:64],
                            "adminUsername": ssh_user,
                            "linuxConfiguration": {
                                "disablePasswordAuthentication": True,
                                "ssh": {
                                    "publicKeys": [
                                        {
                                            "path": f"/home/{ssh_user}/.ssh/authorized_keys",
                                            "keyData": public_key,
                                        }
                                    ]
                                },
                            },
                        },
                        "networkProfile": {
                            "networkInterfaces": [{"id": nic_id}]
                        },
                    },
                },
            )

            self.emit(log, "info", "Reading the public IP address…")
            payload = request_json(
                client,
                "GET",
                f"{base}/resourceGroups/{group}/providers/Microsoft.Network"
                f"/publicIPAddresses/{name}-pip?api-version={API_VERSION['public_ip']}",
                "Reading the public IP",
                headers=headers,
            )

        ip = ((payload or {}).get("properties") or {}).get("ipAddress") or ""
        if not ip:
            raise CloudProviderError(
                f"Azure VM '{name}' did not get a public IP address", 502
            )

        self.emit(log, "info", f"VM '{name}' is reachable at {ip}")
        return ProvisionedServer(
            server_id=group,
            ip=str(ip),
            hostname=name,
            details={"resource_group": group, "size": size, "location": location},
        )

    def destroy_server(self, server_id: str, credentials: Dict[str, str]) -> None:
        """Delete the whole resource group of the server."""
        self.require_credentials(credentials)
        subscription = (credentials.get("subscription_id") or "").strip()
        group = server_id if server_id.startswith("codx-junior-") else self._resource_group(server_id)

        with http_client(300) as client:
            try:
                request_json(
                    client,
                    "DELETE",
                    f"{ARM}/subscriptions/{subscription}/resourceGroups/{group}"
                    f"?api-version={API_VERSION['resource_group']}",
                    "Deleting the resource group",
                    headers=self._headers(credentials),
                )
            except CloudProviderError as ex:
                if "not found" not in ex.message.lower():
                    raise

# Made with ❤️ by codx-junior