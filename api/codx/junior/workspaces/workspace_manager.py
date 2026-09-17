"""
WorkspaceManager — project-scoped workspace persistence.

Workspaces are stored as JSON files inside the project's .codx directory:

    workspaces/<workspace_id>/<workspace_id>.workspace
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone

from codx.junior.settings import CODXJuniorSettings
from codx.junior.workspaces.model import Workspace

if TYPE_CHECKING:
    # Import only for type hints, not at runtime
    from codx.junior.api.workspace_models import WorkspaceFileWriteRequest

logger = logging.getLogger(__name__)

WORKSPACES_DIR = "workspaces"
WORKSPACE_FILE_EXTENSION = ".workspace"


class WorkspaceManager:
    """
    Manages workspace persistence for a given project.

    Workspaces are stored as individual JSON files in:
        workspaces/<workspace_id>/<workspace_id>.workspace

    Workspace folders are:
        workspaces/<workspace_id>/
    """

    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.workspaces_path = os.path.join(settings.codx_path, WORKSPACES_DIR)
        os.makedirs(self.workspaces_path, exist_ok=True)
        logger.debug("WorkspaceManager initialized at '%s'", self.workspaces_path)

    # -------------------------------------------------------------------------
    # Path helpers
    # -------------------------------------------------------------------------

    def _workspace_folder_path(self, workspace_id: str) -> str:
        """Build the folder path for workspace content/config files."""
        return os.path.join(self.workspaces_path, workspace_id)

    def _workspace_file_path(self, workspace_id: str) -> str:
        """Build the file path for a workspace metadata file (inside its folder)."""
        # CHANGED: file lives inside the workspace subfolder, not at root level
        return os.path.join(self._workspace_folder_path(workspace_id), f"{workspace_id}{WORKSPACE_FILE_EXTENSION}")

    def _workspace_file_paths(self) -> List[str]:
        """Return all .workspace file paths for this project."""
        return [
            str(f)
            for f in Path(self.workspaces_path).glob(f"*/*{WORKSPACE_FILE_EXTENSION}")
            if f.is_file()
        ]

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    def list_workspaces(self) -> List[Workspace]:
        """Return all workspaces for this project."""
        workspaces = []
        for file_path in self._workspace_file_paths():
            workspace = self._load_workspace_from_file(file_path)
            if workspace:
                workspaces.append(workspace)
        return sorted(workspaces, key=lambda w: w.name.lower())

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Return a single workspace by id, or None if not found."""
        file_path = self._workspace_file_path(workspace_id)
        if os.path.isfile(file_path):
            return self._load_workspace_from_file(file_path)
        # Fallback: scan all files (covers edge cases where id differs)
        return next((w for w in self.list_workspaces() if w.id == workspace_id), None)

    def save_workspace(
        self,
        workspace: Workspace,
    ) -> Workspace:
        """
        Create or update a workspace.

        Assigns a new id when the workspace has none. Optionally generates
        docker-compose and other config files using AI.

        Args:
            workspace: Workspace object to save.
                           
        Returns:
            The saved workspace object.
        """
        if not workspace.id:
            workspace.id = str(uuid4())
        workspace.updated_at = datetime.now(timezone.utc).isoformat()

        # Ensure workspace folder exists
        workspace_folder = self._workspace_folder_path(workspace.id)
        os.makedirs(workspace_folder, exist_ok=True)

        # Save workspace metadata inside its folder
        file_path = self._workspace_file_path(workspace.id)
        logger.info("Saving workspace '%s' to '%s'", workspace.name, file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(workspace.model_dump(), indent=2))

        if workspace.generate_files:
            # CHANGED: use asyncio.create_task to schedule in current event loop
            # instead of threading. This preserves async context throughout.
            try:
                asyncio.create_task(self._generate_workspace_files_async(workspace, workspace_folder))
                logger.info("Scheduled async file generation for workspace '%s'", workspace.name)
            except RuntimeError:
                # If no running event loop (e.g., called from sync context),
                # fall back to background thread execution
                logger.info(
                    "No running event loop. Starting file generation in background thread for workspace '%s'",
                    workspace.name
                )
                self._generate_workspace_files_sync(workspace, workspace_folder)

        return workspace

    def delete_workspace(self, workspace_id: str) -> None:
        """
        Remove a workspace file and its associated folder from disk.
        
        Args:
            workspace_id: The workspace ID to delete.
        """
        file_path = self._workspace_file_path(workspace_id)
        workspace_folder = self._workspace_folder_path(workspace_id)
        
        # Delete workspace metadata file
        if os.path.isfile(file_path):
            os.remove(file_path)
            logger.info("Deleted workspace metadata file '%s'", workspace_id)
        
        # Delete workspace folder and all contents
        if os.path.isdir(workspace_folder):
            import shutil
            shutil.rmtree(workspace_folder)
            logger.info("Deleted workspace folder '%s'", workspace_folder)
        
        if not os.path.isfile(file_path) and not os.path.isdir(workspace_folder):
            logger.info("Workspace '%s' fully removed", workspace_id)
        else:
            logger.warning("Workspace '%s' partially removed", workspace_id)

    # -------------------------------------------------------------------------
    # File operations (read/write files within workspace folder)
    # -------------------------------------------------------------------------

    def read_workspace_file(self, workspace_id: str, file_path: str) -> str:
        """
        Read a file from within a workspace folder.
        
        Args:
            workspace_id: The workspace ID
            file_path: Relative path within workspace folder (e.g., "docker-compose.yaml")
        
        Returns:
            File content as string
        
        Raises:
            FileNotFoundError if workspace or file doesn't exist
            ValueError if path traversal attempted
        """
        workspace_folder = self._get_workspace_folder_path(workspace_id)
        
        # Prevent path traversal
        requested_path = os.path.normpath(os.path.join(workspace_folder, file_path))
        if not requested_path.startswith(workspace_folder):
            raise ValueError(f"Path traversal not allowed: {file_path}")
        
        if not os.path.isfile(requested_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(requested_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info("Read file from workspace %s: %s", workspace_id, file_path)
            return content
        except Exception as e:
            logger.exception("Error reading file %s: %s", file_path, e)
            raise

    def write_workspace_file(self, workspace_id: str, file_path: str, content: str) -> None:
        """
        Write a file to within a workspace folder.
        
        Args:
            workspace_id: The workspace ID
            file_path: Relative path within workspace folder (e.g., "docker-compose.yaml")
            content: File content to write
        
        Raises:
            FileNotFoundError if workspace doesn't exist
            ValueError if path traversal attempted
        """
        workspace_folder = self._get_workspace_folder_path(workspace_id)
        
        # Prevent path traversal
        requested_path = os.path.normpath(os.path.join(workspace_folder, file_path))
        if not requested_path.startswith(workspace_folder):
            raise ValueError(f"Path traversal not allowed: {file_path}")
        
        # Create parent directories if needed
        os.makedirs(os.path.dirname(requested_path), exist_ok=True)
        
        try:
            with open(requested_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("Wrote file to workspace %s: %s", workspace_id, file_path)
        except Exception as e:
            logger.exception("Error writing file %s: %s", file_path, e)
            raise

    def list_workspace_files(self, workspace_id: str, relative_path: str = "") -> dict:
        """
        List files and folders within a workspace folder.
        
        Args:
            workspace_id: The workspace ID
            relative_path: Relative path within workspace (empty for root)
        
        Returns:
            Dict with 'files' (list of file names) and 'folders' (list of folder names)
        
        Raises:
            FileNotFoundError if workspace doesn't exist
            ValueError if path traversal attempted
        """
        workspace_folder = self._get_workspace_folder_path(workspace_id)
        
        # Prevent path traversal
        target_path = os.path.normpath(os.path.join(workspace_folder, relative_path))
        if not target_path.startswith(workspace_folder):
            raise ValueError(f"Path traversal not allowed: {relative_path}")
        
        if not os.path.isdir(target_path):
            raise FileNotFoundError(f"Path not found: {relative_path}")
        
        files = []
        folders = []
        
        try:
            for entry in os.listdir(target_path):
                entry_path = os.path.join(target_path, entry)
                if os.path.isdir(entry_path):
                    folders.append(entry)
                else:
                    files.append(entry)
            
            logger.info(
                "Listed %d files, %d folders in workspace %s: %s",
                len(files),
                len(folders),
                workspace_id,
                relative_path
            )
            return {"files": sorted(files), "folders": sorted(folders)}
        except Exception as e:
            logger.exception("Error listing files in %s: %s", relative_path, e)
            raise

    # -------------------------------------------------------------------------
    # AI-powered file generation (async-first approach)
    # -------------------------------------------------------------------------

    async def _generate_workspace_files_async(
        self,
        workspace: Workspace,
        workspace_folder: str
    ) -> None:
        """
        Asynchronously generate Docker and config files for a workspace using AI.

        Uses the event loop's native async/await paradigm. No threads, no
        blocking, no nested event loops.

        Args:
            workspace: Workspace object with apps and config.
            workspace_folder: Target folder where files will be saved.
        """
        # CHANGED: Full async implementation using await, no threading
        from codx.junior.workspaces.workspace_file_generator import WorkspaceFileGenerator

        try:
            generator = WorkspaceFileGenerator(settings=self.settings)
            logger.info(
                "Generating workspace files for '%s' in '%s'",
                workspace.name,
                workspace_folder,
            )
            generated_files = await generator.generate_all_files(workspace, workspace_folder)
            logger.info(
                "Successfully generated %d files for workspace '%s'",
                len(generated_files),
                workspace.name,
            )
        except Exception as ex:
            logger.warning(
                "Failed to generate workspace files for '%s': %s. "
                "Workspace created but without Docker/config files.",
                workspace.name,
                ex,
            )

    def _generate_workspace_files_sync(
        self,
        workspace: Workspace,
        workspace_folder: str
    ) -> None:
        """
        Fallback synchronous generation for when called from non-async context.

        Runs the async generator in a new event loop (background thread).
        This preserves backward compatibility for sync callers.

        Args:
            workspace: Workspace object with apps and config.
            workspace_folder: Target folder where files will be saved.
        """
        import threading

        def _run_in_thread():
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self._generate_workspace_files_async(workspace, workspace_folder)
                )
            finally:
                loop.close()

        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()
        logger.info("Started background file generation thread for workspace '%s'", workspace.name)

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _get_workspace_folder_path(self, workspace_id: str) -> str:
        """
        Get absolute path to workspace folder.
        
        Args:
            workspace_id: The workspace ID
        
        Returns:
            Absolute path to the workspace folder
        
        Raises:
            FileNotFoundError if workspace doesn't exist
        """
        workspace_folder = self._workspace_folder_path(workspace_id)
        if not os.path.isdir(workspace_folder):
            raise FileNotFoundError(f"Workspace not found: {workspace_id}")
        return workspace_folder

    def _load_workspace_from_file(self, file_path: str) -> Optional[Workspace]:
        """Load and deserialize a workspace from a JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
                data["folder_path"] = str(Path(file_path).parent.absolute())
            return Workspace(**data)
        except Exception as ex:
            logger.exception("Error loading workspace from '%s': %s", file_path, ex)
            return None