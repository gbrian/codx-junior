"""
LRT-0 smoke tests.

These tests cover the foundation of long-running tasks, i.e. the pieces the
feature depends on and that were broken or missing before milestone LRT-0:

* 0.1 ``codx.junior.kanban`` is importable,
* 0.2 the kanban catalogue is stored as ``index.json`` + ``boards/<id>/board.json``,
  the legacy ``kanban.json`` is migrated with a backup, a save does not lose
  boards and a rename keeps the folders (so no task has to be moved),
* 0.3 ``Chat.root_id`` resolves the topmost ancestor for any depth,
* 0.4 the cost of a descendant rolls up into the root chat (the run budget),
* 0.8 ``ChatManager.find_by_id`` matches the id exactly (not as a substring).

Run with::

    cd api && pytest tests -q
"""

import json
import os
import uuid

import pytest


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class FakeEventManager:
    """Minimal stand-in for EventManager: records the emitted events."""

    def __init__(self):
        self.events = []

    def chat_event(self, chat=None, message=None, event_type=None):
        self.events.append({"chat": getattr(chat, "id", None),
                            "message": message, "type": event_type})

    def message_event(self, chat=None, message=None):
        self.events.append({"chat": getattr(chat, "id", None), "message": "message"})

    def send_event(self, message=None):
        self.events.append({"message": message})


class FakeSettings:
    """The subset of CODXJuniorSettings used by ChatManager."""

    def __init__(self, codx_path: str, project_id: str = "project-1"):
        self.codx_path = codx_path
        self.project_id = project_id
        self.project_name = "test-project"
        self.abs_project_path = codx_path


@pytest.fixture()
def tasks_path(tmp_path):
    """Return a fresh ``.codx/tasks`` folder."""
    path = tmp_path / ".codx" / "tasks"
    path.mkdir(parents=True)
    return str(path)


@pytest.fixture()
def chat_manager(tmp_path, tasks_path):
    """Return a ChatManager bound to a temporary project."""
    from codx.junior.chat_manager import ChatManager

    return ChatManager(
        settings=FakeSettings(codx_path=str(tmp_path / ".codx")),
        event_manager=FakeEventManager(),
    )


def write_json(file_path, data):
    """Write *data* as JSON, creating the parent folder."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2))


def read_json(file_path):
    """Read a JSON file."""
    with open(file_path, "r", encoding="utf-8") as handle:
        return json.loads(handle.read())


# ---------------------------------------------------------------------------
# 0.1 - the kanban package imports
# ---------------------------------------------------------------------------


def test_kanban_package_imports():
    """0.1 - importing the package must not import any missing module."""
    import codx.junior.kanban as kanban

    assert kanban.DEFAULT_BOARD == "kanban"
    assert kanban.KanbanStore is not None
    # A name that is not part of the public API must raise AttributeError,
    # never ModuleNotFoundError.
    with pytest.raises(AttributeError):
        kanban.does_not_exist  # noqa: B018 - attribute access on purpose


# ---------------------------------------------------------------------------
# 0.2 - kanban storage v2
# ---------------------------------------------------------------------------


def test_store_migrates_legacy_kanban(tasks_path):
    """0.2 - the legacy single file is migrated, backed up and split per board."""
    legacy = {
        "version": 0.1,
        "boards": {
            "Bugs": {"description": "Backlog", "columns": [
                {"title": "Backlog"}, {"title": "Done"}]},
            "Sprint 12": {"type": "sprint", "columns": ["To do", "Doing"]},
        },
        "tags": {"ui": "#fff"},
    }
    write_json(os.path.join(tasks_path, "kanban.json"), legacy)

    from codx.junior.kanban.store import KanbanStore

    store = KanbanStore(tasks_path=tasks_path)
    kanban = store.load()

    assert set(kanban["boards"]) == {"Bugs", "Sprint 12"}
    assert kanban["tags"] == {"ui": "#fff"}
    assert kanban["boards"]["Bugs"]["columns"][0]["title"] == "Backlog"
    assert kanban["boards"]["Sprint 12"]["type"] == "sprint"

    index = read_json(os.path.join(tasks_path, "index.json"))
    assert index["version"] == 2
    assert len(index["boards"]) == 2

    for entry in index["boards"]:
        board_file = os.path.join(tasks_path, "boards", entry["id"], "board.json")
        assert os.path.isfile(board_file), board_file
        assert read_json(board_file)["title"] == entry["title"]

    # The legacy file is backed up before being replaced.
    assert os.path.isfile(os.path.join(tasks_path, "kanban.v1.backup.json"))
    assert not os.path.isfile(os.path.join(tasks_path, "kanban.json"))


def test_store_migration_is_idempotent(tasks_path):
    """0.2 - migrating twice keeps the same board ids (no duplicated boards)."""
    write_json(
        os.path.join(tasks_path, "kanban.json"),
        {"version": 0.1, "boards": {"Bugs": {"columns": [{"title": "Backlog"}]}}},
    )

    from codx.junior.kanban.store import KanbanStore

    first = KanbanStore(tasks_path=tasks_path).load()
    first_ids = sorted(
        entry["id"] for entry in read_json(os.path.join(tasks_path, "index.json"))["boards"]
    )

    second = KanbanStore(tasks_path=tasks_path).load()
    second_ids = sorted(
        entry["id"] for entry in read_json(os.path.join(tasks_path, "index.json"))["boards"]
    )

    assert set(first["boards"]) == set(second["boards"]) == {"Bugs"}
    assert first_ids == second_ids


def test_store_save_keeps_ids_and_removes_deleted_boards(tasks_path):
    """0.2 - a save keeps board identity and drops only the removed boards."""
    from codx.junior.kanban.store import KanbanStore

    store = KanbanStore(tasks_path=tasks_path)
    store.save({
        "version": 2,
        "boards": {
            "Bugs": {"columns": [{"title": "Backlog"}]},
            "Ideas": {"columns": [{"title": "New"}]},
        },
        "tags": {},
    })

    first = store.load()
    bugs_id = first["boards"]["Bugs"]["id"]
    assert first["boards"]["Bugs"]["folder"] == "Bugs"

    # Save again with one board removed and the other renamed.
    store.save({
        "version": 2,
        "boards": {
            "Bugs renamed": {**first["boards"]["Bugs"], "title": "Bugs renamed"},
        },
        "tags": {"x": "y"},
    })

    second = store.load()
    assert set(second["boards"]) == {"Bugs renamed"}
    assert second["boards"]["Bugs renamed"]["id"] == bugs_id
    assert second["tags"] == {"x": "y"}
    # The removed board definition is gone.
    assert not os.path.isdir(os.path.join(tasks_path, "boards", first["boards"]["Ideas"]["id"]))


def test_rename_does_not_move_folders(chat_manager, tasks_path):
    """0.2 - renaming a board changes the label only, never the storage path."""
    from codx.junior.db import Chat

    chat_manager.save_kanban({
        "version": 2,
        "boards": {"Bugs": {"columns": [{"title": "tasks"}]}},
        "tags": {},
    })

    chat = Chat(name="Fix login", board="Bugs", column="tasks", description="x")
    chat.messages = []
    saved = chat_manager.save_chat(chat=chat)
    original_path = saved.file_path
    assert os.path.isfile(original_path)
    assert "/Bugs/" in original_path

    # Rename the board (title only) and re-save the chat.
    kanban = chat_manager.load_kanban()
    board = kanban["boards"]["Bugs"]
    kanban["boards"] = {"Bugs renamed": {**board, "title": "Bugs renamed"}}
    chat_manager.save_kanban(kanban)

    reloaded = chat_manager.find_by_id(chat_id=saved.id)
    reloaded.board = "Bugs renamed"
    resaved = chat_manager.save_chat(chat=reloaded)

    assert resaved.file_path == original_path
    assert os.path.isfile(original_path)


def test_chat_paths_ignores_catalogue_files(chat_manager, tasks_path):
    """0.2 - the storage files are never listed as chats."""
    from codx.junior.db import Chat

    chat_manager.save_kanban({
        "version": 2,
        "boards": {"Bugs": {"columns": [{"title": "tasks"}]}},
        "tags": {},
    })
    chat = Chat(name="A task", board="Bugs", column="tasks", description="x")
    saved = chat_manager.save_chat(chat=chat)

    paths = chat_manager.chat_paths()

    assert saved.file_path in paths
    assert not any(os.path.basename(path) in ("index.json", "kanban.json") for path in paths)
    assert not any(os.sep + "boards" + os.sep in path for path in paths)


# ---------------------------------------------------------------------------
# 0.3 - ancestor invariant
# ---------------------------------------------------------------------------


def test_root_id_resolves_topmost_ancestor(chat_manager):
    """0.3 - a 3 level chain resolves to the same main task."""
    from codx.junior.db import Chat
    from codx.junior.identity import resolve_root_id
    from codx.junior.task_manager import TaskManager

    manager = TaskManager(chat_manager=chat_manager, settings=chat_manager.settings)

    main = manager.create_task(name="Main", description="objective")
    child = manager.create_task(name="Child", description="step", parent_chat=main)
    grandchild = manager.create_task(
        name="Grandchild", description="step", parent_chat=child
    )

    assert main.root_id == main.id
    assert child.root_id == main.id
    assert grandchild.root_id == main.id

    # The cache resolves without walking the tree.
    assert resolve_root_id(chat=grandchild, chat_manager=chat_manager) == main.id


def test_root_id_backfilled_for_legacy_chats(chat_manager):
    """0.3 - a chat without root_id gets it resolved (and persisted) on save."""
    from codx.junior.db import Chat
    from codx.junior.identity import resolve_root_id

    main = Chat(name="Main legacy", description="x")
    main = chat_manager.save_chat(chat=main)

    # Emulate a legacy child: parent_id set, root_id missing.
    child = Chat(name="Child legacy", description="x", parent_id=main.id)
    saved_child = chat_manager.save_chat(chat=child)

    assert saved_child.root_id == main.id
    reloaded = chat_manager.find_by_id(chat_id=saved_child.id)
    assert reloaded.root_id == main.id
    assert resolve_root_id(chat=reloaded, chat_manager=chat_manager) == main.id


# ---------------------------------------------------------------------------
# 0.4 - cost roll-up
# ---------------------------------------------------------------------------


def test_cost_rolls_up_to_root_chat(chat_manager):
    """0.4 - the cost of a descendant is added to the root chat exactly once."""
    from codx.junior.db import Chat, Message
    from codx.junior.identity import resolve_root_id
    from codx.junior.task_manager import TaskManager

    manager = TaskManager(chat_manager=chat_manager, settings=chat_manager.settings)
    main = manager.create_task(name="Budget owner", description="objective")
    main.estimation_cost = 10.0
    main = chat_manager.save_chat(chat=main)

    child = manager.create_task(name="Step", description="do it", parent_chat=main)
    child = chat_manager.find_by_id(chat_id=child.id)
    assert resolve_root_id(chat=child, chat_manager=chat_manager) == main.id

    child.messages.append(
        Message(role="assistant", content="done", cost=1.5)
    )
    chat_manager.save_chat(chat=child)

    root = chat_manager.find_by_id(chat_id=main.id)
    reloaded_child = chat_manager.find_by_id(chat_id=child.id)

    assert reloaded_child.cost == pytest.approx(1.5)
    assert root.cost == pytest.approx(1.5)

    # Re-saving the same message must not double count.
    chat_manager.save_chat(chat=reloaded_child)
    assert chat_manager.find_by_id(chat_id=main.id).cost == pytest.approx(1.5)


def test_cost_survives_message_deletion(chat_manager):
    """0.4 - removing a message keeps the spent budget."""
    from codx.junior.db import Chat, Message

    chat = Chat(name="Spender", description="x")
    chat = chat_manager.save_chat(chat=chat)

    message = Message(role="assistant", content="answer", cost=2.0)
    chat_manager.add_message(chat=chat, message=message)
    assert chat.cost == pytest.approx(2.0)

    chat_manager.remove_message(chat=chat, message_doc_id=message.doc_id)
    assert chat_manager.find_by_id(chat_id=chat.id).cost == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# 0.8 - exact chat lookup
# ---------------------------------------------------------------------------


def test_find_by_id_is_exact(chat_manager):
    """0.8 - an id that is a prefix of another one must not match it."""
    from codx.junior.db import Chat

    short_id = "11111111-1111-1111-1111-111111111111"
    long_id = "11111111-1111-1111-1111-111111111119"

    short_chat = Chat(id=short_id, name="Short", description="x")
    short_chat = chat_manager.save_chat(chat=short_chat)
    long_chat = Chat(id=long_id, name="Long", description="x")
    long_chat = chat_manager.save_chat(chat=long_chat)

    found_short = chat_manager.find_by_id(chat_id=short_id)
    found_long = chat_manager.find_by_id(chat_id=long_id)
    missing = chat_manager.find_by_id(chat_id="11111111-1111-1111-1111-11111111111")

    assert found_short is not None and found_short.id == short_id
    assert found_long is not None and found_long.id == long_id
    assert missing is None


def test_find_by_id_survives_random_ids(chat_manager):
    """0.8 - lookup works for generated ids too (regression guard)."""
    from codx.junior.db import Chat

    chat = chat_manager.save_chat(chat=Chat(name="Any", description="x"))
    assert chat_manager.find_by_id(chat_id=chat.id).id == chat.id
    assert chat_manager.find_by_id(chat_id=str(uuid.uuid4())) is None


# ---------------------------------------------------------------------------
# 0.6 - the deprecated sub-task generation is gone
# ---------------------------------------------------------------------------


def test_no_generate_tasks_symbol():
    """0.6 - the deprecated AI sub-task generation does not exist anymore."""
    import codx.junior.engine.chat_engine_actions as actions
    import codx.junior.engine.session as session
    import codx.junior.task_manager as task_manager

    assert not hasattr(actions.ChatEngineActions, "generate_tasks")
    assert not hasattr(session.CODXJuniorSession, "generate_tasks")
    assert not hasattr(task_manager.TaskManager, "create_tasks_from_prompt")


def test_legacy_engine_module_is_gone():
    """0.6 - the shadowed ``codx/junior/engine.py`` module was deleted."""
    import codx.junior.engine as engine_package

    assert engine_package.__file__.endswith(os.path.join("engine", "__init__.py"))


# ---------------------------------------------------------------------------
# 0.7 - the session exposes chat_event
# ---------------------------------------------------------------------------


def test_session_exposes_chat_event():
    """0.7 - ``CODXJuniorSession.chat_event`` exists (POST /api/chats needs it)."""
    from codx.junior.engine.session import CODXJuniorSession

    assert callable(getattr(CODXJuniorSession, "chat_event", None))

# Made with ❤️ by codx-junior