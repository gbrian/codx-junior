import pytest
import os
from datetime import datetime, timedelta
from codx.junior.db import CODXJuniorDB, Chat, Kanban, KanbanColumn, Message
from codx.junior.settings import CODXJuniorSettings

@pytest.fixture
def settings():
    codx_path = "/tmp/test_project/.codx"
    os.makedirs(codx_path, exist_ok=True)
    return CODXJuniorSettings(
        project_path="/tmp/test_project",
        codx_path=codx_path
    )

@pytest.fixture
def db(settings):
    db = CODXJuniorDB(settings)
    db.reset()
    return db

def test_save_and_get_kanban(db):
    kanban = Kanban(
        title="Test Kanban",
        description="Test Description",
        columns=[
            KanbanColumn(title="Todo", color="#ff0000", index=0),
            KanbanColumn(title="Done", color="#00ff00", index=1)
        ]
    )
    
    saved_kanban = db.save_kanban(kanban)
    assert saved_kanban.doc_id is not None
    assert saved_kanban.created_at is not None
    assert saved_kanban.updated_at is not None
    
    kanbans = db.get_all_kankan()
    assert len(kanbans) >= 1
    assert kanbans[0].title == "Test Kanban"

def test_save_and_get_chat(db):
    chat = Chat(
        name="Test Chat",
        kanban_id="test_kanban",
        column_id="test_column",
        messages=[
            Message(
                role="user",
                content="Test message",
                created_at=str(datetime.now())
            )
        ]
    )
    
    db.save_chat(chat)
    chats = db.get_kanban_chats("test_kanban", "test_column")
    assert len(chats) > 0
    assert chats[0].name == "Test Chat"

def test_update_existing_chat(db):
    chat = Chat(
        name="Original Name",
        kanban_id="test_kanban",
        column_id="test_column"
    )
    
    db.save_chat(chat)
    original_id = chat.doc_id
    
    chat.name = "Updated Name"
    db.save_chat(chat)
    
    updated_chats = db.get_kanban_chats("test_kanban", "test_column")
    assert len(updated_chats) == 1
    assert updated_chats[0].doc_id == original_id
    assert updated_chats[0].name == "Updated Name"

def test_update_existing_kanban(db):
    kanban = Kanban(
        title="Original Title",
        description="Original Description"
    )
    
    saved_kanban = db.save_kanban(kanban)
    original_id = saved_kanban.doc_id
    
    saved_kanban.title = "Updated Title"
    db.save_kanban(saved_kanban)
    
    kanbans = db.get_all_kankan()
    assert len(kanbans) == 1
    assert kanbans[0].doc_id == original_id
    assert kanbans[0].title == "Updated Title"
