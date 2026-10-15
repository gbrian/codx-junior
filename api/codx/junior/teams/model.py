"""
Teams domain model.

A **team** is a hybrid group of AI profiles and human users that share a
common purpose inside a project. Typical examples:

- ``Engineering`` — coding profiles + engineers
- ``Support``     — support-facing profiles + support agents
- ``Leadership``  — planning profiles + team leads

Teams are **per project** (exactly like chats) and are persisted as JSON files
by :class:`codx.junior.teams.team_manager.TeamManager`.

Example persisted team:

```json
{
  "id": "6f1b2c3d-4e5f-6789-abcd-ef0123456789",
  "project_id": "proj_123",
  "name": "Engineering",
  "description": "Builds and reviews the product",
  "color": "#6366f1",
  "icon": "fa-solid fa-robot",
  "profiles": ["software_developer", "analyst"],
  "users": ["alice", "bob"],
  "tags": ["engineering"],
  "created_by": "admin",
  "updated_by": "admin",
  "created_at": "2025-01-01T10:00:00",
  "updated_at": "2025-01-01T10:00:00"
}
```
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


def _now_iso() -> str:
    """Return the current local time as an ISO-8601 string."""
    return datetime.now().isoformat()


class Team(BaseModel):
    """
    A hybrid team of AI profiles and human users within a project.

    Attributes:
        id: Unique team identifier (UUID). Assigned server-side on create.
        project_id: Project this team belongs to (set server-side).
        name: Human-readable team name, e.g. ``"Engineering"``.
        description: Purpose / responsibilities of the team.
        color: UI accent colour (hex string).
        icon: UI icon (FontAwesome class or URL).
        profiles: AI profile names that are part of the team.
        users: Human usernames that are part of the team.
        tags: Free-form tags used to categorize/filter teams.
        created_by: Username that created the team.
        updated_by: Username that last updated the team.
        created_at: Creation timestamp (ISO-8601).
        updated_at: Last update timestamp (ISO-8601).
    """

    id: Optional[str] = Field(default=None, description="Unique team identifier (UUID)")
    project_id: Optional[str] = Field(
        default=None, description="Project this team belongs to"
    )
    name: str = Field(default="", description="Human-readable team name")
    description: str = Field(
        default="", description="Purpose / responsibility of the team"
    )
    color: str = Field(default="#6366f1", description="UI accent colour (hex)")
    logo: str = Field(default="", description="UI logo URL")
    icon: str = Field(default="", description="UI FontAwesome class")
    profiles: List[str] = Field(
        default_factory=list, description="AI profile names that are part of the team"
    )
    users: List[str] = Field(
        default_factory=list, description="Human usernames that are part of the team"
    )
    tags: List[str] = Field(
        default_factory=list, description="Free-form tags to categorize the team"
    )
    created_by: Optional[str] = Field(
        default=None, description="Username that created the team"
    )
    updated_by: Optional[str] = Field(
        default=None, description="Username that last updated the team"
    )
    created_at: str = Field(
        default_factory=_now_iso, description="Creation timestamp (ISO-8601)"
    )
    updated_at: str = Field(
        default_factory=_now_iso, description="Last update timestamp (ISO-8601)"
    )


class TeamMembers(BaseModel):
    """
    Payload for adding/removing team members.

    Used by ``POST/DELETE /api/teams/{team_id}/members``.

    Example:

    ```json
    { "profiles": ["software_developer"], "users": ["alice", "bob"] }
    ```
    """

    profiles: List[str] = Field(
        default_factory=list, description="AI profile names to add/remove"
    )
    users: List[str] = Field(
        default_factory=list, description="Human usernames to add/remove"
    )

# Made with ❤️ by codx-junior