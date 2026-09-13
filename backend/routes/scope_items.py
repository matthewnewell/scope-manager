from flask import Blueprint, jsonify, request

from db import db
from models import STATUSES, ScopeItem, ScopeProgressEvent, ancestor_chain

bp = Blueprint("scope_items", __name__, url_prefix="/api/scope-items")


@bp.get("")
def list_scope_items():
    """Flat list, filterable by `project`, `portfolio`, and `charge_number` — the same query
    shape Reckon will call (`?project=X&charge_number=Y`) to read a charge number's current
    earned-value signal. The frontend also uses this (unfiltered by charge_number, one project
    at a time) and builds the tree client-side from `parent_id` — small enough data per
    project that a lazy per-node fetch (Org Charts' approach) isn't worth the extra round trips
    here."""
    query = ScopeItem.query
    project = request.args.get("project")
    if project:
        query = query.filter(ScopeItem.project == project)
    portfolio = request.args.get("portfolio")
    if portfolio:
        query = query.filter(ScopeItem.portfolio == portfolio)
    charge_number = request.args.get("charge_number")
    if charge_number:
        query = query.filter(ScopeItem.charge_number == charge_number)
    items = query.order_by(ScopeItem.created_at).all()
    return jsonify([i.to_dict() for i in items])


@bp.get("/<item_id>")
def get_scope_item(item_id):
    item = ScopeItem.query.get_or_404(item_id)
    children = sorted(item.children, key=lambda c: c.created_at)
    return jsonify({
        **item.to_dict(),
        "ancestors": [a.to_dict(include_counts=False) for a in ancestor_chain(item)[:-1]],
        "children": [c.to_dict() for c in children],
        "progress_events": [e.to_dict() for e in item.progress_events],
    })


@bp.get("/projects")
def list_projects():
    rows = db.session.query(ScopeItem.project).distinct().all()
    return jsonify(sorted({r[0] for r in rows if r[0]}))


def _validate_create(body: dict) -> tuple[dict, int] | None:
    if not (body.get("title") or "").strip():
        return {"error": "title is required"}, 400
    if not (body.get("project") or "").strip():
        return {"error": "project is required"}, 400
    parent_id = body.get("parent_id")
    if parent_id and ScopeItem.query.get(parent_id) is None:
        return {"error": "parent_id does not refer to a real scope item"}, 400
    return None


@bp.post("")
def create_scope_item():
    body = request.get_json(force=True) or {}
    err = _validate_create(body)
    if err:
        return jsonify(err[0]), err[1]

    item = ScopeItem(
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


@bp.put("/<item_id>")
def update_scope_item(item_id):
    """Static fields only — title, description, charge number, external link. Status and
    percent never change here; that's what POST /<id>/progress is for. `parent_id` is
    deliberately not editable after creation in v1 — reparenting needs the same cycle guard
    Org Charts' manager_id update has, worth adding once someone actually needs to move a
    scope item, not before."""
    item = ScopeItem.query.get_or_404(item_id)
    body = request.get_json(force=True) or {}
    if "title" in body:
        if not (body.get("title") or "").strip():
            return jsonify({"error": "title is required"}), 400
        item.title = body["title"].strip()
    if "description" in body:
        item.description = (body.get("description") or "").strip() or None
    if "portfolio" in body:
        item.portfolio = (body.get("portfolio") or "").strip() or None
    if "charge_number" in body:
        item.charge_number = (body.get("charge_number") or "").strip() or None
    if "external_ref" in body:
        item.external_ref = (body.get("external_ref") or "").strip() or None
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
