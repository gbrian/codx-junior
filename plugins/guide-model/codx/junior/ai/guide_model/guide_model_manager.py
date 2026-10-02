import os
from typing import Dict, Optional
from codx.junior.ai.guide_model import GuideModel


class GuideModelManager:
    """
    Manages multiple GuideModel instances, one per project.
    Provides a singleton-like registry keyed by project path.
    """

    _instances: Dict[str, GuideModel] = {}

    DEFAULT_MODEL_NAME = "smollm2-360m-instruct-q4_k_m.gguf"

    @classmethod
    def get_or_create(
        cls,
        project_path: str,
        guide_text: str,
        model_name: Optional[str] = None,
        force_refresh: bool = False
    ) -> GuideModel:
        """
        Returns an existing GuideModel for the project or creates a new one.

        Args:
            project_path: Unique identifier for the project (its filesystem path).
            guide_text: The project guide document content.
            model_name: GGUF model filename to use (defaults to DEFAULT_MODEL_NAME).
            force_refresh: If True, reprocesses the guide even if a state exists.

        Returns:
            A ready-to-use GuideModel instance.
        """
        model_name = model_name or cls.DEFAULT_MODEL_NAME

        if project_path not in cls._instances:
            print(f"[GuideModelManager] Creating GuideModel for project: {project_path}")
            guide_model = GuideModel(model_name=model_name)
            guide_model.load_guide(guide_text, force_refresh=force_refresh)
            cls._instances[project_path] = guide_model
        elif force_refresh:
            print(f"[GuideModelManager] Refreshing guide for project: {project_path}")
            cls._instances[project_path].reload_guide(guide_text)

        return cls._instances[project_path]

    @classmethod
    def remove(cls, project_path: str):
        """Removes a GuideModel instance from the registry."""
        if project_path in cls._instances:
            del cls._instances[project_path]
            print(f"[GuideModelManager] Removed GuideModel for project: {project_path}")

    @classmethod
    def list_active_projects(cls):
        """Returns a list of project paths with active GuideModel instances."""
        return list(cls._instances.keys())