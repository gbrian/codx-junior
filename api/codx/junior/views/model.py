"""
Views domain model.

Defines the Pydantic schema for a saved desktop layout view.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class View(BaseModel):
    """
    Represents a saved desktop layout view for a project.

    Attributes:
        name: Human-readable unique identifier for the view within a project.
        project_id: The project this view belongs to (set server-side on save).
        desktop: Serialized dockview layout produced by ``dockviewApi.toJSON()``.
    """

    name: str
    project_id: Optional[str] = None
    desktop: Optional[Dict[str, Any]] = None

# Made with ❤️ by codx-junior