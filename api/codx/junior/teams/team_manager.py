"""
Team storage and composition for codx-junior.

A **team** is a named group of profiles working together: a lead plus the
profiles that cover the different responsibilities of a task. Teams are the
composition layer on top of profiles, so they never duplicate instructions:
a team only references profile names and the instructions are resolved from
the :class:`~codx.junior.profiles.profile_manager.ProfileManager` when the
team is used.

Storage layout (one folder per team)::

    .codx/teams/<Name>/<Name>.team   # JSON definition (members, tools, model)
    .codx/teams/<Name>/<Name>.md     # Markdown charter (team instructions)

The layout mirrors ``.codx/profiles`` on purpose: same two files, same
folder-name-equals-name invariant, so the mental model is the same.

The team shape itself (roster, ordering, serialization) lives in
:mod:`codx.junior.model.team`; this module only handles the filesystem and the
resolution against the profile manager.

Made with ❤️ by codx-junior
"""

import glob
import json
import logging
import os
import shutil

from datetime import datetime
from typing import Any, Dict, List, Optional

from codx.junior.model.team import Team, TeamMember
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# Extension of the JSON definition (the charter uses ``.md`` like profiles).
TEAM_EXTENSION = ".team"


class TeamManager:
    """
    CRUD and composition for the teams of a project.

    Every team lives in its own folder under ``.codx/teams`` and is made of two
    files: ``<Name>.team`` (definition) and ``<Name>.md`` (charter). Both are
    written together by :meth:`save_team`, so a team is never left half-saved.

    Attributes:
        settings: Project settings.
        teams_path: Absolute path of the project's ``.codx/teams`` folder.
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        profile_manager: Optional[ProfileManager] = None,
    ):
        """
        Initialize the manager.

        Args:
            settings: Project settings.
            profile_manager: Optional shared ProfileManager (built on demand).
        """
        self.settings = settings
        self.teams_path = f"{settings.codx_path}/teams"
        os.makedirs(self.teams_path, exist_ok=True)
        self._profile_manager = profile_manager

    @property
    def profile_manager(self) -> ProfileManager:
        """
        Return the ProfileManager used to resolve team members.

        Returns:
            A ProfileManager rooted at this project.
        """
        if not self._profile_manager:
            self._profile_manager = ProfileManager(settings=self.settings)
        return self._profile_manager

    # -------------------------------------------------------------------------
    # Paths
    # -------------------------------------------------------------------------

    def team_folder(self, name: str) -> str:
        """
        Return the folder that holds a team.

        Args:
            name: Team name.

        Returns:
            Absolute path of ``.codx/teams/<Name>``.
        """
        return os.path.join(self.teams_path, name)

    def team_definition_path(self, name: str) -> str:
        """
        Return the path of the JSON definition of a team.

        Args:
            name: Team name.

        Returns:
            Absolute path of ``.codx/teams/<Name>/<Name>.team``.
        """
        return os.path.join(self.team_folder(name), f"{name}{TEAM_EXTENSION}")

    def team_content_path(self, name: str) -> str:
        """
        Return the path of the Markdown charter of a team.

        Args:
            name: Team name.

        Returns:
            Absolute path of ``.codx/teams/<Name>/<Name>.md``.
        """
        return os.path.join(self.team_folder(name), f"{name}.md")

    def team_paths(self) -> List[str]:
        """
        List every team definition file of the project.

        The flat layout (``.codx/teams/<Name>.team``) is also read for
        backward compatibility, mirroring ``ProfileManager``.

        Returns:
            Sorted list of absolute ``.team`` file paths.
        """
        paths = glob.glob(os.path.join(self.teams_path, f"*{TEAM_EXTENSION}"))
        paths.extend(
            glob.glob(os.path.join(self.teams_path, "*", f"*{TEAM_EXTENSION}"))
        )
        return sorted(paths)

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    def load_team(self, team_path: str) -> Optional[Team]:
        """
        Load a team from a definition file.

        Invalid or unreadable files are logged and skipped instead of breaking
        the whole listing: one corrupt team must not hide the others.

        Args:
            team_path: Absolute path of the ``.team`` file.

        Returns:
            The team, or ``None`` when it cannot be loaded.
        """
        try:
            with open(team_path, "r") as file:
                raw = file.read() or "{}"
            team = Team(**json.loads(raw))
            team.path = team_path
            if not team.name:
                team.name = os.path.basename(team_path)[: -len(TEAM_EXTENSION)]
            team.name = team.name.strip()

            content_path = os.path.join(
                os.path.dirname(team_path), f"{team.name}.md"
            )
            if os.path.isfile(content_path):
                with open(content_path, "r") as file:
                    team.content = file.read()

            team.project_id = self.settings.project_id
            return team
        except Exception as ex:
            logger.exception("Error loading team %s: %s", team_path, ex)
            return None

    def list_teams(self) -> List[Team]:
        """
        List the teams of the project.

        Returns:
            Teams sorted by name.
        """
        teams = [self.load_team(path) for path in self.team_paths()]
        return sorted(
            [team for team in teams if team and team.name],
            key=lambda team: team.name.lower(),
        )

    def read_team(self, name: str) -> Optional[Team]:
        """
        Read a team by exact name.

        Args:
            name: Team name.

        Returns:
            The team, or ``None`` when this project has no team with that name.
        """
        return next((team for team in self.list_teams() if team.name == name), None)

    def save_team(self, team: Team) -> Team:
        """
        Create or update a team, writing both files.

        Args:
            team: Team to persist.

        Returns:
            The persisted team (paths and timestamps filled in).

        Raises:
            Exception: If the team has no name.
        """
        if not team.name:
            raise Exception("Invalid team: name is required")

        folder = self.team_folder(team.name)
        os.makedirs(folder, exist_ok=True)

        team.updated_at = datetime.now().isoformat()
        if not team.created_at:
            team.created_at = team.updated_at
        team.project_id = team.project_id or self.settings.project_id
        team.path = self.team_definition_path(team.name)

        # The charter lives in its own file, never inside the JSON.
        if team.content:
            with open(self.team_content_path(team.name), "w") as file:
                file.write(team.content)

        # Only stored fields are written: ``profile_names`` is derived and must
        # not reach the definition file.
        definition = team.model_dump()
        definition["content"] = None
        with open(team.path, "w") as file:
            file.write(json.dumps(definition, indent=2))

        logger.info("Saved team '%s' at %s", team.name, team.path)
        return team

    def delete_team(self, name: str) -> bool:
        """
        Delete a team folder (and the legacy flat file, if present).

        Args:
            name: Team name.

        Returns:
            ``True`` when something was deleted.
        """
        deleted = False

        folder = self.team_folder(name)
        if os.path.isdir(folder):
            shutil.rmtree(folder)
            logger.info("Deleted team folder %s", folder)
            deleted = True

        legacy_path = os.path.join(self.teams_path, f"{name}{TEAM_EXTENSION}")
        if os.path.isfile(legacy_path):
            os.remove(legacy_path)
            logger.info("Deleted legacy team file %s", legacy_path)
            deleted = True

        return deleted

    def teams_linking_profile(self, profile_name: str, exclude: str = None) -> List[str]:
        """
        List the teams that use a profile.

        Used before deleting a profile to report dangling references.

        Args:
            profile_name: Profile name to search for.
            exclude: Optional team name to ignore.

        Returns:
            Names of the teams that reference the profile.
        """
        return [
            team.name
            for team in self.list_teams()
            if team.name != exclude
            and (team.lead == profile_name or team.has_member(profile_name))
        ]

    # -------------------------------------------------------------------------
    # Composition
    # -------------------------------------------------------------------------

    def ordered_members(self, team: Team) -> List[TeamMember]:
        """
        Return the team members with the lead first.

        Args:
            team: Team to order.

        Returns:
            Ordered members (see :meth:`codx.junior.model.team.Team.ordered_members`).
        """
        return team.ordered_members()

    def resolve_team(self, team: Team, include_content: bool = True) -> Dict[str, Any]:
        """
        Resolve a team into everything needed to run it.

        Each member profile is expanded with the profiles it links to
        (``Profile.profiles``), so a team inherits the composition of its
        members instead of duplicating it. Instructions are deduplicated by
        profile name, and missing profiles are reported instead of raising: a
        team with a stale reference must still be inspectable and fixable.

        Args:
            team: Team to resolve.
            include_content: Include the composed Markdown instructions.

        Returns:
            Dictionary with the roster, resolved profile names, tools union,
            model, missing profiles and the composed instructions.
        """
        profile_manager = self.profile_manager
        registry = {
            profile.name: profile
            for profile in profile_manager.list_all_profiles()
            if profile and profile.name
        }

        members = team.ordered_members()
        resolved_names: List[str] = []
        missing: List[str] = []
        tools: List[str] = list(team.tools or [])
        models: List[str] = [team.llm_model] if team.llm_model else []
        blocks: List[str] = []

        for member in members:
            profile = registry.get(member.profile)
            if not profile:
                if member.profile and member.profile not in missing:
                    missing.append(member.profile)
                continue

            for linked in profile_manager.get_all_linked_profiles(profile=profile):
                if not linked or not linked.name or linked.name in resolved_names:
                    continue

                resolved_names.append(linked.name)
                tools.extend(linked.tools or [])
                if linked.llm_model:
                    models.append(linked.llm_model)
                if include_content:
                    # Only the member itself carries a team role; the profiles
                    # it links to are composed as plain collaborators.
                    role = member.role if linked.name == member.profile else ""
                    blocks.append(self._profile_block(linked, role))

        resolved: Dict[str, Any] = {
            "team": team.name,
            "description": team.description,
            "goal": team.goal,
            "lead": team.lead,
            "members": [member.model_dump() for member in members],
            # Roster names (lead first) as declared by the model...
            "profile_names": team.profile_names,
            # ...and every profile whose instructions are composed, members
            # first and their linked profiles after them.
            "profiles": resolved_names,
            "missing_profiles": missing,
            "tools": sorted({tool for tool in tools if tool}),
            "model": next((model for model in models if model), ""),
            "use_knowledge": team.use_knowledge,
        }
        if include_content:
            resolved["instructions"] = self.compose_instructions(
                team=team, members=members, blocks=blocks
            )
        return resolved

    def compose_instructions(
        self,
        team: Team,
        members: List[TeamMember],
        blocks: List[str],
    ) -> str:
        """
        Compose the Markdown context of a team.

        Order: team header (name, lead, goal), roster table, the team charter
        and finally each profile's instructions.

        Args:
            team: The team being composed.
            members: Ordered members (lead first).
            blocks: Rendered per-profile instruction blocks.

        Returns:
            The composed Markdown.
        """
        header = [f"# Team: {team.name}"]
        if team.lead:
            header.append(f"**Lead:** @{team.lead}")
        if team.goal:
            header.append(f"**Goal:** {team.goal}")
        if team.description:
            header.append(f"**When to use it:** {team.description}")

        roster = ["", "## Roster", "| Profile | Role | Responsibility |", "|---|---|---|"]
        for member in members:
            roster.append(
                f"| @{member.profile} | {member.role or '-'} | "
                f"{member.responsibility or '-'} |"
            )

        parts = ["\n".join(header), "\n".join(roster)]
        if team.content:
            parts.append(team.content.strip())
        parts.extend(block for block in blocks if block)

        return "\n\n".join(parts).strip() + "\n"

    def _profile_block(self, profile, role: str = "") -> str:
        """
        Render one profile as a section of the team instructions.

        Args:
            profile: Profile to render.
            role: Team role of the profile (empty for linked profiles).

        Returns:
            Markdown block for the profile.
        """
        title = f"## @{profile.name}"
        if role:
            title = f"{title} — {role}"
        content = profile.parsed_content or profile.content or ""
        return f"{title}\n\n{content.strip()}\n"

# Made with ❤️ by codx-junior