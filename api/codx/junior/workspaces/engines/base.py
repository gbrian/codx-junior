from abc import ABC, abstractmethod
from typing import List

from codx.junior.workspaces.model import Workspace, WorkspaceStatus


class WorkspaceEngine(ABC):
    """
    Backend-agnostic workspace lifecycle interface.

    Implementations: DockerComposeEngine (phase 1), KubernetesEngine (future).
    """

    @abstractmethod
    def provision(self, workspace: Workspace) -> None:
        """Render/prepare workspace runtime files (compose file, env, network)."""

    @abstractmethod
    def start(self, workspace: Workspace) -> None:
        """Start the workspace containers."""

    @abstractmethod
    def stop(self, workspace: Workspace) -> None:
        """Stop the workspace containers (keep volumes/state)."""

    @abstractmethod
    def destroy(self, workspace: Workspace) -> None:
        """Remove containers, network and runtime state."""

    @abstractmethod
    def status(self, workspace: Workspace) -> WorkspaceStatus:
        """Return the current workspace status."""

    @abstractmethod
    def logs(self, workspace: Workspace, tail: int = 200) -> str:
        """Return recent workspace logs."""