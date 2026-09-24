import os
import sys

os.environ["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "_tmp_data_journal")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import shutil

import pytest

from app import create_app
from db import db


@pytest.fixture()
def client():
    shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.session.remove()
    shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)


def _design_item(client):
    items = client.get("/api/scope-items?project_id=ff5bfe0b-7b18-4337-a464-6517c6f6c13b").get_json()
    return next(i for i in items if i["code"] == "1.2")


def test_editing_a_field_auto_logs_a_change_event(client):
    item = _design_item(client)
    res = client.put(f"/api/scope-items/{item['id']}", json={
        "title": "Systems Engineering (Updated)", "author": "Sam Ortiz (PM)",
    })
    assert res.status_code == 200

    events = client.get(f"/api/scope-items/{item['id']}/events").get_json()
    change = next(e for e in events if e["kind"] == "change")
    assert change["field"] == "title"
    assert change["old_value"] == "Systems Engineering"
    assert change["new_value"] == "Systems Engineering (Updated)"
    assert change["author"] == "Sam Ortiz (PM)"


def test_editing_with_no_actual_change_logs_nothing(client):
    item = _design_item(client)
    client.put(f"/api/scope-items/{item['id']}", json={"title": item["title"]})
    events = client.get(f"/api/scope-items/{item['id']}/events").get_json()
    assert events == []


def test_edit_with_journal_note_logs_both(client):
    item = _design_item(client)
    res = client.put(f"/api/scope-items/{item['id']}", json={
        "charge_number": "CN-4471-10-REV1",
        "journal_note": "Renumbered after a scope split.",
        "author": "Sam Ortiz (PM)",
    })
    assert res.status_code == 200

    events = client.get(f"/api/scope-items/{item['id']}/events").get_json()
    kinds = {e["kind"] for e in events}
    assert kinds == {"change", "note"}
    note = next(e for e in events if e["kind"] == "note")
    assert note["note"] == "Renumbered after a scope split."


def test_progress_updates_are_not_journal_events(client):
    """ScopeProgressEvent and ScopeEvent are deliberately separate feeds."""
    item = _design_item(client)
    client.post(f"/api/scope-items/{item['id']}/progress", json={
        "status": "done", "percent_complete": 100, "note": "Re-confirmed after review.",
    })
    events = client.get(f"/api/scope-items/{item['id']}/events").get_json()
    assert events == []


def test_add_manual_note(client):
    item = _design_item(client)
    res = client.post(f"/api/scope-items/{item['id']}/events", json={
        "note": "Customer asked for a design review recap.", "author": "Sam Ortiz (PM)",
    })
    assert res.status_code == 201
    assert res.get_json()["kind"] == "note"

    events = client.get(f"/api/scope-items/{item['id']}/events").get_json()
    assert len(events) == 1


def test_add_manual_note_requires_text(client):
    item = _design_item(client)
    res = client.post(f"/api/scope-items/{item['id']}/events", json={})
    assert res.status_code == 400


def test_delete_manual_note(client):
    item = _design_item(client)
    created = client.post(f"/api/scope-items/{item['id']}/events", json={"note": "x"}).get_json()
    res = client.delete(f"/api/scope-items/events/{created['id']}")
    assert res.status_code == 204
    assert client.get(f"/api/scope-items/{item['id']}/events").get_json() == []


def test_cannot_delete_a_change_event(client):
    item = _design_item(client)
    client.put(f"/api/scope-items/{item['id']}", json={"title": "New Title"})
    events = client.get(f"/api/scope-items/{item['id']}/events").get_json()
    change = next(e for e in events if e["kind"] == "change")
    res = client.delete(f"/api/scope-items/events/{change['id']}")
    assert res.status_code == 400


def test_item_detail_includes_events(client):
    item = _design_item(client)
    client.post(f"/api/scope-items/{item['id']}/events", json={"note": "context"})
    detail = client.get(f"/api/scope-items/{item['id']}").get_json()
    assert len(detail["events"]) == 1


def test_chat_without_ai_configured_returns_error(client):
    item = _design_item(client)
    res = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "hi"}], "item_id": item["id"],
    })
    assert res.status_code == 200
    body = res.get_json()
    assert body["reply"] == ""
    assert "not configured" in body["error"].lower()


def test_chat_short_circuits_before_validation_when_ai_not_configured(client):
    """Matches The Fixer's chat route: the not-configured check runs first, so a missing
    messages/item_id never gets far enough to be validated in this (default, AI-off) test
    environment — asserting that ordering here rather than the 400s, which would need
    AI_PROVIDER set to actually exercise."""
    res = client.post("/api/chat", json={"item_id": "x"})
    assert res.status_code == 200
    assert "not configured" in res.get_json()["error"].lower()
