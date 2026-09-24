import os
import sys

os.environ["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "_tmp_data")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import shutil

import pytest

import depot_client
from app import create_app
from db import db

BRACKET = "ff5bfe0b-7b18-4337-a464-6517c6f6c13b"
COASTAL = "d4e7a1b9-5c28-4360-9f1a-e83b0c6d72f5"
DEPOT = [
    {"id": BRACKET, "name": "Bracket Assembly Project", "phase": "execution", "portfolio_name": "Industrial Programs"},
    {"id": COASTAL, "name": "Prospect: Coastal Patrol Recompete", "phase": "pursuit", "portfolio_name": "Defense Systems"},
]


@pytest.fixture()
def client(monkeypatch):
    shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)
    monkeypatch.setattr(depot_client, "fetch_projects", lambda: DEPOT)
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.session.remove()
    shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)


def _bracket(client):
    return {i["code"]: i for i in client.get(f"/api/scope-items?project_id={BRACKET}").get_json()}


def test_list_filters_by_project_id_in_code_order(client):
    items = client.get(f"/api/scope-items?project_id={BRACKET}").get_json()
    assert [i["code"] for i in items] == ["1", "1.1", "1.2", "1.3", "1.4", "2", "2.1", "2.2", "2.3", "3", "3.1"]
    assert all(i["depot_project_id"] == BRACKET for i in items)


def test_work_packages_carry_charge_numbers_and_groupings_dont(client):
    items = _bracket(client)
    assert items["1.2"]["charge_number"] == "CN-4471-12"
    assert items["1"]["charge_number"] is None


def test_item_with_no_progress_events_is_honestly_not_started(client):
    fab = _bracket(client)["2.1"]
    assert fab["status"] == "not_started"
    assert fab["percent_complete"] == 0
    assert fab["last_update_note"] is None


def test_item_status_reflects_latest_progress_event(client):
    se = _bracket(client)["1.2"]
    assert se["status"] == "in_progress"
    assert se["percent_complete"] == 37


def test_get_item_includes_ancestors_children_and_history(client):
    items = _bracket(client)
    detail = client.get(f"/api/scope-items/{items['2.1']['id']}").get_json()
    assert [a["id"] for a in detail["ancestors"]] == [items["2"]["id"]]

    production = client.get(f"/api/scope-items/{items['2']['id']}").get_json()
    assert [c["code"] for c in production["children"]] == ["2.1", "2.2", "2.3"]

    se = client.get(f"/api/scope-items/{items['1.2']['id']}").get_json()
    assert [e["percent_complete"] for e in se["progress_events"]] == [15, 37]


def test_create_child_gets_the_next_code(client):
    production = _bracket(client)["2"]
    created = client.post("/api/scope-items", json={
        "project_id": BRACKET, "project": "Bracket Assembly Project",
        "title": "Paint & Finish", "parent_id": production["id"],
    })
    assert created.status_code == 201
    assert created.get_json()["code"] == "2.4"
    assert client.get(f"/api/scope-items/{production['id']}").get_json()["child_count"] == 4


def test_create_rejects_a_code_already_in_the_project(client):
    res = client.post("/api/scope-items", json={
        "project_id": BRACKET, "project": "Bracket Assembly Project", "title": "Dup", "code": "1.2",
    })
    assert res.status_code == 400


def test_create_requires_title_and_project_id(client):
    assert client.post("/api/scope-items", json={"title": "No project"}).status_code == 400
    assert client.post("/api/scope-items", json={"project_id": BRACKET, "project": "X"}).status_code == 400


def test_code_can_be_edited_but_not_to_a_taken_one(client):
    items = _bracket(client)
    assert client.put(f"/api/scope-items/{items['2.3']['id']}", json={"code": "2.1"}).status_code == 400
    res = client.put(f"/api/scope-items/{items['2.3']['id']}", json={"code": "2.9"})
    assert res.status_code == 200 and res.get_json()["code"] == "2.9"


def test_add_progress_requires_note(client):
    fab = _bracket(client)["2.1"]
    res = client.post(f"/api/scope-items/{fab['id']}/progress", json={"status": "done", "percent_complete": 100})
    assert res.status_code == 400


def test_add_progress_rejects_bad_status_and_percent(client):
    fab = _bracket(client)["2.1"]
    bad_status = client.post(f"/api/scope-items/{fab['id']}/progress", json={
        "status": "almost_done", "percent_complete": 50, "note": "x",
    })
    assert bad_status.status_code == 400
    bad_percent = client.post(f"/api/scope-items/{fab['id']}/progress", json={
        "status": "done", "percent_complete": 150, "note": "x",
    })
    assert bad_percent.status_code == 400


def test_add_progress_round_trip(client):
    tooling = _bracket(client)["1.4"]
    res = client.post(f"/api/scope-items/{tooling['id']}/progress", json={
        "status": "in_progress", "percent_complete": 30, "note": "Casting date committed.",
        "author": "Sam Ortiz (PM)",
    })
    assert res.status_code == 201
    assert res.get_json()["percent_complete"] == 30
    detail = client.get(f"/api/scope-items/{tooling['id']}").get_json()
    assert len(detail["progress_events"]) == 2  # the seeded one + this one


def test_delete_blocked_when_item_has_children(client):
    production = _bracket(client)["2"]
    assert client.delete(f"/api/scope-items/{production['id']}").status_code == 400


def test_delete_leaf_item(client):
    special = _bracket(client)["2.3"]
    assert client.delete(f"/api/scope-items/{special['id']}").status_code == 204
    assert client.get(f"/api/scope-items/{special['id']}").status_code == 404


def test_projects_lists_depot_projects_with_scope_first(client):
    res = client.get("/api/scope-items/projects").get_json()
    assert res["depot_reachable"]
    assert [p["id"] for p in res["projects"]] == [BRACKET, COASTAL]
    assert res["projects"][0]["item_count"] == 11 and res["projects"][1]["item_count"] == 0


# ── the WBS contract other apps read ─────────────────────────────────────────────────────────
def test_wbs_marks_work_packages(client):
    wbs = client.get(f"/api/wbs?project_id={BRACKET}").get_json()
    leaves = [e["code"] for e in wbs["elements"] if e["leaf"]]
    assert leaves == ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "3.1"]
    se = next(e for e in wbs["elements"] if e["code"] == "1.2")
    assert [h["percent_complete"] for h in se["history"]] == [15, 37]
    assert client.get("/api/wbs").status_code == 400


def test_import_builds_the_tree_from_codes(client):
    res = client.post("/api/wbs/import", json={
        "project_id": COASTAL, "project": "Prospect: Coastal Patrol Recompete",
        "elements": [{"code": "1", "title": "Engineering"}, {"code": "1.1", "title": "PM"}, {"code": "1.2", "title": "SE"}],
    })
    assert res.status_code == 201
    els = {e["code"]: e for e in res.get_json()["elements"]}
    assert els["1.1"]["parent_id"] == els["1"]["id"] and els["1.1"]["leaf"] and not els["1"]["leaf"]
    assert els["1.1"]["charge_number"] is None


def test_import_refuses_orphans_and_existing_trees(client):
    orphan = client.post("/api/wbs/import", json={
        "project_id": COASTAL, "project": "C", "elements": [{"code": "2.1", "title": "Fab"}],
    })
    assert orphan.status_code == 400
    existing = client.post("/api/wbs/import", json={
        "project_id": BRACKET, "project": "B", "elements": [{"code": "1", "title": "X"}],
    })
    assert existing.status_code == 409
