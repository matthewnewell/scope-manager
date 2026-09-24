from flask import Blueprint, jsonify, request

import depot_client
import journal
from db import db
from models import STATUSES, ScopeEvent, ScopeItem, ScopeProgressEvent, ancestor_chain, code_key, next_child_code

bp = Blueprint("scope_items", __name__, url_prefix="/api/scope-items")


@bp.get("")
def list_scope_items():
    """Flat list in WBS-code order, filterable by `project_id` (a Depot project id), `project`
    (name, kept for older callers), `portfolio`, and `charge_number` — the query shape Reckon
    will call to read a charge number's current earned-value signal. The frontend fetches one
    project at a time and builds the tree client-side from `parent_id`."""
    query = ScopeItem.query
    project_id = request.args.get("project_id")
    if project_id:
        query = query.filter(ScopeItem.depot_project_id == project_id)
    project = request.args.get("project")
    if project:
        query = query.filter(ScopeItem.project == project)
    portfolio = request.args.get("portfolio")
    if portfolio:
        query = query.filter(ScopeItem.portfolio == portfolio)
    charge_number = request.args.get("charge_number")
    if charge_number:
        query = query.filter(ScopeItem.charge_number == charge_number)
    items = sorted(query.all(), key=lambda i: (code_key(i.code), i.created_at))
    return jsonify([i.to_dict() for i in items])


@bp.get("/<item_id>")
def get_scope_item(item_id):
    item = ScopeItem.query.get_or_404(item_id)
    children = sorted(item.children, key=lambda c: (code_key(c.code), c.created_at))
    return jsonify({
        **item.to_dict(),
        "ancestors": [a.to_dict(include_counts=False) for a in ancestor_chain(item)[:-1]],
        "children": [c.to_dict() for c in children],
        "progress_events": [e.to_dict() for e in item.progress_events],
        "events": [e.to_dict() for e in ScopeEvent.query.filter_by(scope_item_id=item.id).order_by(ScopeEvent.created_at.desc(), ScopeEvent.kind.asc(), ScopeEvent.id.asc()).all()],
    })


@bp.get("/projects")
def list_projects():
    """Projects for the picker: every Depot project (so one with no scope yet can get a WBS),
    each with how many scope items it has. Awarded work first; pursuits carry their phase so the
    page can say their draft WBS lives in Good Plan until award. If the Depot is down, the
    projects that already have scope here."""
    counts: dict[str, int] = {}
    names: dict[str, str] = {}
    for item in ScopeItem.query.all():
        if item.depot_project_id:
            counts[item.depot_project_id] = counts.get(item.depot_project_id, 0) + 1
            names[item.depot_project_id] = item.project
    depot = depot_client.fetch_projects()
    if depot is None:
        rows = [{"id": pid, "name": names[pid], "phase": None, "portfolio": None, "item_count": n} for pid, n in counts.items()]
    else:
        rows = [
            {
                "id": p["id"], "name": p["name"], "phase": p.get("phase"),
                "portfolio": p.get("portfolio_name"), "item_count": counts.get(p["id"], 0),
            }
            for p in depot
        ]
    rows.sort(key=lambda r: (r["item_count"] == 0, r["phase"] == "pursuit", r["name"]))
    return jsonify({"projects": rows, "depot_reachable": depot is not None})


def _validate_create(body: dict) -> tuple[dict, int] | None:
    if not (body.get("title") or "").strip():
        return {"error": "title is required"}, 400
    if not (body.get("project_id") or "").strip():
        return {"error": "project_id (the Depot project id) is required"}, 400
    if not (body.get("project") or "").strip():
        return {"error": "project (its name) is required"}, 400
    parent_id = body.get("parent_id")
    if parent_id:
        parent = db.session.get(ScopeItem, parent_id)
        if parent is None:
            return {"error": "parent_id does not refer to a real scope item"}, 400
        if parent.depot_project_id != body["project_id"]:
            return {"error": "parent_id belongs to a different project"}, 400
    code = (body.get("code") or "").strip()
    if code and _code_taken(body["project_id"], code):
        return {"error": f"WBS {code} is already used in this project"}, 400
    return None


def _code_taken(project_id: str, code: str, except_id: str | None = None) -> bool:
    q = ScopeItem.query.filter_by(depot_project_id=project_id, code=code)
    return any(i.id != except_id for i in q.all())


@bp.post("")
def create_scope_item():
    body = request.get_json(force=True) or {}
    err = _validate_create(body)
    if err:
        return jsonify(err[0]), err[1]

    parent = db.session.get(ScopeItem, body["parent_id"]) if body.get("parent_id") else None
    siblings = ScopeItem.query.filter_by(depot_project_id=body["project_id"], parent_id=parent.id if parent else None).all()
    item = ScopeItem(
        depot_project_id=body["project_id"].strip(),
        code=(body.get("code") or "").strip() or next_child_code(parent, siblings),
        project=body["project"].strip(),
        portfolio=(body.get("portfolio") or "").strip() or None,
        title=body["title"].strip(),
        description=(body.get("description") or "").strip() or None,
        parent_id=body.get("parent_id") or None,
        charge_number=(body.get("charge_number") or "").strip() or None,
        external_ref=(body.get("external_ref") or "").strip() or None,
        created_by=(body.get("created_by") or "").strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


def _journal_snapshot(item: ScopeItem) -> dict:
    return {f: getattr(item, f) for f in journal.SCOPE_ITEM_FIELDS}


@bp.put("/<item_id>")
def update_scope_item(item_id):
    """Static fields only — title, description, charge number, external link. Status and
    percent never change here; that's what POST /<id>/progress is for. `parent_id` is
    deliberately not editable after creation in v1 — reparenting needs the same cycle guard
    Org Charts' manager_id update has, worth adding once someone actually needs to move a
    scope item, not before.

    Every changed field is auto-logged to the journal; an optional `journal_note` (plus
    `author`) is recorded alongside it in the same save — see journal.py."""
    item = ScopeItem.query.get_or_404(item_id)
    body = request.get_json(force=True) or {}
    before = _journal_snapshot(item)

    if "title" in body:
        if not (body.get("title") or "").strip():
            return jsonify({"error": "title is required"}), 400
        item.title = body["title"].strip()
    if "description" in body:
        item.description = (body.get("description") or "").strip() or None
    if "portfolio" in body:
        item.portfolio = (body.get("portfolio") or "").strip() or None
    if "code" in body:
        code = (body.get("code") or "").strip()
        if not code:
            return jsonify({"error": "a WBS code can't be blank"}), 400
        if _code_taken(item.depot_project_id, code, item.id):
            return jsonify({"error": f"WBS {code} is already used in this project"}), 400
        item.code = code
    if "charge_number" in body:
        item.charge_number = (body.get("charge_number") or "").strip() or None
    if "external_ref" in body:
        item.external_ref = (body.get("external_ref") or "").strip() or None

    journal.record_changes(
        item.id, before, _journal_snapshot(item),
        author=body.get("author"), note=body.get("journal_note"),
    )

    db.session.commit()
    return jsonify(item.to_dict())


@bp.delete("/<item_id>")
def delete_scope_item(item_id):
    item = ScopeItem.query.get_or_404(item_id)
    if item.children:
        return jsonify({
            "error": f'"{item.title}" has {len(item.children)} child item(s) — move or remove them first.',
        }), 400
    db.session.delete(item)
    db.session.commit()
    return "", 204


@bp.post("/<item_id>/progress")
def add_progress(item_id):
    """The only way status/percent_complete ever change — a deliberate, noted judgment call,
    not a field flip. `note` is required on purpose (see models.py)."""
    item = ScopeItem.query.get_or_404(item_id)
    body = request.get_json(force=True) or {}

    status = body.get("status")
    if status not in STATUSES:
        return jsonify({"error": f"status must be one of {', '.join(STATUSES)}"}), 400

    percent = body.get("percent_complete")
    if not isinstance(percent, int) or not (0 <= percent <= 100):
        return jsonify({"error": "percent_complete must be an integer 0-100"}), 400

    note = (body.get("note") or "").strip()
    if not note:
        return jsonify({"error": "note is required — say what changed and why"}), 400

    event = ScopeProgressEvent(
        scope_item_id=item.id,
        status=status,
        percent_complete=percent,
        note=note,
        author=(body.get("author") or "").strip() or None,
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(item.to_dict()), 201


# ── Journal ──────────────────────────────────────────────────────────────────────────────────

@bp.get("/<item_id>/events")
def list_events(item_id):
    """The item's journal, newest first (within one save, changes before the note)."""
    ScopeItem.query.get_or_404(item_id)
    events = (
        ScopeEvent.query.filter_by(scope_item_id=item_id)
        .order_by(ScopeEvent.created_at.desc(), ScopeEvent.kind.asc(), ScopeEvent.id.asc())
        .all()
    )
    return jsonify([e.to_dict() for e in events])


@bp.post("/<item_id>/events")
def add_event(item_id):
    """Add a manual note — a decision, a risk, context that isn't itself a progress judgment.
    Auto-captured 'change' events are written by the PUT route above, not here."""
    ScopeItem.query.get_or_404(item_id)
    body = request.get_json(force=True) or {}
    note = (body.get("note") or "").strip()
    if not note:
        return jsonify({"error": "note is required"}), 400

    ev = ScopeEvent(
        scope_item_id=item_id,
        kind="note",
        note=note,
        author=(body.get("author") or "").strip() or None,
    )
    db.session.add(ev)
    db.session.commit()
    return jsonify(ev.to_dict()), 201


@bp.delete("/events/<event_id>")
def delete_event(event_id):
    """Remove a manual note (a typo, a wrong call). 'change' history is permanent."""
    ev = ScopeEvent.query.get_or_404(event_id)
    if ev.kind != "note":
        return jsonify({"error": "only manual notes can be deleted; change history is permanent"}), 400
    db.session.delete(ev)
    db.session.commit()
    return "", 204
