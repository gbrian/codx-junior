"""
Teams package.

Provides the :class:`Team` model and :class:`TeamManager` for persisting and
retrieving hybrid teams (AI profiles + human users) on a per-project basis.
"""

from codx.junior.teams.model import Team, TeamMembers
from codx.junior.teams.team_manager import TeamManager

__all__ = ["Team", "TeamMembers", "TeamManager"]

# Made with ❤️ by codx-junior