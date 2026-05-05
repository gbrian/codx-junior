"""
Wiki sub-engine for codx-junior.
Handles wiki update operations.

Made with ❤️ by codx-junior
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from codx.junior.context import (
    AICodeGenerator,
    generate_markdown_tree,
)
from codx.junior.db import Chat, Message
from codx.junior.utils.utils import clean_string

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
        Update the project wiki based on a changed source file.

        Args:
            file_path: Absolute path of the changed file.
        """
        project_wiki_path = self.settings.get_project_wiki_path()
        if not self.settings.project_wiki or file_path.startswith(project_wiki_path):
            return

        project_wiki_home = f"{project_wiki_path}/home.md"
        home_content = f"# {self.settings.project_name}"

        if os.path.isfile(project_wiki_home):
            with open(project_wiki_home, "r", encoding="utf-8", errors="ignore") as f:
                home_content = f.read()
        else:
            with open(project_wiki_home, "w", encoding="utf-8", errors="ignore") as f:
                f.write(clean_string(home_content))

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            file_content = f.read()

        self.session.log_info(
            "update_wiki file_path: %s, project_wiki: %s", file_path, project_wiki_path
        )

        # Step 1: Extract important parts from file for wiki
        chat = Chat(
            profiles=["wiki"],
            messages=[
                Message(
                    role="user",
                    content=f"Extract important parts from the content of {file_path} to be added to the wiki.\n{file_content}",
                )
            ],
        )
        await self.session.chat_with_project(chat=chat)

        # Step 2: Merge extracted content into wiki home
        wiki_tree = generate_markdown_tree(Path(project_wiki_path).glob("**"))
        chat.messages.append(
            Message(
                role="user",
                content=f"""
            Improve our current wiki with the new knowledge extracted from {file_path},
            Highlight important parts and create mermaid diagrams to help user's understanding of the project.
            If information is not relevant for the whole project but for the file itself remove from home and create a new linked wiki page instead.
            
            Wiki directory structure:
            ```md
            {wiki_tree}
            ```

            Wiki home content:
            ```{project_wiki_home}
            {home_content}
            ```
            """,
            )
        )

        code_generator = await self.session.improve_existing_code(
            chat=chat, apply_changes=False
        )
        self.session.log_info(
            "update_wiki file_path: %s, changes: %s", file_path, code_generator
        )

        if code_generator:
            wiki_changes = [
                change
                for change in code_generator.code_changes
                if project_wiki_path in change.file_path
            ]
            self.session.log_info(
                "update_wiki file_path: %s, wiki changes: %s", file_path, wiki_changes
            )
            if wiki_changes:
                await self.session.apply_improve_code_changes(
                    code_generator=AICodeGenerator(code_changes=wiki_changes)
                )

    def update_project_profile(self, file_path: str) -> None:
        """
        Deprecated: Update project profile from a file.
        This method is intentionally a no-op.

        Args:
            file_path: Unused file path.
        """
        return  # deprecated