import os
import pytest
from datetime import datetime
from codx.junior.db import CODXJuniorDB, Kanban, KanbanColumn
from codx.junior.settings import CODXJuniorSettings

@pytest.fixture
def db():
    settings = CODXJuniorSettings(project_path="test_project", codx_path=os.path.dirname(__file__))
    return CODXJuniorDB(settings)

@pytest.fixture
def sample_kanban():
    return Kanban(
        title="Test Board",
        description="Test Description",
        columns=[
            KanbanColumn(
                title="Todo",
                color="#ff0000",
                index=0,
                chats=[]
            ),
            KanbanColumn(
                title="In Progress",
                color="#00ff00", 
                index=1,
                chats=[]
            )
        ],
        created_at=str(datetime.now()),
        updated_at=str(datetime.now())
    )

def test_create_kanban(db, sample_kanban):
    created = db.create_kanban(sample_kanban)
    assert created.title == sample_kanban.title
    assert created.description == sample_kanban.description
    assert len(created.columns) == 2
    assert created.doc_id is not None

def test_get_kanban(db, sample_kanban):
    created = db.create_kanban(sample_kanban)
    retrieved = db.get_kanban(created.doc_id)
    assert retrieved.title == sample_kanban.title
    assert retrieved.doc_id == created.doc_id

def test_update_kanban(db, sample_kanban):
    created = db.create_kanban(sample_kanban)
    created.title = "Updated Board"
    created.description = "Updated Description"
    updated = db.update_kanban(created)
    assert updated.title == "Updated Board"
    assert updated.description == "Updated Description"

def test_delete_kanban(db, sample_kanban):
    created = db.create_kanban(sample_kanban)
    db.delete_kanban(created)
    assert db.get_kanban(created.doc_id) is None

def test_kanban_with_columns(db, sample_kanban):
    created = db.create_kanban(sample_kanban)
    assert len(created.columns) == 2
    assert created.columns[0].title == "Todo"
    assert created.columns[1].title == "In Progress"
    assert created.columns[0].color == "#ff0000"
    assert created.columns[1].color == "#00ff00"

def test_kanban_timestamps(db, sample_kanban):
    created = db.create_kanban(sample_kanban)
    assert created.created_at is not None
    assert created.updated_at is not None

def test_update_kanban_update_time(db, sample_kanban):
    created = db.create_kanban(sample_kanban)
    original_update_time = created.updated_at
    created.title = "Updated Board"
    updated = db.update_kanban(created)
    assert updated.updated_at is not None
    assert updated.updated_at != original_update_time
