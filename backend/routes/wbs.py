"""
The WBS, as other apps read it. Good Plan puts every labor line, material and ODC on one leaf of
this tree (a work package), and Reckon will line budget, progress and S4 actuals up per element.
The tree itself is edited in this app's own pages (routes/scope_items.py); this is the contract
for everyone else, plus the one write another app makes: bringing a pursuit's draft WBS over from
Good Plan once the work is awarded.
"""

from flask import Blueprint, jsonify, request

from db import db
from models import ScopeItem, code_key

bp = Blueprint("wbs", __name__, url_prefix="/api/wbs")


def _elements(items: list[ScopeItem]) -> list[dict]:
    parents = {i.parent_id for i in items if i.parent_id}
    return [
        {
            "id": i.id,
            "code": i.code,
            "title": i.title,
            "parent_id": i.parent_id,
            "charge_number": i.charge_number,
            "leaf": i.id not in parents,
            "status": i.status,
            "percent_complete": i.percent_complete,
            # Every recorded judgment, oldest first: Reckon reads earned value over time from it.
            "history": [
                {"at": e.created_at.isoformat(), "percent_complete": e.percent_complete, "status": e.status}
                for e in i.progress_events
            ],
        }
        for i in sorted(items, key=lambda i: (code_key(i.code), i.created_at))
    ]


@bp.get("")
def get_wbs():
    """`?project_id=` (a Depot project id) -> {project_id, elements}. `leaf` marks work packages,
    the only elements budget may sit on. An empty list means the project has no WBS here yet."""
    project_id = request.args.get("project_id")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    items = ScopeItem.query.filter_by(depot_project_id=project_id).all()
    return jsonify({"project_id": project_id, "elements": _elements(items)})


@bp.post("/import")
def import_wbs():
    """Create a project's WBS from a list of `{code, title}` (Good Plan's draft, at award).
    Parents come from the codes ("1.2" sits under "1"), so every parent code must be in the list.
    Only for a project with no scope here yet — never merges into an existing tree. Charge numbers
    stay blank: S4 assigns them once the project is set up there."""
    body = request.get_json(force=True) or {}
    project_id = (body.get("project_id") or "").strip()
    project = (body.get("project") or "").strip()
    elements = body.get("elements")
    if not project_id or not project:
        return jsonify({"error": "project_id and project are required"}), 400
    if not isinstance(elements, list) or not elements:
        return jsonify({"error": "elements must be a non-empty list of {code, title}"}), 400
    if ScopeItem.query.filter_by(depot_project_id=project_id).first() is not None:
        return jsonify({"error": "this project already has a WBS in Scope Manager"}), 409

    rows = []
    for e in elements:
        code = str(e.get("code") or "").strip()
        title = str(e.get("title") or "").strip()
        if not code or not title:
            return jsonify({"error": "every element needs a code and a title"}), 400
        rows.append((code, title))
    codes = [c for c, _ in rows]
    if len(set(codes)) != len(codes):
        return jsonify({"error": "WBS codes must be unique"}), 400
    for code in codes:
        if "." in code and code.rsplit(".", 1)[0] not in codes:
            return jsonify({"error": f"WBS {code} has no parent {code.rsplit('.', 1)[0]} in the list"}), 400

    by_code: dict[str, ScopeItem] = {}
    author = (body.get("author") or "").strip() or None
    for code, title in sorted(rows, key=lambda r: code_key(r[0])):
        parent = by_code.get(code.rsplit(".", 1)[0]) if "." in code else None
        item = ScopeItem(
            depot_project_id=project_id, project=project,
            portfolio=(body.get("portfolio") or "").strip() or None,
            code=code, title=title, parent_id=parent.id if parent else None, created_by=author,
        )
        db.session.add(item)
        db.session.flush()
        by_code[code] = item
    db.session.commit()
    return jsonify({"project_id": project_id, "elements": _elements(list(by_code.values()))}), 201
