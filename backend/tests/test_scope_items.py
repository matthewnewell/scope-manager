import os
import sys

os.environ["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "_tmp_data")
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


def _bracket_items(client):
    return client.get("/api/scope-items?project=Bracket Assembly Program").get_json()


def test_list_filters_by_project(client):
    items = _bracket_items(client)
    assert len(items) == 5  # 3 top-level + 2 children of Build & Integration
    assert all(i["project"] == "Bracket Assembly Program" for i in items)


def test_item_with_no_progress_events_is_honestly_not_started(client):
    items = _bracket_items(client)
    build = next(i for i in items if i["title"] == "Build & Integration")
    assert build["status"] == "not_started"
    assert build["percent_complete"] == 0
    assert build["last_update_note"] is None


def test_item_status_reflects_latest_progress_event(client):
    items = _bracket_items(client)
    design = next(i for i in items if i["title"] == "Design Definition")
    assert design["status"] == "done"
    assert design["percent_complete"] == 100


def test_get_item_includes_ancestors_children_and_history(client):
    items = _bracket_items(client)
    build = next(i for i in items if i["title"] == "Build & Integration")
    fixture = next(i for i in items if i["title"] == "Fixture Fabrication")

    detail = client.get(f"/api/scope-items/{fixture['id']}").get_json()
    assert [a["id"] for a in detail["ancestors"]] == [build["id"]]

    build_detail = client.get(f"/api/scope-items/{build['id']}").get_json()
    assert len(build_detail["children"]) == 2

    design = next(i for i in items if i["title"] == "Design Definition")
    design_detail = client.get(f"/api/scope-items/{design['id']}").get_json()
    assert len(design_detail["progress_events"]) == 2
    assert design_detail["progress_events"][0]["percent_complete"] == 40
    assert design_detail["progress_events"][1]["percent_complete"] == 100


def test_create_child_item(client):
    items = _bracket_items(client)
    build = next(i for i in items if i["title"] == "Build & Integration")

    created = client.post("/api/scope-items", json={
        "project": "Bracket Assembly Program",
        "title": "Paint & Finish",
        "parent_id": build["id"],
    })
    assert created.status_code == 201
    assert created.get_json()["parent_id"] == build["id"]

    build_detail = client.get(f"/api/scope-items/{build['id']}").get_json()
    assert build_detail["child_count"] == 3


def test_create_requires_title_and_project(client):
    res = client.post("/api/scope-items", json={"title": "No project"})
    assert res.status_code == 400
    res = client.post("/api/scope-items", json={"project": "X"})
    assert res.status_code == 400


def test_add_progress_requires_note(client):
    items = _bracket_items(client)
    procurement = next(i for i in items if i["title"] == "Long-Lead Procurement")
    res = client.post(f"/api/scope-items/{procurement['id']}/progress", json={
        "status": "done", "percent_complete": 100,
    })
    assert res.status_code == 400


def test_add_progress_rejects_bad_status_and_percent(client):
    items = _bracket_items(client)
    procurement = next(i for i in items if i["title"] == "Long-Lead Procurement")
    bad_status = client.post(f"/api/scope-items/{procurement['id']}/progress", json={
        "status": "almost_done", "percent_complete": 50, "note": "x",
    })
    assert bad_status.status_code == 400
    bad_percent = client.post(f"/api/scope-items/{procurement['id']}/progress", json={
        "status": "done", "percent_complete": 150, "note": "x",
    })
    assert bad_percent.status_code == 400


def test_add_progress_round_trip(client):
    items = _bracket_items(client)
    procurement = next(i for i in items if i["title"] == "Long-Lead Procurement")
    res = client.post(f"/api/scope-items/{procurement['id']}/progress", json={
        "status": "done", "percent_complete": 100, "note": "Casting received and accepted.",
        "author": "Sam Ortiz (PM)",
    })
    assert res.status_code == 201
    assert res.get_json()["status"] == "done"
    assert res.get_json()["percent_complete"] == 100

    detail = client.get(f"/api/scope-items/{procurement['id']}").get_json()
    assert len(detail["progress_events"]) == 2  # the seeded one + this one


def test_delete_blocked_when_item_has_children(client):
    items = _bracket_items(client)
    build = next(i for i in items if i["title"] == "Build & Integration")
    res = client.delete(f"/api/scope-items/{build['id']}")
    assert res.status_code == 400


def test_delete_leaf_item(client):
    items = _bracket_items(client)
    fixture = next(i for i in items if i["title"] == "Fixture Fabrication")
    res = client.delete(f"/api/scope-items/{fixture['id']}")
    assert res.status_code == 204
    assert client.get(f"/api/scope-items/{fixture['id']}").status_code == 404


def test_projects_endpoint_lists_both_seeded_projects(client):
    res = client.get("/api/scope-items/projects")
    assert res.status_code == 200
    assert set(res.get_json()) == {
        "Bracket Assembly Program",
        "Nacelle Fairing Retrofit",
    }
