"""
File sub-engine for codx-junior.
Handles all file system operations including reading, writing, diffing and profile application.

Made with ❤️ by codx-junior
"""

import logging
import os
import subprocess

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from codx.junior.db import Chat, Message
from codx.junior.model.model import Profile
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.project.project_discover import find_all_user_projects
from codx.junior.utils.utils import write_file

if TYPE_CHECKING:
    from codx.junior.engine.session import CODXJuniorSession

logger = logging.getLogger(__name__)


class FileEngine:
    """
    Handles file system operations for the project.

    ```mermaid
    flowchart TD
        FE[FileEngine]
        FE --> read_file
        FE --> write_project_file
        FE --> diff_file
        FE --> process_project_file_before_saving
        FE --> apply_file_profile
        FE --> get_valid_project_file_path
        FE --> search_files
        FE --> get_file_info
    ```
    """

    def __init__(self, session: "CODXJuniorSession") -> None:
        """Initialize with a reference to the parent session."""
        self.session = session

    @property
    def settings(self):
        """Shortcut to session settings."""
        return self.session.settings

    def get_file_info(self, file_path: str) -> dict:
        """
        Return metadata for a file: last_modification (ISO 8601) and size in bytes.

        Args:
            file_path: Absolute or relative (to project root) path to the file.

        Returns:
            Dict with 'last_modification' (str or None) and 'size' (int or None).
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.settings.abs_project_path, file_path)
        if not os.path.isfile(file_path):
            return {"last_modification": None, "size": None}
        stat = os.stat(file_path)
        return {
            "last_modification": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": stat.st_size,
        }

    def parse_file_line(self, file: str, base_path: str) -> dict:
        """
        Parse a file name into a structured dict for directory listings.

        Args:
            file: Relative file name.
            base_path: Base directory path.

        Returns:
            Dict with name, file_path, is_dir, children, last_modification, and size.
        """
        file_path = os.path.join(base_path, file)
        if not file_path.startswith(self.settings.abs_project_path):
            file_path = f"{self.settings.abs_project_path}/{file_path}"
        is_dir = os.path.isdir(file_path)
        entry = {
            "name": file.split("/")[-1],
            "file_path": file_path,
            "is_dir": is_dir,
            "children": [] if is_dir else None,
        }
        if not is_dir:
            entry.update(self.get_file_info(file_path))
        else:
            entry["last_modification"] = None
            entry["size"] = None
        return entry

    def read_directory(self, path: str) -> dict:
        """
        List the contents of a directory.

        Args:
            path: Absolute path to the directory.

        Returns:
            Dict with path, full_path, and files list.
        """
        files = os.listdir(path)
        return {
            "path": path,
            "full_path": path,
            "files": [self.parse_file_line(file, path) for file in sorted(files)],
        }

    def get_project_file_path(self, path: str) -> str:
        """
        Resolve a (possibly relative) path to an absolute project path.

        Args:
            path: Possibly relative file path.

        Returns:
            Absolute file path.
        """
        abs_file_path, _ = self.get_valid_project_file_path(file_path=path)
        return abs_file_path

    def read_file(self, path: str) -> dict:
        """
        Read a project file and return its content along with file metadata.

        Args:
            path: File path (relative or absolute).

        Returns:
            Dict with 'content', 'last_modification', and 'size'.
        """
        path = self.get_project_file_path(path=path)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        info = self.get_file_info(path)
        return {
            "content": content,
            **info,
        }

    def diff_file(self, path: str, content: str, from_branch: str = None, to_branch: str = None) -> dict:
        """
        Diff a project file against provided content using git diff --no-index.

        Args:
            path: File path.
            content: New content to diff against.

        Returns:
            Dict with 'diff', 'stats', 'last_modification', and 'size'.
        """
        path = self.get_project_file_path(path=path)

        cmd = ["git", "diff", "--no-index", path, "-"]
        result = subprocess.run(cmd, input=content, text=True, capture_output=True)
        diff_out = result.stdout

        git_command = f"""
        cat << EOF | git --no-pager diff --shortstat --no-index -- - {path}
        {content}
        EOF
        """
        diff_stats_out = os.popen(git_command).read()

        info = self.get_file_info(path)
        return {
            "diff": diff_out.strip(),
            "stats": diff_stats_out.strip(),
            **info,
        }

    def diff_file_comments(
        self, path: str, content: str, comments: dict = None
    ) -> None:
        """
        Diff a file with inline comments (placeholder, not yet implemented).

        Args:
            path: File path.
            content: File content.
            comments: Optional dict of inline comments.
        """
        pass

    async def process_project_file_before_saving(
        self, file_path: str, content: str
    ) -> str:
        """
        Apply all matching file profiles to content before saving.

        Args:
            file_path: Absolute file path.
            content: File content to process.

        Returns:
            Processed file content.
        """
        file_profiles = self.session.get_profile_manager().get_file_profiles_by_file_path(
            file_path=file_path
        )
        self.session.log_info(
            "Applying file profiles %s to %s",
            [p.name for p in file_profiles],
            file_path,
        )
        if file_profiles:
            for profile in file_profiles:
                content = await self.apply_file_profile(
                    file_path=file_path, content=content, profile=profile
                )
        return content

    async def apply_file_profile(
        self, file_path: str, content: str, profile: Profile
    ) -> str:
        """
        Apply a single file profile to content using AI.

        Args:
            file_path: File path for context.
            content: Current file content.
            profile: Profile with instructions to apply.

        Returns:
            Improved file content.
        """
        file_profile_prompt = f"""
        You are given a section of code that requires improvement by applying best practices. Your task is to refactor the code while ensuring that it adheres to the specified best practices. Please follow the instructions below:

        ### File Content:
        ```
        {content}
        ```

        ### Instructions:
        ```
        {profile.content}
        ```
        Return the final content without any kind of decoration or extra comments. 
        Avoid surronding your response with fences (```), just return the final content.
        """

        content_message = Message(role="user", content=file_profile_prompt)
        chat = Chat(
            name=f"Improve file with profile {profile.name}", messages=[content_message]
        )
        await self.session.chat_with_project(chat=chat, disable_knowledge=True)
        return chat.messages[-1].content

    def get_valid_project_file_path(self, file_path: str) -> tuple:
        """
        Validate and resolve a file path within the user's allowed projects.

        Args:
            file_path: The path to validate.

        Returns:
            Tuple of (absolute_path, project_settings).

        Raises:
            Exception: If the file is outside any user project.
        """
        # Check all user projects first
        for project in find_all_user_projects(self.session.user):
            if file_path.startswith(project.abs_project_path):
                return file_path, project

        # Reject files outside all user projects that actually exist
        if os.path.exists(file_path) and not file_path.startswith(
            self.settings.abs_project_path
        ):
            raise Exception(
                f"Can't work with files outside user's projects: {os.path.abspath(file_path)}"
            )

        # Resolve relative paths into the current project
        norm_file_path = os.path.normpath(file_path.lstrip("/"))
        new_abs_file_path = os.path.normpath(
            os.path.join(self.settings.abs_project_path, norm_file_path)
        )
        return new_abs_file_path, self.settings

    async def write_project_file(
        self, file_path: str, content: str, process: bool = True
    ) -> dict:
        """
        Write content to a project file, optionally processing through file profiles.

        Args:
            file_path: Target file path.
            content: Content to write.
            process: Whether to run file profiles before writing.

        Returns:
            Dict with file and project metadata including last_modification and size.

        Raises:
            Exception: If writing fails.
        """
        abs_file_path, file_project = self.get_valid_project_file_path(file_path)
        try:
            os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)

            if process:
                content = await self.process_project_file_before_saving(
                    file_path=abs_file_path, content=content
                )

            write_file(file_path=abs_file_path, content=content)
            info = self.get_file_info(abs_file_path)
            return {
                "file_project": file_project.project_name,
                "file_project_path": file_project.abs_project_path,
                "file_path": file_path,
                "abs_file_path": abs_file_path,
                "project_path": self.settings.abs_project_path,
                **info,
            }
        except Exception as ex:
            raise Exception(f"Error processing file {abs_file_path}:\n{ex}") from ex

    def search_files(self, search: str) -> list:
        """
        Search for files whose paths contain the search string.

        Args:
            search: Substring to search for.

        Returns:
            List of matching file dicts including last_modification and size.
        """
        sources = self.session.get_knowledge().get_all_sources()
        matching = [s for s in sources if search in s]
        base_path = self.settings.abs_project_path
        return [self.parse_file_line(file, base_path) for file in sorted(matching)]

    def get_wiki_file(self, file_path: str) -> dict:
        """
        Read a wiki file and return its content along with file metadata.

        Args:
            file_path: Relative path within the wiki directory.

        Returns:
            Dict with 'content', 'last_modification', and 'size', or a 'not found' message dict.
        """
        project_wiki_path = self.settings.get_project_wiki_path()
        if project_wiki_path:
            if project_wiki_path[-1] != "/" and file_path[0] != "/":
                file_path = f"/{file_path}"
            wiki_file = f"{project_wiki_path}{file_path}"
            try:
                logger.info("Reading wiki file: %s", wiki_file)
                with open(wiki_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                info = self.get_file_info(wiki_file)
                return {"content": content, **info}
            except OSError:
                pass
        return {"content": f"> {file_path} not found", "last_modification": None, "size": None}

    def get_readme(self) -> dict:
        """
        Read the project README.md and return its content along with file metadata.

        Returns:
            Dict with 'content', 'last_modification', and 'size'.
        """
        readme_file = os.path.join(self.settings.abs_project_path, "README.md")
        if os.path.isfile(readme_file):
            with open(readme_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            info = self.get_file_info(readme_file)
            return {"content": content, **info}
        return {"content": "", "last_modification": None, "size": None}

    def api_image_to_text(self, image_bytes: bytes) -> str:
        """
        Convert image bytes to text using OCR (pytesseract).

        Args:
            image_bytes: Raw image bytes.

        Returns:
            Extracted text string.
        """
        from PIL import Image
        import pytesseract
        import io

        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text