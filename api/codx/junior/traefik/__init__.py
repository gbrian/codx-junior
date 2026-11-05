"""
Traefik routing helpers.

This package owns the *custom* Traefik rules users can attach to workspace
services, running containers or arbitrary URLs.  It is intentionally split
from ``codx.junior.api.traefik`` so the merge/build logic can be unit tested
without importing the FastAPI application.

Storage model
-------------
Rules are stored with the settings object that owns them:

* global rules -> ``GlobalSettings.traefik_rules``
* project rules -> ``CODXJuniorSettings.traefik_rules`` (``.codx/project.json``)

The rule itself has no ``scope`` field: the storage location is the scope.
That is what lets the exact same UI component work against the global and the
project stores.
"""

from codx.junior.traefik.model import TraefikRule, TraefikTargetType

__all__ = ["TraefikRule", "TraefikTargetType"]
