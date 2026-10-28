"""
Canonical task creation for codx-junior.

A **task** is a :class:`~codx.junior.db.Chat` stored in
``.codx/tasks/<board>/<column>/`` (kanban). This module is the only place where
a task is built and persisted, so the creation rules are enforced once and
every entry point behaves exactly the same.

Creation rules
--------------
1. **Only two kinds of callers may create tasks**: the LLM tools
   (``create_task`` and ``project_manager(action="create_task")``) and the API
   endpoints (``POST /api/chats/tasks``). Both delegate here.
2. **All the information must come from the caller.** ``name`` and
   ``description`` are mandatory: there is no AI step that expands, splits or
   rewrites a task after creation.
3. **Nothing is inherited from the parent chat.** ``profiles``, ``files``,
   ``board``, ``column``, ``sprints``, ``tags`` and the first message come
   exclusively from the arguments. Only the *linkage* (``parent_id``) and the
   project scope are resolved from the parent chat, when one is given.

Deprecated entry points (removed by this module)
------------------------------------------------
* ``ChatEngineActions.generate_tasks`` — turned a conversation into a list of
  sub-tasks and processed each one through the engine.
* ``TaskManager.create_tasks_from_prompt`` — asked the model for a task list.

Creating a task is now an explicit decision, never an inference.

```mermaid
flowchart TD
    A[LLM tool: create_task] --> M[TaskManager.create_task]
    B[LLM tool: project_manager create_task] --> M
    C[API: POST /api/chats/tasks] --> M
    M --> V{name and description?}
    V -->|no| E[ValueError: information is mandatory]
    V -->|yes| N[Normalize profiles / files / tags]
    N --> K[Build Chat mode=task + first user message]
    K --> S[ChatManager.save_chat]
    S --> R[Return the saved task]
```

Made with ❤️ by codx-junior
"""

import logging
from typing import Any, List, Optional

from codx.junior.chat_manager import ChatManager
from codx.junior.db import Chat, Message
from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# Default destination, matching ChatManager defaults.
DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"
DEFAULT_MODE = "task"


def to_list(value: Any) -> List[str]:
    """
    Normalize a string, iterable or None into a clean list of strings.

    Args:
        value: A string, a list/tuple/set or None.

    Returns:
        List of non-empty, stripped strings (order preserved).

    Example:
        >>> to_list("ui")
        ['ui']
        >>> to_list([" ui ", "", None])
        ['ui']
    """
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    try:
        return [str(item).strip() for item in value if item and str(item).strip()]
    except TypeError:
        return []


def to_profile_names(value: Any) -> List[str]:
    """
    Normalize a profile list: no duplicates, no leading ``@``.

    The chat engine re-emits profiles as ``@name`` mentions, so a stored
    ``@name`` (or ``@@name``) would never resolve to a profile. Only the values
    received are used — profiles are never inherited from the parent chat.

    Args:
        value: A string, a list/tuple/set or None.

    Returns:
        De-duplicated profile names, order preserved.

    Example:
        >>> to_profile_names(["@backend", "backend", " ui "])
        ['backend', 'ui']
    """
    names: List[str] = []
    for name in to_list(value):
        clean = name.lstrip("@").strip()
        if clean and clean not in names:
            names.append(clean)
    return names


def to_progress(value: Any, default: int = 0) -> int:
    """
    Clamp a completion percentage into the ``0-100`` range.

    Args:
        value: Raw progress value (may be None or a string).
        default: Value returned when ``value`` is not a number.

    Returns:
        Integer percentage.
    """
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return default


class TaskManager:
    """
    Canonical task (kanban chat) factory for a project.

    Attributes:
        settings: Project settings, used to resolve the project scope.
        chat_manager: Persistence layer (built from ``settings`` when omitted).
        event_manager: Optional event manager used to notify the UI.
    """

    def __init__(
        self,
        settings: Optional[CODXJuniorSettings] = None,
        chat_manager: Optional[ChatManager] = None,
        event_manager=None,
        session=None,
    ):
        """
        Initialize the manager.

        Args:
            settings: Project settings.
            chat_manager: Optional ChatManager; built from ``settings`` when omitted.
            event_manager: Optional event manager (only used for notifications).
            session: Optional session, kept for backward compatibility. Used to
                resolve ``settings``, ``chat_manager`` and ``event_manager`` when
                they are not provided explicitly.

        Raises:
            ValueError: When neither a chat manager nor settings are available.
        """
        self.settings = settings or getattr(session, "settings", None)
        self.event_manager = event_manager or getattr(session, "event_manager", None)

        self.chat_manager = chat_manager
        if self.chat_manager is None and session is not None:
            try:
                self.chat_manager = session.get_chat_manager()
            except (AttributeError, TypeError):
                self.chat_manager = None
        if self.chat_manager is None:
            if self.settings is None:
                raise ValueError(
                    "TaskManager requires project settings or a chat manager"
                )
            self.chat_manager = ChatManager(
                settings=self.settings,
                event_manager=self.event_manager,
            )

    def create_task(
        self,
        name: str,
        description: str,
        content: Optional[str] = None,
        board: Optional[str] = None,
        column: Optional[str] = None,
        sprints: Any = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        progress: Any = 0,
        assignees: Any = None,
        profiles: Any = None,
        files: Any = None,
        tags: Any = None,
        parent_id: Optional[str] = None,
        parent_chat: Optional[Chat] = None,
        project_id: Optional[str] = None,
        owner_project_id: Optional[str] = None,
        user: Optional[str] = None,
        mode: str = DEFAULT_MODE,
    ) -> Chat:
        """
        Create and persist a task with the information provided by the caller.

        Only the arguments are used: nothing is copied from ``parent_chat`` but
        the linkage (``parent_id``) and the project scope fallbacks. The
        destination (board/column/sprint/state) is validated by the caller that
        knows the project catalogue (``project_manager``); this method only
        applies the defaults.

        Args:
            name: Task name/title (required).
            description: Complete task description (required).
            content: First user message; defaults to ``description``.
            board: Kanban board; defaults to ``kanban``.
            column: Kanban column; defaults to ``tasks``.
            sprints: Sprint identifiers to associate (each one is a board).
            status: Initial task state (``Chat.status``).
            priority: Task priority (``high`` / ``medium`` / ``low``).
            due_date: Due date in ISO format (``YYYY-MM-DD``).
            progress: Completion percentage (clamped to 0-100).
            assignees: Assigned usernames.
            profiles: Profiles/roles for the task (parameter only).
            files: Files related to the task (parameter only).
            tags: Tags for categorizing the task.
            parent_id: Parent chat id (falls back to ``parent_chat.id``).
            parent_chat: Chat that triggered the creation (scope + linkage only).
            project_id: Project the task works on (falls back to the parent).
            owner_project_id: Project that stores the task (falls back to the parent).
            user: Author username.
            mode: Chat mode of the task (``task`` by default).

        Returns:
            The persisted :class:`~codx.junior.db.Chat`.

        Raises:
            ValueError: When ``name`` or ``description`` is missing.

        Example:
            >>> TaskManager(settings).create_task(
            ...     name="Fix login timeout",
            ...     description="## Context\nThe login times out after 30s...",
            ...     board="kanban",
            ...     column="tasks",
            ...     profiles=["backend"],
            ... )
        """
        name = (name or "").strip()
        description = (description or "").strip()

        if not name:
            raise ValueError("name is required to create a task")
        if not description:
            raise ValueError(
                "description is required to create a task: tasks are created "
                "with all their information (there is no AI sub-task "
                "generation anymore)"
            )

        settings_project_id = getattr(self.settings, "project_id", None)
        task_profiles = to_profile_names(profiles)
        task_files = to_list(files)

        task = Chat(
            name=name,
            description=description,
            parent_id=parent_id or getattr(parent_chat, "id", None),
            board=(board or DEFAULT_BOARD).strip(),
            column=(column or DEFAULT_COLUMN).strip(),
            sprints=to_list(sprints),
            status=(status or "").strip(),
            priority=priority,
            due_date=due_date,
            progress=to_progress(progress),
            assignees=to_list(assignees),
            profiles=task_profiles,
            file_list=task_files,
            tags=to_list(tags),
            project_id=(
                project_id
                or getattr(parent_chat, "project_id", None)
                or settings_project_id
            ),
            owner_project_id=(
                owner_project_id
                or getattr(parent_chat, "owner_project_id", None)
                or settings_project_id
            ),
            mode=mode,
        )

        task.messages.append(
            Message(
                role="user",
                content=(content or description).strip(),
                profiles=task_profiles,
                files=task_files,
                user=user,
            )
        )

        saved_task = self.chat_manager.save_chat(chat=task)

        logger.info(
            "TaskManager: task created id='%s' name='%s' board='%s' column='%s' "
            "sprints=%s profiles=%s parent_id=%s",
            saved_task.id,
            saved_task.name,
            saved_task.board,
            saved_task.column,
            saved_task.sprints,
            task_profiles,
            saved_task.parent_id,
        )

        if self.event_manager is not None:
            try:
                self.event_manager.chat_event(
                    chat=saved_task,
                    message=f"Task '{saved_task.name}' created",
                    event_type="created",
                )
            except Exception as ex:
                logger.warning("TaskManager: could not emit chat event: %s", ex)

        return saved_task

# Made with ❤️ by codx-junior