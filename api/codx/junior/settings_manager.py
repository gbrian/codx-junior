"""
GlobalSettingsManager: Manages global settings with sectioned storage and version control.

Each section of GlobalSettings is stored in its own JSON file under:
    <config_folder>/settings/<section>.json

Version history is kept under:
    <config_folder>/history/<section>/<timestamp>.json

Made with ❤️ by codx-junior
"""

import os
import json
import logging
import pathlib
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Avoid circular imports - will be injected at runtime
_SECTION_VALIDATORS: Dict[str, Type[BaseModel]] = {}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_HISTORY_ENTRIES = 50
SETTINGS_DIR_NAME = "settings"
HISTORY_DIR_NAME = "history"
ENCODING = "utf-8"


class SectionVersion(BaseModel):
    """Represents a single version snapshot of a settings section."""
    section: str
    timestamp: str
    file_path: str


class GlobalSettingsManager:
    """
    Manages reading, writing, and version history of GlobalSettings sections.

    Each top-level field of GlobalSettings is treated as an independent section,
    stored in its own JSON file and versioned independently.

    ```mermaid
    classDiagram
        class GlobalSettingsManager {
            +config_folder: str
            +settings_dir: Path
            +history_dir: Path
            +read_section(section, model_class) T
            +write_section(section, data) void
            +list_history(section) List[SectionVersion]
            +rollback(section, timestamp) bool
            +read_all() dict
        }
    ```
    """

    def __init__(self, config_folder: Optional[str] = None) -> None:
        """
        Initialize the manager with the given config folder.

        Args:
            config_folder: Root folder for settings storage.
                           Defaults to CODX_JUNIOR_CONFIG_FOLDER env var or HOME.
        """
        home = os.environ.get("HOME", "/root")
        self.config_folder = config_folder or os.environ.get(
            "CODX_JUNIOR_CONFIG_FOLDER", home
        )
        self.settings_dir = pathlib.Path(self.config_folder) / SETTINGS_DIR_NAME
        self.history_dir = pathlib.Path(self.config_folder) / HISTORY_DIR_NAME
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create base directories if they do not exist."""
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Settings dir: %s | History dir: %s", self.settings_dir, self.history_dir)

    def _section_file(self, section: str) -> pathlib.Path:
        """Return the path to the section's JSON file."""
        return self.settings_dir / f"{section}.json"

    def _section_history_dir(self, section: str) -> pathlib.Path:
        """Return the path to the history folder for a section, creating it if needed."""
        history_section_dir = self.history_dir / section
        history_section_dir.mkdir(parents=True, exist_ok=True)
        return history_section_dir

    def _backup_section(self, section: str) -> None:
        """
        Create a versioned backup of the current section file.

        Keeps at most MAX_HISTORY_ENTRIES backups per section.

        Args:
            section: Name of the section to back up.
        """
        section_file = self._section_file(section)
        if not section_file.exists():
            return

        history_dir = self._section_history_dir(section)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_file = history_dir / f"{timestamp}.json"

        try:
            backup_file.write_text(section_file.read_text(encoding=ENCODING), encoding=ENCODING)
            logger.debug("Backed up section '%s' to %s", section, backup_file)
        except OSError as ex:
            logger.error("Failed to backup section '%s': %s", section, ex)

        self._prune_history(section)

    def _prune_history(self, section: str) -> None:
        """
        Remove oldest history entries beyond MAX_HISTORY_ENTRIES.

        Args:
            section: Name of the section to prune.
        """
        history_dir = self._section_history_dir(section)
        entries = sorted(history_dir.glob("*.json"), key=os.path.getmtime)
        if len(entries) > MAX_HISTORY_ENTRIES:
            for old_entry in entries[:-MAX_HISTORY_ENTRIES]:
                try:
                    old_entry.unlink()
                    logger.debug("Pruned old history entry: %s", old_entry)
                except OSError as ex:
                    logger.warning("Could not prune history entry %s: %s", old_entry, ex)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_section(self, section: str, model_class: Type[T], default: Optional[T] = None) -> T:
        """
        Read and deserialize a settings section into a Pydantic model.

        Args:
            section: Name of the section (matches GlobalSettings field name).
            model_class: Pydantic model class to deserialize into.
            default: Default instance if file is missing or corrupt.

        Returns:
            Deserialized model instance.
        """
        section_file = self._section_file(section)
        if not section_file.exists():
            logger.info("Section '%s' file not found, returning default.", section)
            return default if default is not None else model_class()

        try:
            raw = section_file.read_text(encoding=ENCODING)
            data = json.loads(raw)
            return model_class(**data) if isinstance(data, dict) else model_class.parse_raw(raw)
        except (json.JSONDecodeError, ValueError, TypeError) as ex:
            logger.error("Error deserializing section '%s': %s", section, ex)
            return default if default is not None else model_class()

    def read_section_raw(self, section: str) -> Any:
        """
        Read a section as raw Python data (dict, list, or scalar).

        Args:
            section: Name of the section.

        Returns:
            Parsed JSON data or None if the file is not found.
        """
        section_file = self._section_file(section)
        if not section_file.exists():
            logger.info("Section '%s' file not found.", section)
            return None

        try:
            return json.loads(section_file.read_text(encoding=ENCODING))
        except json.JSONDecodeError as ex:
            logger.error("Error reading raw section '%s': %s", section, ex)
            return None

    def write_section(self, section: str, data: Any) -> None:
        """
        Serialize and persist a settings section, backing up the previous version first.

        Validates data against the registered schema for the section before persisting.

        Args:
            section: Name of the section.
            data: Data to persist. Can be a Pydantic model, dict, list, or scalar.

        Raises:
            ValidationError: If data fails schema validation for this section.
        """
        # Validate data before backup/write
        self._validate_section_data(section, data)

        self._backup_section(section)
        section_file = self._section_file(section)

        try:
            if isinstance(data, BaseModel):
                serialized = data.json(indent=2)
            else:
                serialized = json.dumps(data, indent=2)

            section_file.write_text(serialized, encoding=ENCODING)
            logger.info("Section '%s' written to %s", section, section_file)
        except (OSError, TypeError) as ex:
            logger.error(
                "Failed to write section '%s': %s\n%s",
                section, ex, traceback.format_exc()
            )
            raise

    def list_history(self, section: str) -> List[SectionVersion]:
        """
        List available version snapshots for a section, newest first.

        Args:
            section: Name of the section.

        Returns:
            List of SectionVersion objects ordered from newest to oldest.
        """
        history_dir = self._section_history_dir(section)
        entries = sorted(history_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        return [
            SectionVersion(
                section=section,
                timestamp=entry.stem,
                file_path=str(entry),
            )
            for entry in entries
        ]

    def get_version(self, section: str, timestamp: str) -> Any:
        """
        Retrieve the raw content of a specific version snapshot.

        Args:
            section: Name of the section.
            timestamp: Timestamp string (stem of the history file).

        Returns:
            Parsed JSON data of the snapshot, or None if not found.
        """
        history_dir = self._section_history_dir(section)
        version_file = history_dir / f"{timestamp}.json"
        if not version_file.exists():
            logger.warning("Version '%s' not found for section '%s'.", timestamp, section)
            return None

        try:
            return json.loads(version_file.read_text(encoding=ENCODING))
        except json.JSONDecodeError as ex:
            logger.error(
                "Error reading version '%s' for section '%s': %s",
                timestamp, section, ex
            )
            return None

    def rollback(self, section: str, timestamp: str) -> bool:
        """
        Rollback a section to a specific historical version.

        The current state is backed up before rolling back.

        Args:
            section: Name of the section.
            timestamp: Timestamp of the version to restore.

        Returns:
            True if rollback succeeded, False otherwise.
        """
        version_data = self.get_version(section, timestamp)
        if version_data is None:
            logger.error(
                "Rollback failed: version '%s' not found for section '%s'.",
                timestamp, section
            )
            return False

        logger.info("Rolling back section '%s' to version '%s'.", section, timestamp)
        self.write_section(section, version_data)
        return True

    def read_all(self) -> Dict[str, Any]:
        """
        Read all available section files as raw data.

        Returns:
            Dictionary mapping section names to their raw parsed data.
        """
        result: Dict[str, Any] = {}
        for section_file in self.settings_dir.glob("*.json"):
            section = section_file.stem
            result[section] = self.read_section_raw(section)
        return result

    # ------------------------------------------------------------------
    # Validation API
    # ------------------------------------------------------------------

    def register_section_validator(
        self, section: str, model_class: Type[BaseModel]
    ) -> None:
        """
        Register a Pydantic model class as the validator for a section.

        This validator will be used by write_section() to validate data
        before persisting to disk.

        Args:
            section: Name of the section (must match GlobalSettings field name).
            model_class: Pydantic BaseModel class to use for validation.
        """
        _SECTION_VALIDATORS[section] = model_class
        logger.debug("Registered validator for section '%s': %s", section, model_class.__name__)

    def register_section_validators(self, validators: Dict[str, Type[BaseModel]]) -> None:
        """
        Register multiple section validators at once.

        Args:
            validators: Dict mapping section names to their model classes.
        """
        for section, model_class in validators.items():
            self.register_section_validator(section, model_class)

    def _validate_section_data(self, section: str, data: Any) -> None:
        """
        Validate section data against its registered schema before write.

        If no validator is registered for the section, validation is skipped
        (backward compatibility).

        Args:
            section: Name of the section.
            data: Data to validate.

        Raises:
            ValidationError: If data fails schema validation.
        """
        # If no validator registered, skip validation
        if section not in _SECTION_VALIDATORS:
            logger.debug(
                "No validator registered for section '%s', skipping validation",
                section
            )
            return

        model_class = _SECTION_VALIDATORS[section]

        try:
            # If data is already a Pydantic model of the correct type, consider it valid
            if isinstance(data, model_class):
                logger.debug("Section '%s' data already validated (Pydantic model)", section)
                return

            # For dicts, lists, or other data types, attempt to construct the model
            # This will raise ValidationError if data doesn't conform to the schema
            if isinstance(data, list):
                # For list sections, validate each item
                logger.debug("Validating list section '%s' with %d items", section, len(data))
                for idx, item in enumerate(data):
                    try:
                        # Get the inner model type from the List type hint
                        inner_model = self._get_list_inner_type(model_class)
                        if inner_model and not isinstance(item, inner_model):
                            inner_model(**item) if isinstance(item, dict) else inner_model(item)
                    except ValidationError as ex:
                        logger.error(
                            "Validation error for list item %d in section '%s': %s",
                            idx, section, ex
                        )
                        raise
            else:
                # For single object or dict data
                logger.debug("Validating section '%s' with model %s", section, model_class.__name__)
                if isinstance(data, dict):
                    model_class(**data)
                else:
                    model_class(data)

            logger.debug("Section '%s' data validation passed", section)

        except ValidationError as ex:
            logger.error(
                "Section '%s' validation failed: %s\nValidation details: %s",
                section, str(ex), ex.errors()
            )
            raise
        except (TypeError, ValueError) as ex:
            logger.error(
                "Section '%s' validation error (unexpected type): %s\n%s",
                section, str(ex), traceback.format_exc()
            )
            raise ValidationError(f"Invalid data type for section '{section}': {ex}")

    @staticmethod
    def _get_list_inner_type(model_class: Type) -> Optional[Type]:
        """
        Extract the inner model type from a List[Model] type hint.

        Args:
            model_class: The type to inspect (should be List[X]).

        Returns:
            The inner type X, or None if not a List type.
        """
        # Check if it's a generic type with __args__
        if hasattr(model_class, "__args__") and model_class.__args__:
            return model_class.__args__[0]
        return None