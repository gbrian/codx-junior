"""
ViewManager module.

Handles CRUD operations for desktop layout views stored per project.
Views are persisted as JSON files inside the project's `.codx/views/` directory.
"""

import os
import json
import logging
import pathlib

from typing import List, Optional

from codx.junior.settings import CODXJuniorSettings
from codx.junior.views.model import View

logger = logging.getLogger(__name__)

VIEWS_DIR = "views"
VIEW_FILE_EXTENSION = ".view"


class ViewManager:
    """
    Manages saved desktop layout views for a given project.

    Views are stored as JSON files in `<codx-ok, please-wait..._path>/views/<name>.view`.

    ```mermaid
    classDiagram
        class ViewManager {
            +settings: CODXJuniorSettings
            +views_path: str
            +list_views() List[View]
            +read_view(name: str) Optional[View]
            +save_view(view: View) View
            +delete_view(name: str) bool
            +rename_view(old_name: str, new_name: str) View
        }
    ```
    """

    def __init__(self, settings: CODXJuniorSettings) -> None:
        """
        Initialize ViewManager for the given project settings.

        Args:
            settings: The project settings containing codx_path and project_id.
        """
        self.settings = settings
        self.views_path = os.path.join(settings.codx_path, VIEWS_DIR)
        os.makedirs(self.views_path, exist_ok=True)
        logger.debug("ViewManager initialized at '%s'", self.views_path)

    def _view_file_path(self, name: str) -> str:
        """
        Build the full file path for a view by its name.

        Args:
            name: The view name.

        Returns:
            The absolute file path for the view JSON file.
        """
        safe_name = name.replace("/", "_").replace("\\", "_")
        return os.path.join(self.views_path, f"{safe_name}{VIEW_FILE_EXTENSION}")

    def _load_view_from_file(self, file_path: str) -> Optional[View]:
        """
        Load and deserialize a single view from a JSON file.

        Args:
            file_path: Absolute path to the `.view` file.

        Returns:
            A `View` instance, or None if loading fails.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.loads(fh.read())
            view = View(**data)
            logger.debug("Loaded view '%s' from '%s'", view.name, file_path)
            return view
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error("Failed to load view from '%s': %s", file_path, exc)
            return None

    def list_views(self) -> List[View]:
        """
        Return all views saved for this project.

        Returns:
            A list of `View` instances sorted alphabetically by name.
        """
        view_files = sorted(pathlib.Path(self.views_path).glob(f"*{VIEW_FILE_EXTENSION}"))
        views = []
        for file_path in view_files:
            view = self._load_view_from_file(str(file_path))
            if view is not None:
                views.append(view)
        logger.info("Listed %d views for project '%s'", len(views), self.settings.project_id)
        return views

    def read_view(self, name: str) -> Optional[View]:
        """
        Read a single view by its name.

        Args:
            name: The view name to look up.

        Returns:
            The matching `View` instance, or None if not found.
        """
        file_path = self._view_file_path(name)
        if not os.path.isfile(file_path):
            logger.warning("View '%s' not found at '%s'", name, file_path)
            return None
        return self._load_view_from_file(file_path)

    def save_view(self, view: View) -> View:
        """
        Persist a view to disk (create or overwrite).

        The view's ``project_id`` is always set to the current project's id
        to ensure ownership is correctly recorded.

        Args:
            view: The `View` object to save.

        Returns:
            The saved `View` instance.

        Raises:
            ValueError: When the view has no name.
        """
        if not view.name:
            raise ValueError("Cannot save a view without a name.")

        # Always associate the view with this project
        view.project_id = self.settings.project_id

        file_path = self._view_file_path(view.name)
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(view.model_dump(), indent=2))

        logger.info("Saved view '%s' to '%s'", view.name, file_path)
        return view

    def delete_view(self, name: str) -> bool:
        """
        Delete a view by its name.

        Args:
            name: The view name to delete.

        Returns:
            True if the view was deleted, False if it did not exist.
        """
        file_path = self._view_file_path(name)
        if not os.path.isfile(file_path):
            logger.warning("Attempted to delete non-existent view '%s'", name)
            return False

        os.remove(file_path)
        logger.info("Deleted view '%s' from '%s'", name, file_path)
        return True

    def rename_view(self, old_name: str, new_name: str) -> View:
        """
        Rename an existing view.

        Loads the view under `old_name`, updates its name to `new_name`,
        saves it under the new name, then removes the old file.

        Args:
            old_name: The current view name.
            new_name: The desired new view name.

        Returns:
            The updated `View` instance saved under the new name.

        Raises:
            FileNotFoundError: When no view with `old_name` exists.
            ValueError: When `new_name` is empty.
        """
        if not new_name:
            raise ValueError("New view name must not be empty.")

        existing_view = self.read_view(old_name)
        if existing_view is None:
            raise FileNotFoundError(f"View '{old_name}' does not exist.")

        # Save under new name first, then remove the old file
        existing_view.name = new_name
        self.save_view(existing_view)

        old_file_path = self._view_file_path(old_name)
        if os.path.isfile(old_file_path):
            os.remove(old_file_path)
            logger.info("Removed old view file '%s' after rename to '%s'", old_file_path, new_name)

        logger.info("Renamed view '%s' -> '%s'", old_name, new_name)
        return existing_view

# Made with ❤️ by codx-junior