"""
File sub-engine for codx-junior.
Handles all file system operations including reading, writing, diffing and profile application.

Made with ❤️ by codx-junior
"""

import logging
import os
import re
import subprocess

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Pattern, Tuple

import pathspec

from codx.junior.db import Chat, Message
from codx.junior.model.model import Profile
from codx.junior.project.project_discover import find_all_user_projects
from codx.junior.utils.utils import write_file

if TYPE_CHECKING:
    from codx.junior.engine.session import CODXJuniorSession

logger = logging.getLogger(__name__)

# Name of the gitignore file
GITIGNORE_FILE = ".gitignore"
# Name of the git directory to always skip
GIT_DIR = ".git"

# Upload constraints
DEFAULT_MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1 GB
DEFAULT_MAX_TOTAL_SIZE = 4 * DEFAULT_MAX_FILE_SIZE  # 4 GB


class GitIgnoreManager:
    """
    Efficiently checks whether files are git-ignored by pre-loading
    all .gitignore rules found within a directory tree.

    Instead of spawning one subprocess per file (git check-ignore),
    this class reads every .gitignore file once and performs all checks
    in memory using the `pathspec` library.

    Supports nested .gitignore files: each .gitignore applies to its
    own directory and all subdirectories, matching git's actual behaviour.

    Also correctly handles the case where a parent directory is ignored:
    any file or directory inside an ignored directory is also considered
    ignored, regardless of whether it matches a pattern directly.

    ```mermaid
    flowchart TD
        A[GitIgnoreManager created with root_path] --> B[scan_gitignore_files]
        B --> C{.gitignore found?}
        C -- Yes --> D[Parse rules with pathspec]
        C -- No --> E[No rules for that dir]
        D --> F[Store dir -> PathSpec mapping]
        F --> G[is_ignored called with abs_path]
        G --> H[Walk up from file to root]
        H --> I{PathSpec for dir?}
        I -- Yes --> J[Check relative path against PathSpec]
        J --> K{Matches?}
        K -- Yes --> L[Return True - is ignored]
        K -- No --> M[Continue up the tree]
        I -- No --> M
        M --> N[Check if dir itself is ignored]
        N -- Yes --> L
        N -- No --> O{Reached root?}
        O -- Yes --> P[Return False - not ignored]
        O -- No --> H
    ```
    """

    def __init__(self, root_path: str) -> None:
        """
        Initialize and pre-load all .gitignore rules under root_path.

        Args:
            root_path: Absolute path to the root directory to scan.
        """
        self.root_path: str = os.path.normpath(root_path)
        # Maps absolute directory path -> compiled PathSpec for that directory
        self._specs: Dict[str, pathspec.PathSpec] = {}
        # Cache of already-computed ignored directories to speed up child lookups
        self._ignored_dirs_cache: Dict[str, bool] = {}
        self._load_all_gitignore_files()

    def _load_all_gitignore_files(self) -> None:
        """
        Walk the directory tree once and load every .gitignore found.

        Each .gitignore is compiled into a PathSpec and stored keyed
        by the directory that contains it.
        """
        for dir_path, dirs, files in os.walk(self.root_path):
            # Skip .git internals entirely
            if GIT_DIR in dirs:
                dirs.remove(GIT_DIR)

            if GITIGNORE_FILE in files:
                gitignore_path = os.path.join(dir_path, GITIGNORE_FILE)
                spec = self._parse_gitignore(gitignore_path)
                if spec is not None:
                    self._specs[dir_path] = spec
                    logger.debug(
                        "Loaded .gitignore rules from %s", gitignore_path
                    )

        logger.debug(
            "GitIgnoreManager loaded %d .gitignore file(s) under %s",
            len(self._specs),
            self.root_path,
        )

    def _parse_gitignore(self, gitignore_path: str) -> Optional[pathspec.PathSpec]:
        """
        Parse a single .gitignore file into a PathSpec object.

        Args:
            gitignore_path: Absolute path to the .gitignore file.

        Returns:
            Compiled PathSpec, or None if the file cannot be read.
        """
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", lines)
        except OSError as ex:
            logger.warning("Could not read %s: %s", gitignore_path, ex)
            return None

    def _is_within_root(self, abs_path: str) -> bool:
        """
        Check whether abs_path is the root_path itself or a descendant of it.

        This guard prevents the recursive walk in _is_dir_ignored from
        climbing above root_path all the way to the filesystem root,
        which would cause infinite recursion since the base-case
        ``abs_dir_path == self.root_path`` would never be reached.

        Args:
            abs_path: Normalised absolute path to test.

        Returns:
            True if abs_path equals root_path or starts with root_path + os.sep.
        """
        return abs_path == self.root_path or abs_path.startswith(
            self.root_path + os.sep
        )

    def _is_dir_ignored(self, abs_dir_path: str) -> bool:
        """
        Check whether a directory itself is matched by any .gitignore rule,
        walking up to root_path. Results are cached to avoid redundant work
        when checking many children of the same directory.

        This is the key method that ensures children of ignored directories
        are also reported as ignored, even if they don't match any pattern
        directly.

        The recursion is bounded by two base cases:
        1. ``abs_dir_path == self.root_path`` – we have reached the root; never ignored.
        2. ``not self._is_within_root(abs_dir_path)`` – the path has escaped the root
           (e.g. the listed directory is outside the root); treat as not ignored and
           stop climbing to prevent infinite recursion toward the filesystem root.

        Args:
            abs_dir_path: Absolute path of the directory to check.

        Returns:
            True if the directory (or any of its ancestors up to root) is ignored.
        """
        # Already resolved - return cached result
        if abs_dir_path in self._ignored_dirs_cache:
            return self._ignored_dirs_cache[abs_dir_path]

        # Base case: the root itself is never ignored
        if abs_dir_path == self.root_path:
            self._ignored_dirs_cache[abs_dir_path] = False
            return False

        # Safety guard: if we have somehow walked above the root (e.g. the path
        # passed to is_ignored was outside the tree), stop recursion immediately.
        # Without this guard, dirname("/") == "/" causes infinite recursion.
        if not self._is_within_root(abs_dir_path):
            logger.debug(
                "Path is outside GitIgnoreManager root; treating as not ignored: %s",
                abs_dir_path,
            )
            self._ignored_dirs_cache[abs_dir_path] = False
            return False

        parent = os.path.dirname(abs_dir_path)

        # If the parent is ignored, so is this directory (cascade)
        if self._is_dir_ignored(parent):
            self._ignored_dirs_cache[abs_dir_path] = True
            return True

        # Check whether this directory matches any rule in its parent's scope
        # or any ancestor's scope (walk up from parent to root)
        current = parent
        while True:
            spec = self._specs.get(current)
            if spec is not None:
                try:
                    rel = os.path.relpath(abs_dir_path, current)
                except ValueError:
                    pass
                else:
                    if spec.match_file(rel):
                        self._ignored_dirs_cache[abs_dir_path] = True
                        return True

            if current == self.root_path:
                break

            ancestor = os.path.dirname(current)
            # Guard against infinite loop at filesystem root
            if ancestor == current:
                break
            current = ancestor

        self._ignored_dirs_cache[abs_dir_path] = False
        return False

    def is_ignored(self, abs_path: str) -> bool:
        """
        Check whether a file or directory is matched by any .gitignore rule.

        Handles two cases:
        1. The path itself matches a .gitignore pattern.
        2. The path lives inside a directory that is ignored (cascade).

        Walking up the directory tree from abs_path to root_path mirrors
        how git resolves ignore rules (nearest .gitignore wins, rules are
        cumulative). The additional parent-directory cascade check ensures
        that files inside ignored folders are correctly reported as ignored
        even if no pattern matches them directly.

        If abs_path is outside the root_path tree, this method returns False
        immediately since no rules from this root can apply to it.

        Args:
            abs_path: Absolute path of the file or directory to check.

        Returns:
            True if the path is ignored by any applicable .gitignore rule,
            or if any of its ancestor directories up to root_path is ignored.
        """
        abs_path = os.path.normpath(abs_path)
        parent_dir = os.path.dirname(abs_path)

        # If the path is entirely outside the root, no rules here apply to it.
        if not self._is_within_root(abs_path):
            logger.debug(
                "Path is outside GitIgnoreManager root; skipping ignore check: %s",
                abs_path,
            )
            return False

        # Fast path: if the containing directory is already known to be ignored,
        # every child is ignored too - no need to check patterns.
        if self._is_dir_ignored(parent_dir):
            logger.debug(
                "Path is inside an ignored directory, marking as ignored: %s", abs_path
            )
            return True

        # Walk up from the file's directory to root checking each .gitignore
        current_dir = parent_dir
        while True:
            spec = self._specs.get(current_dir)
            if spec is not None:
                try:
                    rel = os.path.relpath(abs_path, current_dir)
                except ValueError:
                    # Different drives on Windows - skip
                    pass
                else:
                    if spec.match_file(rel):
                        return True

            # Stop after we have checked the root
            if current_dir == self.root_path:
                break

            ancestor = os.path.dirname(current_dir)
            # Guard against infinite loop at filesystem root
            if ancestor == current_dir:
                break
            current_dir = ancestor

        return False


class FileEngine:
    """
    Handles file system operations for the project.

    ```mermaid
    flowchart TD
        FE[FileEngine]
        FE --> read_file
        FE --> write_project_file
        FE --> upload_file
        FE --> upload_files
        FE --> diff_file
        FE --> process_project_file_before_saving
        FE --> apply_file_profile
        FE --> get_valid_project_file_path
        FE --> search_files
        FE --> search_files_content
        FE --> get_file_info
        FE --> _build_gitignore_manager
    ```
    """

    def __init__(self, session: "CODXJuniorSession") -> None:
        """Initialize with a reference to the parent session."""
        self.session = session

    @property
    def settings(self):
        """Shortcut to session settings."""
        return self.session.settings

    def _build_gitignore_manager(self, search_root: str) -> GitIgnoreManager:
        """
        Build a GitIgnoreManager pre-loaded with all .gitignore rules
        found under search_root.

        Creating it once per search operation means we pay the cost of
        reading .gitignore files exactly once rather than once per file.

        Args:
            search_root: Absolute directory path to scan for .gitignore files.

        Returns:
            Ready-to-use GitIgnoreManager instance.
        """
        logger.debug("Building GitIgnoreManager for root: %s", search_root)
        return GitIgnoreManager(root_path=search_root)

    def _compile_regex_pattern(self, pattern: str, case_sensitive: bool = False) -> Optional[Pattern]:
        """
        Compile a regex pattern with error handling.

        Globally enables MULTILINE mode so that ^ and $ match line boundaries
        in addition to string boundaries. This allows patterns to work across
        multi-line content naturally.

        Args:
            pattern: Regex pattern string.
            case_sensitive: Whether to compile with IGNORECASE flag.

        Returns:
            Compiled regex pattern or None if compilation fails.

        Raises:
            ValueError: If regex pattern is invalid.
        """
        try:
            flags = re.MULTILINE
            if not case_sensitive:
                flags |= re.IGNORECASE
            return re.compile(pattern, flags)
        except re.error as ex:
            raise ValueError(f"Invalid regex pattern: {ex}")

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

    def parse_file_line(
        self,
        file: str,
        base_path: str,
        gitignore_manager: Optional[GitIgnoreManager] = None,
        parent_is_ignored: bool = False,
    ) -> dict:
        """
        Parse a file name into a structured dict for directory listings.

        The ``parent_is_ignored`` flag allows callers to propagate ignored
        status from a containing directory so that children of an ignored
        folder are correctly marked as ignored even when their own path
        does not match any .gitignore pattern directly.

        Args:
            file: Relative file name.
            base_path: Base directory path.
            gitignore_manager: Optional pre-loaded manager used to flag ignored entries.
            parent_is_ignored: When True, marks the entry as ignored regardless of
                               whether its path matches a .gitignore pattern directly.
                               Used to cascade ignored status from parent directories.

        Returns:
            Dict with name, file_path, is_dir, is_ignored, children,
            last_modification, and size.
        """
        file_path = os.path.join(base_path, file)
        if not file_path.startswith(self.settings.abs_project_path):
            file_path = f"{self.settings.abs_project_path}/{file_path}"
        is_dir = os.path.isdir(file_path)

        # A path is ignored if its parent is already ignored (cascade) OR if it
        # matches a .gitignore rule directly via the manager.
        if parent_is_ignored:
            is_ignored = True
        elif gitignore_manager is not None:
            is_ignored = gitignore_manager.is_ignored(file_path)
        else:
            is_ignored = False

        entry = {
            "name": file.split("/")[-1],
            "file_path": file_path,
            "is_dir": is_dir,
            "is_ignored": is_ignored,
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
        List the contents of a directory, flagging git-ignored entries.

        If the directory being listed is itself git-ignored, all of its
        children are also marked as ignored (cascade behaviour matching git).

        The GitIgnoreManager is rooted at the project root so that rules
        defined above the listed directory (e.g. a top-level .gitignore
        that ignores this folder) are taken into account.  When ``path``
        is outside the project root the manager will simply return
        ``is_ignored=False`` for every entry rather than raising an error.

        Args:
            path: Absolute path to the directory.

        Returns:
            Dict with path, full_path, is_ignored, and files list.
        """
        files = os.listdir(path)

        # Root the GitIgnoreManager at the project root so that rules defined
        # outside the listed directory (e.g. a top-level .gitignore that ignores
        # this folder) are still taken into account.
        project_root = self.settings.abs_project_path
        gitignore_manager = self._build_gitignore_manager(project_root)

        # Determine whether the directory being listed is itself ignored.
        # If so, every child inherits that status.
        dir_is_ignored = gitignore_manager.is_ignored(path)
        if dir_is_ignored:
            logger.debug(
                "Directory is git-ignored; all children will be marked ignored: %s",
                path,
            )

        return {
            "path": path,
            "full_path": path,
            "is_ignored": dir_is_ignored,
            "files": [
                self.parse_file_line(
                    file,
                    path,
                    gitignore_manager,
                    parent_is_ignored=dir_is_ignored,
                )
                for file in sorted(files)
            ],
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

    def diff_file(
        self,
        path: str,
        content: str,
        from_branch: str = None,
        to_branch: str = None,
    ) -> dict:
        """
        Diff a project file against provided content using git diff --no-index.

        Args:
            path: File path.
            content: New content to diff against.
            from_branch: Reserved for future use.
            to_branch: Reserved for future use.

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

    def get_valid_project_file_path(self, file_path: str) -> Tuple[str, any]:
        """
        Validate and resolve a file path within the user's allowed projects.

        Handles both absolute and relative paths:
        - Absolute paths: Must be within a user's project directory
        - Relative paths: Resolved within the current project root

        Prevents path traversal attacks using '..' sequences.

        Args:
            file_path: The path to validate (absolute or relative).

        Returns:
            Tuple of (absolute_path, project_settings).

        Raises:
            ValueError: If path is outside user projects or traversal is attempted.
        """
        norm_input_path = os.path.normpath(file_path.lstrip("/"))

        if os.path.isabs(file_path):
            return self._resolve_absolute_path(file_path)

        return self._resolve_relative_path(norm_input_path, file_path)

    def _resolve_absolute_path(self, file_path: str) -> Tuple[str, any]:
        """
        Resolve and validate an absolute file path against all allowed projects.

        Args:
            file_path: Absolute file path to validate.

        Returns:
            Tuple of (absolute_path, project_settings).

        Raises:
            ValueError: If path is outside all user projects.
        """
        abs_file_path = os.path.normpath(file_path)

        # Check current project first (fast path)
        try:
            rel_path = os.path.relpath(abs_file_path, self.settings.abs_project_path)
            if not rel_path.startswith(".."):
                return abs_file_path, self.settings
        except ValueError:
            pass

        # Fall back to checking all user projects
        for project in find_all_user_projects(self.session.user):
            try:
                rel_path = os.path.relpath(abs_file_path, project.abs_project_path)
                if not rel_path.startswith(".."):
                    return abs_file_path, project
            except ValueError:
                continue

        raise ValueError(
            "Access denied: absolute path is outside all allowed projects: %s"
            % abs_file_path
        )

    def _resolve_relative_path(
        self, norm_input_path: str, original_path: str
    ) -> Tuple[str, any]:
        """
        Resolve and validate a relative file path within the current project root.

        Args:
            norm_input_path: Normalised (lstripped) relative path.
            original_path: Original path string for error messages.

        Returns:
            Tuple of (absolute_path, project_settings).

        Raises:
            ValueError: If path escapes the project root.
        """
        new_abs_file_path = os.path.normpath(
            os.path.join(self.settings.abs_project_path, norm_input_path)
        )

        try:
            rel_path = os.path.relpath(
                new_abs_file_path, self.settings.abs_project_path
            )
            if rel_path.startswith(".."):
                raise ValueError(
                    "Access denied: path traversal outside project root: %s"
                    % original_path
                )
        except ValueError:
            raise ValueError(
                "Access denied: path is on different drive: %s" % original_path
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
            OSError: If writing fails.
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
        except OSError as ex:
            raise OSError("Error processing file %s:\n%s" % (abs_file_path, ex)) from ex

    async def upload_file(
        self,
        file_path: str,
        file_content: bytes,
        process: bool = False,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    ) -> dict:
        """
        Upload a single file to the project.

        Validates file size and path security before writing.
        Supports optional file profile application during upload.

        Args:
            file_path: Target file path (relative to project root).
            file_content: Raw file bytes to write.
            process: Whether to apply file profiles before writing.
            max_file_size: Maximum allowed file size in bytes.

        Returns:
            Dict with upload metadata including file path, size, and modification time.

        Raises:
            ValueError: If file size exceeds limit or path is invalid.
            OSError: If file write fails.
        """
        # Validate file size
        file_size = len(file_content)
        if file_size > max_file_size:
            raise ValueError(
                "File size %d exceeds maximum allowed size %d bytes"
                % (file_size, max_file_size)
            )

        # Validate and resolve file path
        abs_file_path, file_project = self.get_valid_project_file_path(file_path)

        try:
            # Create parent directories if needed
            os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)

            # Decode content if it's bytes and we need to process
            if isinstance(file_content, bytes):
                try:
                    content_str = file_content.decode("utf-8")
                except UnicodeDecodeError:
                    # For binary files, write as-is
                    logger.info("Writing binary file: %s", abs_file_path)
                    with open(abs_file_path, "wb") as f:
                        f.write(file_content)
                    info = self.get_file_info(abs_file_path)
                    return {
                        "file_project": file_project.project_name,
                        "file_project_path": file_project.abs_project_path,
                        "file_path": file_path,
                        "abs_file_path": abs_file_path,
                        "project_path": self.settings.abs_project_path,
                        "is_binary": True,
                        **info,
                    }
            else:
                content_str = file_content

            # Apply file profiles if requested (text files only)
            if process:
                content_str = await self.process_project_file_before_saving(
                    file_path=abs_file_path, content=content_str
                )

            write_file(file_path=abs_file_path, content=content_str)
            info = self.get_file_info(abs_file_path)
            return {
                "file_project": file_project.project_name,
                "file_project_path": file_project.abs_project_path,
                "file_path": file_path,
                "abs_file_path": abs_file_path,
                "project_path": self.settings.abs_project_path,
                "is_binary": False,
                **info,
            }
        except OSError as ex:
            logger.error("Error uploading file %s: %s", abs_file_path, ex)
            raise OSError("Error uploading file %s:\n%s" % (abs_file_path, ex)) from ex

    async def upload_files(
        self,
        file_uploads: List[Tuple[str, bytes]],
        process: bool = False,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        max_total_size: int = DEFAULT_MAX_TOTAL_SIZE,
    ) -> dict:
        """
        Upload multiple files to the project in batch.

        Validates total size across all files and individual file sizes.
        Supports optional file profile application during upload.
        Continues processing remaining files even if some fail.

        Args:
            file_uploads: List of (file_path, file_content) tuples.
            process: Whether to apply file profiles before writing.
            max_file_size: Maximum allowed size for individual files.
            max_total_size: Maximum allowed total size for all files combined.

        Returns:
            Dict with results containing:
            - successful: List of successfully uploaded files
            - failed: List of failed uploads with error details
            - total_files: Total number of files attempted
            - total_size_uploaded: Total size of successfully uploaded files
        """
        # Validate total size
        total_size = sum(len(content) for _, content in file_uploads)
        if total_size > max_total_size:
            raise ValueError(
                "Total upload size %d exceeds maximum allowed size %d bytes"
                % (total_size, max_total_size)
            )

        successful = []
        failed = []

        logger.info(
            "Starting batch upload of %d files (total size: %d bytes)",
            len(file_uploads),
            total_size,
        )

        for file_path, file_content in file_uploads:
            try:
                result = await self.upload_file(
                    file_path=file_path,
                    file_content=file_content,
                    process=process,
                    max_file_size=max_file_size,
                )
                successful.append(result)
                logger.info("Successfully uploaded file: %s", file_path)
            except (ValueError, OSError) as ex:
                error_msg = str(ex)
                failed.append({
                    "file_path": file_path,
                    "error": error_msg,
                })
                logger.warning(
                    "Failed to upload file %s: %s", file_path, error_msg
                )

        total_uploaded = sum(f.get("size", 0) or 0 for f in successful)

        result_dict = {
            "total_files": len(file_uploads),
            "successful": successful,
            "failed": failed,
            "total_size_uploaded": total_uploaded,
        }

        logger.info(
            "Batch upload completed: %d successful, %d failed",
            len(successful),
            len(failed),
        )

        return result_dict

    def search_files(
        self,
        search: str,
        search_path: str = None,
        page: int = 0,
        page_size: int = 50,
        raw_search: bool = False,
        use_regex: bool = False,
    ) -> dict:
        """
        Search for files whose paths contain the search pattern.

        Performs a filesystem search (not knowledge-based) within the project.
        Optionally limits search to a specific subdirectory.
        Supports both substring and regex pattern matching.

        When raw_search is False, files and directories matched by any
        .gitignore rule are excluded from results. All .gitignore files are
        loaded once before the walk for maximum performance.

        Each result entry includes an 'is_ignored' flag.  When raw_search is
        False ignored entries are filtered out; when True they are included
        with is_ignored=True so callers can still distinguish them.

        Args:
            search: Substring or regex pattern to search for in file paths.
            search_path: Optional subdirectory path (relative to project root).
            page: Page number (0-indexed, default 0).
            page_size: Number of results per page (default 50).
            raw_search: If True, include all files. If False, exclude git-ignored files.
            use_regex: If True, treat search as regex pattern. If False, use substring match.

        Returns:
            Dict with page info, total_files count, and paginated files list.
            Includes 'error' field if an error occurs during search.
        """
        try:
            search_root = self._resolve_search_root(search_path)
            if search_root is None:
                return {"page": page, "total_files": 0, "page_size": page_size, "files": []}

            # Compile regex if needed
            compiled_pattern = None
            if use_regex:
                try:
                    compiled_pattern = self._compile_regex_pattern(search, case_sensitive=False)
                except ValueError as ex:
                    logger.warning("Invalid regex pattern: %s", ex)
                    return {
                        "page": page,
                        "total_files": 0,
                        "page_size": page_size,
                        "files": [],
                        "error": str(ex),
                    }

            # Build the ignore manager once - O(dirs) cost instead of O(files)
            gitignore_manager = self._build_gitignore_manager(search_root)

            matching_files = []

            for root, dirs, files in os.walk(search_root):
                # Always skip the .git bookkeeping directory
                if GIT_DIR in dirs:
                    dirs.remove(GIT_DIR)

                if not raw_search:
                    # Prune ignored directories in-place so os.walk skips their subtrees
                    dirs[:] = [
                        d for d in dirs
                        if not gitignore_manager.is_ignored(os.path.join(root, d))
                    ]

                for file in files:
                    file_path = os.path.join(root, file)
                    is_ignored = gitignore_manager.is_ignored(file_path)

                    # Discard ignored files when not in raw mode
                    if not raw_search and is_ignored:
                        logger.debug("Skipping git-ignored file: %s", file_path)
                        continue

                    try:
                        rel_path = os.path.relpath(
                            file_path, self.settings.abs_project_path
                        )
                    except ValueError:
                        continue

                    # Match using regex or substring
                    matches = False
                    if use_regex:
                        matches = compiled_pattern.search(rel_path) is not None
                    else:
                        matches = search.lower() in rel_path.lower()

                    if matches:
                        entry = self.parse_file_line(
                            rel_path,
                            self.settings.abs_project_path,
                            gitignore_manager,
                        )
                        matching_files.append(entry)

            matching_files.sort(key=lambda x: x["file_path"])

            total_files = len(matching_files)
            page_start = page * page_size
            page_end = page_start + page_size

            return {
                "page": page,
                "total_files": total_files,
                "page_size": page_size,
                "files": matching_files[page_start:page_end],
            }
        except Exception as ex:
            error_msg = str(ex)
            logger.error("Error during file search: %s", error_msg)
            return {
                "page": page,
                "total_files": 0,
                "page_size": page_size,
                "files": [],
                "error": error_msg,
            }

    def search_files_content(
        self,
        query: str,
        search_path: str = None,
        page: int = 0,
        page_size: int = 50,
        case_sensitive: bool = False,
        raw_search: bool = False,
        use_regex: bool = False,
    ) -> dict:
        """
        Search for file content matching a query pattern.

        Searches file contents within the project scope with pagination support.
        search_path can be a directory or a file:
        - If a directory: searches all files within that directory tree
        - If a file: searches only that single file
        When raw_search is False, git-ignored files are excluded. All .gitignore
        files are loaded once before the walk for maximum performance.
        Supports both substring and regex pattern matching.

        Args:
            query: Substring or regex pattern to search for in file contents.
            search_path: Optional directory or file path (relative to project root).
            page: Page number (0-indexed, default 0).
            page_size: Number of results per page (default 50).
            case_sensitive: Whether search should be case-sensitive (default False).
            raw_search: If True, include all files. If False, exclude git-ignored files.
            use_regex: If True, treat query as regex pattern. If False, use substring match.

        Returns:
            Dict with page info, total_files, total_matches, and paginated results.
            Each result includes an 'is_ignored' flag.
            Includes 'error' field if an error occurs during search.
        """
        try:
            search_info = self._resolve_search_root(search_path)
            if search_info is None:
                return {
                    "page": page,
                    "total_files": 0,
                    "total_matches": 0,
                    "page_size": page_size,
                    "results": [],
                }

            # Check if search_info is a file (single file search mode)
            is_single_file_search = os.path.isfile(search_info)

            # Compile regex if needed
            compiled_pattern = None
            if use_regex:
                try:
                    compiled_pattern = self._compile_regex_pattern(query, case_sensitive=case_sensitive)
                except ValueError as ex:
                    logger.warning("Invalid regex pattern: %s", ex)
                    return {
                        "page": page,
                        "total_files": 0,
                        "total_matches": 0,
                        "page_size": page_size,
                        "results": [],
                        "error": str(ex),
                    }

            search_pattern = query if case_sensitive else query.lower()
            matching_results = []

            if is_single_file_search:
                # Single file search mode
                logger.debug("Single file search mode for: %s", search_info)
                try:
                    rel_path = os.path.relpath(
                        search_info, self.settings.abs_project_path
                    )
                except ValueError:
                    return {
                        "page": page,
                        "total_files": 0,
                        "total_matches": 0,
                        "page_size": page_size,
                        "results": [],
                        "error": "File path is outside project root",
                    }

                # Build ignore manager for the project root
                gitignore_manager = self._build_gitignore_manager(self.settings.abs_project_path)
                is_ignored = gitignore_manager.is_ignored(search_info)

                # Discard ignored files when not in raw mode
                if not raw_search and is_ignored:
                    logger.debug(
                        "File is git-ignored, skipping: %s", search_info
                    )
                    return {
                        "page": page,
                        "total_files": 0,
                        "total_matches": 0,
                        "page_size": page_size,
                        "results": [],
                    }

                result = self._search_in_file(
                    file_path=search_info,
                    rel_path=rel_path,
                    search_pattern=search_pattern,
                    compiled_pattern=compiled_pattern,
                    case_sensitive=case_sensitive,
                    use_regex=use_regex,
                    is_ignored=is_ignored,
                )
                if result is not None:
                    matching_results.append(result)
            else:
                # Directory search mode
                logger.debug("Directory search mode for: %s", search_info)
                # Build the ignore manager once - O(dirs) cost instead of O(files)
                gitignore_manager = self._build_gitignore_manager(search_info)

                for root, dirs, files in os.walk(search_info):
                    # Always skip the .git bookkeeping directory
                    if GIT_DIR in dirs:
                        dirs.remove(GIT_DIR)

                    if not raw_search:
                        # Prune ignored directories in-place so os.walk skips their subtrees
                        dirs[:] = [
                            d for d in dirs
                            if not gitignore_manager.is_ignored(os.path.join(root, d))
                        ]

                    for file in files:
                        file_path = os.path.join(root, file)
                        is_ignored = gitignore_manager.is_ignored(file_path)

                        # Discard ignored files when not in raw mode
                        if not raw_search and is_ignored:
                            logger.debug(
                                "Skipping git-ignored file in content search: %s", file_path
                            )
                            continue

                        try:
                            rel_path = os.path.relpath(
                                file_path, self.settings.abs_project_path
                            )
                        except ValueError:
                            continue

                        result = self._search_in_file(
                            file_path=file_path,
                            rel_path=rel_path,
                            search_pattern=search_pattern,
                            compiled_pattern=compiled_pattern,
                            case_sensitive=case_sensitive,
                            use_regex=use_regex,
                            is_ignored=is_ignored,
                        )
                        if result is not None:
                            matching_results.append(result)

            matching_results.sort(key=lambda x: (-x["match_count"], x["rel_path"]))

            total_files = len(matching_results)
            total_matches = sum(r["match_count"] for r in matching_results)
            page_start = page * page_size
            page_end = page_start + page_size

            return {
                "page": page,
                "total_files": total_files,
                "total_matches": total_matches,
                "page_size": page_size,
                "results": matching_results[page_start:page_end],
            }
        except Exception as ex:
            error_msg = str(ex)
            logger.error("Error during content search: %s", error_msg)
            return {
                "page": page,
                "total_files": 0,
                "total_matches": 0,
                "page_size": page_size,
                "results": [],
                "error": error_msg,
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_search_root(self, search_path: Optional[str]) -> Optional[str]:
        """
        Resolve the root directory or file for a search operation.

        Args:
            search_path: Optional relative path (file or directory); None means project root.

        Returns:
            Absolute path (directory or file), or None if path doesn't exist.
        """
        if search_path:
            search_root = self.get_project_file_path(search_path)
            # Accept both files and directories
            if not os.path.exists(search_root):
                logger.warning("search_path does not exist: %s", search_root)
                return None
            # If it's a file, return the file path; if it's a directory, return the directory path
            return search_root
        return self.settings.abs_project_path

    def _search_in_file(
        self,
        file_path: str,
        rel_path: str,
        search_pattern: str,
        compiled_pattern: Optional[Pattern] = None,
        case_sensitive: bool = False,
        use_regex: bool = False,
        is_ignored: bool = False,
    ) -> Optional[dict]:
        """
        Search for a pattern inside a single file and return match metadata.

        Args:
            file_path: Absolute path to the file.
            rel_path: Path relative to the project root (used in results).
            search_pattern: Pre-lowercased (or not) substring pattern to look for.
            compiled_pattern: Pre-compiled regex pattern or None.
            case_sensitive: Whether the search is case-sensitive.
            use_regex: Whether to use regex matching.
            is_ignored: Whether the file is git-ignored (carried into result).

        Returns:
            Result dict if matches were found, None otherwise.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError as ex:
            logger.debug("Could not read file %s: %s", file_path, ex)
            return None

        matches = []

        if use_regex:
            # Regex search
            for line_num, line in enumerate(content.split("\n"), 1):
                match_objs = list(compiled_pattern.finditer(line))
                if match_objs:
                    matches.append({
                        "line_number": line_num,
                        "line_content": line.strip(),
                        "match_count": len(match_objs),
                    })
        else:
            # Substring search
            search_content = content if case_sensitive else content.lower()
            if search_pattern not in search_content:
                return None

            for line_num, line in enumerate(content.split("\n"), 1):
                line_search = line if case_sensitive else line.lower()
                if search_pattern in line_search:
                    matches.append({
                        "line_number": line_num,
                        "line_content": line.strip(),
                        "match_count": line_search.count(search_pattern),
                    })

        if not matches:
            return None

        file_info = self.get_file_info(file_path)
        return {
            "file_path": file_path,
            "rel_path": rel_path,
            "match_count": len(matches),
            "matches": matches,
            "is_ignored": is_ignored,
            **file_info,
        }

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


# Made with ❤️ by codx-junior