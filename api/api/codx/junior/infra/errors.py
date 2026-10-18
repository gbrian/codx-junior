"""
Exception types shared by the infrastructure layer.

The HTTP layer (`api/codx/junior/api/infra.py`) maps these to status codes:

| Exception               | HTTP | Meaning                                        |
| :---------------------- | :--- | :--------------------------------------------- |
| `InfraValidationError`  | 422  | A host definition / key was rejected            |
| `InfraConflictError`    | 409  | The resource is still in use                    |
| `SshError`              | 422  | The SSH handshake (or the `ssh` binary) failed  |

Cloud failures carry their own `status_code` in
`codx/junior/infra/cloud/base.py` (`CloudProviderError`).

Example
-------
```python
from codx.junior.infra.errors import InfraValidationError

if not payload.hostname:
    raise InfraValidationError("An SSH host requires 'hostname'")
```
"""


class InfraValidationError(ValueError):
    """A supplied definition is invalid (host, key, provisioning request)."""


class InfraConflictError(RuntimeError):
    """The resource cannot be deleted because something still references it."""


class SshError(RuntimeError):
    """An SSH operation failed (binary missing, handshake refused, tunnel)."""

# Made with ❤️ by codx-junior