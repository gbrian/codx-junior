"""
TeamManager — project-scoped team persistence.

Teams are hybrid groups of AI profiles and human users that share a common
purpose within a project (e.g. "Engineering", "Support", "Leadership").
They are stored as JSON files inside the project's ``.codx`` directory:

    <codx_path>/teams/<slugified-name>.<team-id>.json

Storing teams next to the project (like chats under ``tasks/``) keeps them
scoped to the project they belong to.

```mermaid
classDiagram
    class TeamManager {
        +settings: CODXJuniorSettings
        +teams_path: str
        +list_teams() List~Team~
        +find_by_id(team_id) Optional~Team~
        +find_by_name(name) Optional~Team~
        +save_team(team) Team
        +delete_team(team_id) bool
        +add_members(team_id, profiles, users, actor) Team
        +remove_members(team_id, profiles, users, actor) Team
    }
```
"""

import os
import json
import uuid
import logging
import pathlib

from datetime import datetime
from typing import List, Optional

from slugify import slugify

from codx.junior.settings import CODXJuniorSettings
from codx.junior.teams.model import Team

logger = logging.getLogger(__name__)

TEAMS_DIR = "teams"
TEAM_FILE_EXTENSION = ".json"


def _dedupe(values: List[str]) -> List[str]:
    """Return *values* with duplicates removed, preserving order."""
    return list(dict.fromkeys(values))


class TeamManager:
    """
    Manages hybrid teams (AI profiles + humans) for a given project.

    Contract:
        * ``save_team`` upserts by ``id`` (a new id is generated when missing)
          and removes the superseded file when the name changes.
        * ``add_members`` / ``remove_members`` mutate the persisted team and
          return the saved instance.

    :param settings: Project-level settings.
    """

    def __init__(self, settings: CODXJuniorSettings) -> None:
        """Initialise the manager, creating the ``teams`` directory."""
        self.settings = settings
        self.teams_path = os.path.join(settings.codx_path, TEAMS_DIR)
        os.makedirs(self.teams_path, exist_ok=True)
        logger.debug("TeamManager initialized at '%s'", self.teams_path)

    # -------------------------------------------------------------------------
    # Path helpers
    # -------------------------------------------------------------------------

    def _team_file_path(self, team: Team) -> str:
        """
        Build the canonical file path for *team*.

        :param team: Team whose path to compute.
        :return: Absolute file path string.
        """
        return os.path.join(
            self.teams_path,
            f"{slugify(team.name)}.{team.id}{TEAM_FILE_EXTENSION}",
        )

    def _team_file_paths(self) -> List[str]:
        """Return every team file path for this project."""
        return [
            str(path)
            for path in pathlib.Path(self.teams_path).glob(f"*{TEAM_FILE_EXTENSION}")
            if path.is_file()
        ]

    def _find_team_file(self, team_id: Optional[str]) -> Optional[str]:
        """
        Return the file path backing *team_id*, or ``None`` when missing.

        The team id is the last segment of the file name
        (``<slug>.<id>.json``), so matching on the suffix is unambiguous.

        :param team_id: Team UUID to locate.
        :return: File path or ``None``.
        """
        if not team_id:
            return None
        suffix = f".{team_id}{TEAM_FILE_EXTENSION}"
        return next((p for p in self._team_file_paths() if p.endswith(suffix)), None)

    # -------------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------------

    def _load_team_from_file(self, file_path: str) -> Optional[Team]:
        """
        Load and deserialize a single team from a JSON file.

        :param file_path: Absolute path to the team JSON file.
        :return: A :class:`Team` instance, or ``None`` if loading fails.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.loads(fh.read())
            return Team(**data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error("Failed to load team from '%s': %s", file_path, exc)
            return None

    def list_teams(self) -> List[Team]:
        """
        Return all teams saved for this project, sorted by name.

        :return: List of :class:`Team` instances.
        """
        teams = [
            team
            for team in (self._load_team_from_file(p) for p in self._team_file_paths())
            if team is not None
        ]
        teams.sort(key=lambda team: (team.name or "").lower())
        logger.info(
            "Listed %d teams for project '%s'", len(teams), self.settings.project_id
        )
        return teams

    def find_by_id(self, team_id: Optional[str]) -> Optional[Team]:
        """
        Return a single team by id, or ``None`` when not found.

        :param team_id: UUID of the team to locate.
        :return: Loaded :class:`Team` or ``None``.
        """
        file_path = self._find_team_file(team_id)
        if file_path:
            return self._load_team_from_file(file_path)
        if team_id:
            logger.warning("Team id '%s' not found", team_id)
        return None

    def find_by_name(self, name: Optional[str]) -> Optional[Team]:
        """
        Return a single team by (case-insensitive) name, or ``None``.

        :param name: Team name to look up.
        :return: Loaded :class:`Team` or ``None``.
        """
        if not name:
            return None
        target = name.strip().lower()
        return next(
            (
                team
                for team in self.list_teams()
                if (team.name or "").strip().lower() == target
            ),
            None,
        )

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    def save_team(self, team: Team) -> Team:
        """
        Create or update a team (keyed by ``id``) and persist it to disk.

        A new UUID is assigned when the team has none, and the team is always
        bound to the current project. When the team was renamed, the previous
        file is removed so no orphan is left behind.

        :param team: The team to persist (mutated in place).
        :return: The persisted team.
        :raises ValueError: when the team has no name.
        """
        if not team.name or not team.name.strip():
            raise ValueError("Cannot save a team without a name.")

        if not team.id:
            team.id = str(uuid.uuid4())

        # Teams always belong to the current project.
        team.project_id = self.settings.project_id

        now = datetime.now().isoformat()
        team.updated_at = now
        if not team.created_at:
            team.created_at = now

        # Detect a pre-existing file (id is stable) so a rename removes the
        # superseded file instead of leaving an orphan behind.
        previous_file = self._find_team_file(team.id)
        file_path = self._team_file_path(team)

        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(team.model_dump(), indent=2))

        if previous_file and previous_file != file_path and os.path.isfile(previous_file):
            os.remove(previous_file)
            logger.info("Removed superseded team file '%s' after rename", previous_file)

        logger.info("Saved team '%s' (id=%s) to '%s'", team.name, team.id, file_path)
        return team

    def delete_team(self, team_id: Optional[str]) -> bool:
        """
        Delete the team identified by *team_id*.

        :param team_id: UUID of the team to delete.
        :return: ``True`` when a team was deleted, ``False`` otherwise.
        """
        file_path = self._find_team_file(team_id)
        if file_path and os.path.isfile(file_path):
            os.remove(file_path)
            logger.info("Deleted team '%s' at '%s'", team_id, file_path)
            return True
        logger.warning("Attempted to delete non-existent team '%s'", team_id)
        return False

    # -------------------------------------------------------------------------
    # Membership
    # -------------------------------------------------------------------------

    def add_members(
        self,
        team_id: str,
        profiles: Optional[List[str]] = None,
        users: Optional[List[str]] = None,
        actor: Optional[str] = None,
    ) -> Team:
        """
        Add AI profiles and/or humans to a team (duplicates are ignored).

        :param team_id: UUID of the team to update.
        :param profiles: AI profile names to add.
        :param users: Human usernames to add.
        :param actor: Optional username recorded in ``updated_by``.
        :return: The persisted team.
        :raises ValueError: when the team does not exist.
        """
        team = self.find_by_id(team_id)
        if not team:
            raise ValueError(f"Team not found: {team_id}")

        if profiles:
            team.profiles = _dedupe(list(team.profiles or []) + list(profiles))
        if users:
            team.users = _dedupe(list(team.users or []) + list(users))
        if actor:
            team.updated_by = actor

        return self.save_team(team)

    def remove_members(
        self,
        team_id: str,
        profiles: Optional[List[str]] = None,
        users: Optional[List[str]] = None,
        actor: Optional[str] = None,
    ) -> Team:
        """
        Remove AI profiles and/or humans from a team.

        :param team_id: UUID of the team to update.
        :param profiles: AI profile names to remove.
        :param users: Human usernames to remove.
        :param actor: Optional username recorded in ``updated_by``.
        :return: The persisted team.
        :raises ValueError: when the team does not exist.
        """
        team = self.find_by_id(team_id)
        if not team:
            raise ValueError(f"Team not found: {team_id}")

        if profiles:
            remove_profiles = set(profiles)
            team.profiles = [p for p in (team.profiles or []) if p not in remove_profiles]
        if users:
            remove_users = set(users)
            team.users = [u for u in (team.users or []) if u not in remove_users]
        if actor:
            team.updated_by = actor

        return self.save_team(team)

# Made with ❤️ by codx-junior