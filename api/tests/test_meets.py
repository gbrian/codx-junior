"""
Tests for the meets API.

Two behaviours are covered, both of which were the cause of a broken call:

* **Signalling identity** – the lifecycle socket events (``initiated``,
  ``joined``, ``left``, ``ended``) must carry the sender socket id (``fromSid``).
  Peers key the WebRTC connection by ``username::sessionId``; without it the
  answer and the ICE candidates were looked up under a key that did not exist
  and the participants could not see each other.

* **Shared browser session** – the host can start a browser/computer session
  *for the whole room*. The association lives on the meet (so late joiners get
  it back) and is broadcast as a ``browser-session`` event.

The router is mounted on a bare ``FastAPI`` app and socket emission is stubbed,
so the suite runs without the engine, a socket server or Docker.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from codx.junior.api import meets as meets_api
from codx.junior.meets.meet_manager import get_meet_manager


@pytest.fixture
def api(monkeypatch):
    """Return ``(client, events)`` with socket emission captured."""
    events = []

    async def fake_emit(event, data, to=None):  # noqa: ARG001 - emit signature
        events.append({"event": event, "data": data})

    monkeypatch.setattr(meets_api, "_emit", fake_emit)
    app = FastAPI()
    app.include_router(meets_api.router, prefix="/api")
    return TestClient(app), events


def headers(username="admin", sid="sid-admin", **extra):
    """Participant identity: the API resolves it from these headers."""
    return {"x-username": username, "x-sid": sid, **extra}


def new_meet_id():
    """Unique id per test: the meet registry is a process-wide singleton."""
    return f"test-{uuid.uuid4().hex[:10]}"


def events_of(events, event_type):
    return [item["data"] for item in events if item["data"].get("type") == event_type]


def initiate(client, meet_id, name="Test meet", username="admin", sid="sid-admin"):
    response = client.post(
        "/api/meets/initiate",
        json={"meetId": meet_id, "name": name, "participants": []},
        headers=headers(username, sid),
    )
    assert response.status_code == 200, response.text
    return response.json()["meet"]


def join(client, meet_id, username, sid):
    response = client.post(
        "/api/meets/join",
        json={"meetId": meet_id},
        headers=headers(username, sid),
    )
    assert response.status_code == 200, response.text
    return response.json()["meet"]


# ---------------------------------------------------------------------------
# Signalling identity
# ---------------------------------------------------------------------------


def test_lifecycle_events_carry_the_sender_session_id(api):
    client, events = api
    meet_id = new_meet_id()

    initiate(client, meet_id)
    join(client, meet_id, "gbrian", "sid-gbrian")

    initiated = events_of(events, "initiated")
    joined = events_of(events, "joined")
    assert initiated and initiated[0]["fromSid"] == "sid-admin"
    # This is what lets the existing peer build the offer for the right device.
    assert joined and joined[0]["fromSid"] == "sid-gbrian"


def test_join_event_exposes_the_shared_browser_to_newcomers(api):
    client, events = api
    meet_id = new_meet_id()
    initiate(client, meet_id)
    client.post(
        f"/api/meets/{meet_id}/browser",
        json={"sessionId": "session-1", "sessionName": "KasmVNC"},
        headers=headers(),
    )

    join(client, meet_id, "gbrian", "sid-gbrian")

    joined = events_of(events, "joined")[-1]
    assert joined["participants"] == ["admin", "gbrian"]
    assert joined["sharedBrowser"]["session_id"] == "session-1"


# ---------------------------------------------------------------------------
# Shared browser session
# ---------------------------------------------------------------------------


def test_sharing_a_browser_session_is_stored_and_broadcast(api):
    client, events = api
    meet_id = new_meet_id()
    initiate(client, meet_id, name="Standup")

    response = client.post(
        f"/api/meets/{meet_id}/browser",
        json={"sessionId": "session-42", "sessionName": "Firefox", "kind": "browser"},
        headers=headers("admin", "sid-admin"),
    )

    assert response.status_code == 200, response.text
    meet = response.json()["meet"]
    assert meet["shared_browser"] == {
        "session_id": "session-42",
        "session_name": "Firefox",
        "kind": "browser",
        "owner": "admin",
        "timestamp": meet["shared_browser"]["timestamp"],
    }

    broadcast = events_of(events, "browser-session")[-1]
    assert broadcast["meetId"] == meet_id
    assert broadcast["from"] == "admin"
    assert broadcast["fromSid"] == "sid-admin"
    assert broadcast["sharedBrowser"]["session_id"] == "session-42"


def test_shared_browser_survives_in_the_meet_details(api):
    client, _ = api
    meet_id = new_meet_id()
    initiate(client, meet_id)
    client.post(
        f"/api/meets/{meet_id}/browser",
        json={"sessionId": "session-7", "sessionName": "Shared"},
        headers=headers(),
    )

    details = client.get(f"/api/meets/{meet_id}").json()["meet"]
    assert details["shared_browser"]["session_id"] == "session-7"


def test_unsharing_clears_the_session(api):
    client, events = api
    meet_id = new_meet_id()
    initiate(client, meet_id)
    client.post(
        f"/api/meets/{meet_id}/browser",
        json={"sessionId": "session-9"},
        headers=headers(),
    )

    response = client.delete(f"/api/meets/{meet_id}/browser", headers=headers())

    assert response.status_code == 200, response.text
    assert response.json()["meet"]["shared_browser"] is None
    assert events_of(events, "browser-session")[-1]["sharedBrowser"] is None


def test_sharing_requires_a_session_id(api):
    client, _ = api
    meet_id = new_meet_id()
    initiate(client, meet_id)

    response = client.post(
        f"/api/meets/{meet_id}/browser", json={"sessionId": "  "}, headers=headers()
    )

    assert response.status_code == 400


def test_sharing_an_unknown_meet_is_a_404(api):
    client, _ = api

    response = client.post(
        f"/api/meets/{new_meet_id()}/browser",
        json={"sessionId": "session-x"},
        headers=headers(),
    )

    assert response.status_code == 404


def test_manager_clears_the_session_when_set_with_none():
    manager = get_meet_manager()
    meet = manager.initiate_meet(
        meet_id=new_meet_id(), name="Manager meet", initiator="admin"
    )
    manager.set_shared_browser(meet.meet_id, {"session_id": "one"})
    assert manager.get_meet(meet.meet_id).shared_browser == {"session_id": "one"}

    manager.set_shared_browser(meet.meet_id, None)
    assert manager.get_meet(meet.meet_id).shared_browser is None
