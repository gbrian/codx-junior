"""
Wiki sub-engine for codx-junior.
Handles wiki update operations.

Made with ❤️ by codx-junior
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codx.junior.engine.session import CODXJuniorSession

logger = logging.getLogger(__name__)


class WikiEngine:
    """
    Handles wiki-related file operations.

    ```mermaid
    flowchart TD
        WE[WikiEngine]
        WE --> process_wiki_changes
        WE --> update_wiki
        WE --> update_project_profile
    ```
    """

    def __init__(self, session: "CODXJuniorSession") -> None:
        """Initialize with a reference to the parent session."""
        self.session = session

    @property
    def settings(self):
        """Shortcut to session settings."""
        return self.session.settings

    async def process_wiki_changes(self) -> None:
        """
        Process pending wiki changes (placeholder, not yet implemented).
        """
        pass

    async def update_wiki(self, file_path: str) -> None:
        """
        Queue a debounced wiki update for a changed source file.

        The previous implementation ran an AI code-generation chat on every
        call. That made the wiki refresh continuously while editing and could
        rewrite unrelated pages. The change is now handed to the shared
        scheduler, which waits for a quiet period and updates only this file.

        Args:
            file_path: Absolute path of the changed file.
        """
        project_wiki_path = self.settings.get_project_wiki_path()
        if not self.settings.project_wiki or file_path.startswith(project_wiki_path):
            return
        from codx.junior.wiki.scheduler import schedule_wiki_update

        schedule_wiki_update(
            self.settings,
            files=[file_path],
            reason="engine-file-change",
        )

    def update_project_profile(self, file_path: str) -> None:
        """
        Deprecated: Update project profile from a file.
        This method is intentionally a no-op.

        Args:
            file_path: Unused file path.
        """
        return  # deprecated