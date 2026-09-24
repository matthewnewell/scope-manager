"""Journal capture — turns a scope-item edit into append-only ScopeEvent rows.

Ported from The Fixer's / Value Stream's journal.py: same shape, same reasoning. Progress
updates (status/percent_complete) are deliberately NOT logged here — those already go through
ScopeProgressEvent, which requires its own note and drives the item's current status. This
module only covers the item's other fields.
"""

from datetime import datetime, timezone

from db import db
from models import ScopeEvent

# field name -> label shown in the feed
SCOPE_ITEM_FIELDS = {
    "code": "WBS code",
    "title": "title",
    "description": "description",
    "portfolio": "portfolio",
    "charge_number": "charge number",
    "external_ref": "external link",
}


def _fmt(value) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def record_changes(
    scope_item_id: str,
    before: dict,
    after: dict,
    fields: dict = SCOPE_ITEM_FIELDS,
    *,
    author: str | None = None,
    note: str | None = None,
) -> bool:
    """Append one 'change' event per field in `fields` that actually changed, plus one 'note'
    event if `note` was supplied. All events from one save share an exact timestamp so the feed
    can group them. Returns whether anything changed. Caller commits."""
    author = (author or "").strip() or None
    ts = datetime.now(timezone.utc)
    changed = False
    for field, label in fields.items():
        old, new = before.get(field), after.get(field)
        if old == new:
            continue
        changed = True
        db.session.add(
            ScopeEvent(
                scope_item_id=scope_item_id,
                created_at=ts,
                author=author,
                kind="change",
                field=label,
                old_value=_fmt(old),
                new_value=_fmt(new),
            )
        )
    if note and note.strip():
        db.session.add(
            ScopeEvent(
                scope_item_id=scope_item_id,
                created_at=ts,
                author=author,
                kind="note",
                note=note.strip(),
            )
        )
    return changed
