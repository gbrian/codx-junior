"""
AWS EC2 provider (`/api/infra/cloud/*`).

Implementation notes
--------------------
No `boto3` dependency: EC2 is driven through its **Query API**
(``POST https://ec2.<region>.amazonaws.com`` with form-encoded parameters and
an XML answer) and requests are signed with **AWS Signature Version 4**
(`hmac`/`hashlib` only).

Credentials
-----------
| key                 | type     | notes                                        |
| :------------------ | :------- | :------------------------------------------- |
| `access_key_id`     | text     | IAM user with EC2 permissions                |
| `secret_access_key` | password | matching secret                              |
| `session_token`     | password | optional (temporary STS credentials)         |

Provisioning steps: `ImportKeyPair` → security group (SSH + extra ports) →
`RunInstances` → poll `DescribeInstances` for the public IP.

Example
-------
```python
from codx.junior.infra.cloud import get_provider

provider = get_provider("aws")
server = provider.create_server(request, public_key="ssh-ed25519 AAAA…")
print(server.server_id, server.ip)
```
"""

import hashlib
import hmac
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

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

API_VERSION = "2016-11-15"

SERVICE = "ec2"

# Provider-side image aliases: label → (owner id, name pattern)
IMAGE_CATALOG = {
    "ubuntu-24.04": {
        "owner": "099720109477",
        "pattern": "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*",
    },
    "ubuntu-22.04": {
        "owner": "099720109477",
        "pattern": "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*",
    },
    "debian-12": {
        "owner": "136693071363",
        "pattern": "debian-12-amd64-*",
    },
}

SECURITY_GROUP_NAME = "codx-junior-infra"


def _sign(key: bytes, message: str) -> bytes:
    """HMAC-SHA256 helper used by the SigV4 key derivation."""
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _find_all(node: ET.Element, tag: str) -> List[ET.Element]:
    """Find descendants by local tag name (namespace agnostic)."""
    return [element for element in node.iter() if element.tag.split("}")[-1] == tag]


def _text(node: ET.Element, tag: str, default: str = "") -> str:
    """Text of the first child with the given tag."""
    for child in node:
        if child.tag.split("}")[-1] == tag:
            return (child.text or default).strip()
    return default


class AwsProvider(CloudProvider):
    """Create/destroy EC2 instances through the signed Query API."""

    id = "aws"
    name = "Amazon Web Services"
    icon = "fa-aws"
    summary = "EC2 instances in any region, billed per second."
    ssh_user = "ubuntu"
    uploads_key = True

    credentials: List[Dict[str, Any]] = [
        {
            "key": "access_key_id",
            "label": "Access key id",
            "type": "text",
            "required": True,
            "placeholder": "AKIA…",
            "help": "IAM → user → Security credentials → access keys.",
        },
        {
            "key": "secret_access_key",
            "label": "Secret access key",
            "type": "password",
            "required": True,
            "secret": True,
            "help": "Shown only once when the access key is created.",
        },
        {
            "key": "session_token",
            "label": "Session token (optional)",
            "type": "password",
            "required": False,
            "secret": True,
            "help": "Only for temporary STS credentials.",
        },
    ]

    regions = [
        {"value": "us-east-1", "label": "N. Virginia (us-east-1)"},
        {"value": "us-west-2", "label": "Oregon (us-west-2)"},
        {"value": "eu-west-1", "label": "Ireland (eu-west-1)"},
        {"value": "eu-central-1", "label": "Frankfurt (eu-central-1)"},
        {"value": "ap-southeast-1", "label": "Singapore (ap-southeast-1)"},
        {"value": "sa-east-1", "label": "São Paulo (sa-east-1)"},
    ]

    sizes = [
        {"value": "t3.micro", "label": "t3.micro · 2 vCPU · 1 GB", "note": "Free tier"},
        {"value": "t3.small", "label": "t3.small · 2 vCPU · 2 GB"},
        {"value": "t3.medium", "label": "t3.medium · 2 vCPU · 4 GB"},
        {"value": "t3.large", "label": "t3.large · 2 vCPU · 8 GB"},
        {"value": "m5.large", "label": "m5.large · 2 vCPU · 8 GB"},
        {"value": "c5.large", "label": "c5.large · 2 vCPU · 4 GB"},
    ]

    images = [
        {"value": "ubuntu-24.04", "label": "Ubuntu 24.04 LTS"},
        {"value": "ubuntu-22.04", "label": "Ubuntu 22.04 LTS"},
        {"value": "debian-12", "label": "Debian 12"},
    ]

    default_region = "us-east-1"
    default_size = "t3.small"
    default_image = "ubuntu-24.04"

    # -- SigV4 -------------------------------------------------------------

    def _signed_headers(
        self, credentials: Dict[str, str], region: str, body: str
    ) -> Dict[str, str]:
        """Build the SigV4 headers for a form-encoded Query API call."""
        access_key = (credentials.get("access_key_id") or "").strip()
        secret_key = (credentials.get("secret_access_key") or "").strip()
        token = (credentials.get("session_token") or "").strip()

        host = f"{SERVICE}.{region}.amazonaws.com"
        amz_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        date_stamp = amz_date[:8]

        headers: Dict[str, str] = {
            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            "host": host,
            "x-amz-date": amz_date,
        }
        if token:
            headers["x-amz-security-token"] = token

        signed_headers = ";".join(sorted(headers))
        canonical_headers = "".join(
            f"{name}:{headers[name]}\n" for name in sorted(headers)
        )
        canonical_request = "\n".join(
            ["POST", "/", "", canonical_headers, signed_headers, _sha256(body)]
        )
        credential_scope = f"{date_stamp}/{region}/{SERVICE}/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                _sha256(canonical_request),
            ]
        )

        signing_key = _sign(f"AWS4{secret_key}".encode("utf-8"), date_stamp)
        signing_key = _sign(signing_key, region)
        signing_key = _sign(signing_key, SERVICE)
        signing_key = _sign(signing_key, "aws4_request")
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        headers["authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return headers

    def _call(
        self, credentials: Dict[str, str], region: str, params: Dict[str, str]
    ) -> ET.Element:
        """Sign and POST a Query API action, returning the parsed XML root."""
        payload = {"Version": API_VERSION, **params}
        body = urlencode({key: str(value) for key, value in payload.items()})
        headers = self._signed_headers(credentials, region, body)
        url = f"https://{SERVICE}.{region}.amazonaws.com/"

        with http_client(120) as client:
            try:
                response = client.post(url, content=body, headers=headers)
            except Exception as ex:  # httpx.HTTPError
                raise CloudProviderError(f"AWS request failed: {ex}", 502) from ex

        if response.status_code >= 400:
            message = ""
            try:
                root = ET.fromstring(response.text or "")
                message = _text(root, "Message") or _text(root, "message")
            except ET.ParseError:
                message = (response.text or "")[:300]
            status = 422 if response.status_code in (400, 401, 403) else 502
            raise CloudProviderError(
                f"AWS request failed: {message or response.status_code}", status
            )

        try:
            return ET.fromstring(response.text or "<empty/>")
        except ET.ParseError as ex:
            raise CloudProviderError(f"Unreadable AWS response: {ex}", 502) from ex

    # -- helpers -----------------------------------------------------------

    def _resolve_ami(self, credentials: Dict[str, str], region: str, image: str) -> str:
        """Resolve an image alias (or passthrough ``ami-…``) to an AMI id."""
        reference = self.resolve_image(image)
        if reference.startswith("ami-"):
            return reference

        catalog = IMAGE_CATALOG.get(reference)
        if not catalog:
            raise CloudProviderError(f"Unsupported AWS image alias '{reference}'", 422)

        root = self._call(
            credentials,
            region,
            {
                "Action": "DescribeImages",
                "Owner.1": catalog["owner"],
                "Filter.1.Name": "name",
                "Filter.1.Value.1": catalog["pattern"],
                "Filter.2.Name": "state",
                "Filter.2.Value.1": "available",
            },
        )
        amis = [
            _text(item, "imageId")
            for item in _find_all(root, "imagesSet")
            for item in _find_all(item, "item")
        ]
        if not amis:
            raise CloudProviderError(
                f"No AMI matches '{reference}' in {region}", 422
            )
        return amis[-1]

    def _import_key(
        self, credentials: Dict[str, str], region: str, name: str, public_key: str
    ) -> str:
        """Register the public key (idempotent). Returns the EC2 key name."""
        key_name = f"codx-junior-{name}"[:255]
        try:
            self._call(
                credentials,
                region,
                {"Action": "ImportKeyPair", "KeyName": key_name, "PublicKeyMaterial": public_key},
            )
        except CloudProviderError as ex:
            if "Duplicate" not in ex.message and "already exists" not in ex.message:
                raise
        return key_name

    def _ensure_security_group(
        self, credentials: Dict[str, str], region: str, open_ports: List[int]
    ) -> str:
        """Find or create the security group exposing SSH (+ extra ports)."""
        root = self._call(
            credentials,
            region,
            {
                "Action": "DescribeSecurityGroups",
                "Filter.1.Name": "group-name",
                "Filter.1.Value.1": SECURITY_GROUP_NAME,
            },
        )
        groups = _find_all(root, "item")
        group_id = ""
        for group in groups:
            candidate = _text(group, "groupId")
            if candidate:
                group_id = candidate
                break

        if not group_id:
            created = self._call(
                credentials,
                region,
                {
                    "Action": "CreateSecurityGroup",
                    "GroupName": SECURITY_GROUP_NAME,
                    "GroupDescription": "codx-junior infra management (SSH)",
                },
            )
            group_id = _text(created, "groupId")
            if not group_id:
                raise CloudProviderError("AWS did not return a security group id", 502)

            ports = sorted({22, *[int(port) for port in open_ports or [] if port]})
            params: Dict[str, str] = {
                "Action": "AuthorizeSecurityGroupIngress",
                "GroupId": group_id,
            }
            for index, port in enumerate(ports, start=1):
                params[f"IpPermissions.{index}.IpProtocol"] = "tcp"
                params[f"IpPermissions.{index}.FromPort"] = str(port)
                params[f"IpPermissions.{index}.ToPort"] = str(port)
                params[f"IpPermissions.{index}.IpRanges.1.CidrIp"] = "0.0.0.0/0"
            self._call(credentials, region, params)

        return group_id

    def _public_ip(
        self, credentials: Dict[str, str], region: str, instance_id: str,
        log: Optional[LogCallback],
    ) -> str:
        """Poll `DescribeInstances` until the instance publishes an IP."""
        for _ in range(60):
            root = self._call(
                credentials,
                region,
                {"Action": "DescribeInstances", "InstanceId.1": instance_id},
            )
            for instance in _find_all(root, "instancesSet"):
                for item in _find_all(instance, "item"):
                    ip = _text(item, "ipAddress")
                    if ip:
                        return ip
            self.emit(log, "info", f"Waiting for instance {instance_id} to get an IP…")
            time.sleep(5)
        raise CloudProviderError(f"Instance {instance_id} did not get an IP in time", 502)

    # -- contract ----------------------------------------------------------

    def validate(
        self, credentials: Dict[str, str], region: Optional[str] = None
    ) -> CloudValidateResult:
        """Check the credentials with a cheap `DescribeRegions` call."""
        self.require_credentials(credentials)
        region_name = self.resolve_region(region)
        self._call(credentials, region_name, {"Action": "DescribeRegions"})
        return CloudValidateResult(
            ok=True,
            account=None,
            message=f"Credentials valid (region {region_name}).",
        )

    def create_server(
        self,
        request: CloudServerRequest,
        public_key: str,
        log: Optional[LogCallback] = None,
    ) -> ProvisionedServer:
        """Import the key, ensure the security group and run the instance."""
        self.require_credentials(request.credentials)
        if not public_key:
            raise CloudProviderError("A public SSH key is required", 422)

        credentials = request.credentials
        region = self.resolve_region(request.region)
        size = self.resolve_size(request.size)
        name = (request.name or "").strip()
        if not name:
            raise CloudProviderError("A server name is required", 422)

        self.emit(log, "info", "Registering the SSH key pair…")
        key_name = self._import_key(credentials, region, name, public_key)

        self.emit(log, "info", "Ensuring the SSH security group…")
        group_id = self._ensure_security_group(credentials, region, request.open_ports)

        self.emit(log, "info", f"Resolving the image '{self.resolve_image(request.image)}'…")
        ami = self._resolve_ami(credentials, region, request.image)

        tags: Dict[str, str] = {
            "Name": name,
            "managed-by": "codx-junior",
            **(request.tags or {}),
        }
        params: Dict[str, str] = {
            "Action": "RunInstances",
            "ImageId": ami,
            "InstanceType": size,
            "MinCount": "1",
            "MaxCount": "1",
            "KeyName": key_name,
            "SecurityGroupId.1": group_id,
        }
        for index, (tag_key, tag_value) in enumerate(tags.items(), start=1):
            params[f"TagSpecification.1.ResourceType"] = "instance"
            params[f"TagSpecification.1.Tag.{index}.Key"] = tag_key
            params[f"TagSpecification.1.Tag.{index}.Value"] = tag_value

        self.emit(log, "info", f"Starting a '{size}' instance in {region}…")
        root = self._call(credentials, region, params)
        instance_id = ""
        for item in _find_all(root, "instancesSet"):
            for instance in _find_all(item, "item"):
                instance_id = _text(instance, "instanceId")
                break
        if not instance_id:
            raise CloudProviderError("AWS did not return an instance id", 502)

        ip = self._public_ip(credentials, region, instance_id, log)
        self.emit(log, "info", f"Instance {instance_id} is running at {ip}")
        return ProvisionedServer(
            server_id=instance_id,
            ip=ip,
            hostname=name,
            details={"region": region, "size": size, "key_name": key_name},
        )

    def destroy_server(self, server_id: str, credentials: Dict[str, str]) -> None:
        """Terminate the instance."""
        self.require_credentials(credentials)
        region = self.resolve_region(None)
        self._call(
            credentials,
            region,
            {"Action": "TerminateInstances", "InstanceId.1": server_id},
        )

# Made with ❤️ by codx-junior