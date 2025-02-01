import os
import pytest
from datetime import datetime, timedelta
from codx.junior.db import CODXJuniorDB, Chat, Message
from codx.junior.settings import CODXJuniorSettings

@pytest.fixture
def db():
    settings = CODXJuniorSettings(project_path="test_project", codx_path=os.path.dirname(__file__))
    return CODXJuniorDB(settings)

@pytest.fixture
def sample_chat():
    return Chat(
        name="Test Chat",
        mode="chat",
        board="Default",
        column="todo",
        messages=[
            Message(
                role="user",
                content="Test message 1",
                created_at=str(datetime.now()),
                updated_at=str(datetime.now())
            ),
            Message(
                role="assistant",
                content="Test response 1",
                created_at=str(datetime.now()),
                updated_at=str(datetime.now())
            )
        ],
        created_at=str(datetime.now()),
        updated_at=str(datetime.now())
    )

def test_create_chat(db, sample_chat):
    created = db.create_chat(sample_chat)
    assert created.name == sample_chat.name
    assert created.mode == sample_chat.mode
    assert len(created.messages) == 2
    assert created.doc_id is not None

def test_get_chat(db, sample_chat):
    created = db.create_chat(sample_chat)
    retrieved = db.get_chat(created.doc_id)
    assert retrieved.name == sample_chat.name
    assert retrieved.doc_id == created.doc_id

def test_update_chat(db, sample_chat):
    created = db.create_chat(sample_chat)
    created.name = "Updated Chat"
    created.mode = "task"
    updated = db.update_chat(created)
    assert updated.name == "Updated Chat"
    assert updated.mode == "task"
    # Verify timestamp was updated
    assert datetime.fromisoformat(updated.updated_at) > datetime.fromisoformat(created.created_at)

def test_delete_chat(db, sample_chat):
    created = db.create_chat(sample_chat)
    db.delete_chat(created)
    assert db.get_chat(created.doc_id) is None

def test_chat_with_messages(db, sample_chat):
    created = db.create_chat(sample_chat)
    assert len(created.messages) == 2
    assert created.messages[0].role == "user"
    assert created.messages[1].role == "assistant"
    assert created.messages[0].content == "Test message 1"
    assert created.messages[1].content == "Test response 1"

def test_chat_timestamps(db, sample_chat):
    created = db.create_chat(sample_chat)
    assert datetime.fromisoformat(created.created_at)
    assert datetime.fromisoformat(created.updated_at)
    # Verify created_at and updated_at are within last minute
    now = datetime.now()
    created_at = datetime.fromisoformat(created.created_at)
    updated_at = datetime.fromisoformat(created.updated_at)
    assert now - timedelta(minutes=1) <= created_at <= now
    assert now - timedelta(minutes=1) <= updated_at <= now
