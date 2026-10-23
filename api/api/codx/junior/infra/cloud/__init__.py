"""
Cloud provisioning engine (`/api/infra/cloud/*`).

Registry
--------
`PROVIDERS` maps the id used by the API (`aws`, `azure`, `hetzner`) to its
implementation. Adding a provider is: implement `CloudProvider`, register it
here — the wizard renders itself from `GET /api/infra/cloud/providers`.

Example
-------
```python
from codx.junior.infra.cloud import get_provider, provider_catalog

print([provider.id for provider in provider_catalog().providers])  # ['aws', 'azure', 'hetzner']
print(get_provider("aws").catalog().default_size)                 # 't3.small'
```

Diagram
-------
flowchart LR
    R[api/infra.py] --> J[CloudJobManager]
    J --> P{Provider}
    P --> H[Hetzner REST]
    P --> A[AWS EC2 Query]
    P --> Z[Azure ARM]
    J --> S[SshKeyStore]
    J --> D[InfraHostStore]
"""
"""

from typing import Dict, List

from codx.junior.infra.cloud.aws import AwsProvider
from codx.junior.infra.cloud.azure import AzureProvider
from codx.junior.infra.cloud.base import (
    CloudProvider,
    CloudCredentialsError,  # type: ignore[attr-defined]
) if False else None  # placeholder removed below