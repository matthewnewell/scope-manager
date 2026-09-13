"""
Scope Manager: a minimal work-breakdown structure and a place to record honest progress
judgments against it — the narrowest version of "epics/features/stories" that still gives
Reckon (the future project-execution dashboard) the one signal it actually needs: earned value
(BCWP) per charge number.

**Deliberately not Azure Boards / Jira.** No sprints, no kanban, no backlog grooming, no
GitHub/Azure Boards sync. Those are real products other teams have spent years building; this
ecosystem's own failure mode (BurnedValue) was trying to build one app that does everything.
For software work that already lives in GitHub Issues or Azure Boards, the plan is for Scope
Manager (or Reckon directly) to *read* that system's status via its own API rather than
re-implement it — not built here, `external_ref` is a plain link-out for now. For everything
else (hardware, manufacturing, anything with no existing backlog tool), the model below is the
whole native experience.

**One self-referential table, not a hardcoded Epic → Feature → Story taxonomy.** A `ScopeItem`
optionally has a `parent_id` pointing at another `ScopeItem` — nest as shallow or as deep as a
given project's scope actually calls for, in whatever vocabulary fits it (a manufacturing WBS
doesn't naturally speak "epic/story"). Same "plain self-reference, no rigid schema" choice Org
Charts made for reporting lines.

**Percent complete is always a person's judgment call — never computed.** Even where a
`ScopeItem` has a GitHub/Azure Boards link, a closed-issue count is not the same thing as real
progress (the same "no fake precision" rule DWMP applies to dwell time and Good Plan applies to
FTE totals: a number nobody actually knows isn't shown as one that's known). So a `ScopeItem`
carries no live status/percent_complete columns of its own — its current state is always the
*latest* `ScopeProgressEvent`, the same way DWMP's current status is always computed from the
latest `StatusSnapshot` rather than duplicated onto `Part`. A freshly created item with no
events yet is honestly "not started, 0%," not a stored default masquerading as an update.
"""

from datetime import datetime, timezone

from db import _uuid, db

STATUSES = ("not_started", "in_progress", "at_risk", "done")


def _now():
    return datetime.now(timezone.utc)


class ScopeItem(db.Model):
    __tablename__ = "scope_item"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    project = db.Column(db.String(200), nullable=False, index=True)
    portfolio = db.Column(db.String(200), nullable=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    parent_id = db.Column(db.String(36), db.ForeignKey("scope_item.id"), nullable=True, index=True)
    # The join key Reckon needs to line this item's earned value up against S4 actuals (ACWP).
    # Nullable — plenty of scope items (a container/epic-ish grouping node, say) won't carry a
    # charge number of their own; only the leaf work actually charged against one does.
    charge_number = db.Column(db.String(80), nullable=True, index=True)
    # A link out to a GitHub issue / Azure Boards item, informational only — never a status
    # source. See the module docstring.
    external_ref = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    parent = db.relationship("ScopeItem", remote_side=[id], backref="children")
    progress_events = db.relationship(
        "ScopeProgressEvent",
        backref="scope_item",
        cascade="all, delete-orphan",
        order_by="ScopeProgressEvent.created_at",
    )

    @property
    def latest_progress(self) -> "ScopeProgressEvent | None":
        return self.progress_events[-1] if self.progress_events else None

    @property
    def status(self) -> str:
        latest = self.latest_progress
        return latest.status if latest else "not_started"

    @property
    def percent_complete(self) -> int:
        latest = self.latest_progress
        return latest.percent_complete if latest else 0

    def to_dict(self, include_counts: bool = True) -> dict:
        latest = self.latest_progress
        d = {
            "id": self.id,
            "project": self.project,
            "portfolio": self.portfolio,
            "title": self.title,
            "description": self.description,
            "parent_id": self.parent_id,
            "charge_number": self.charge_number,
            "external_ref": self.external_ref,
            "created_by": self.created_by,
            "status": self.status,
            "percent_complete": self.percent_complete,
            "last_update_note": latest.note if latest else None,
            "last_updated_by": latest.author if latest else None,
            "last_updated_at": latest.created_at.isoformat() if latest else None,
        }
        if include_counts:
            d["child_count"] = len(self.children)
        return d


class ScopeProgressEvent(db.Model):
    """One recorded judgment call: "as of now, this item is X% done, status Y" — plus a
    required note, so updating this is always a small deliberate act, not a slider dragged
    idly. Append-only; nothing here is ever edited or deleted once recorded, same as this
    ecosystem's other journals (The Fixer's IncidentEvent, Conway's Depot's MapEvent)."""

    __tablename__ = "scope_progress_event"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    scope_item_id = db.Column(db.String(36), db.ForeignKey("scope_item.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    percent_complete = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scope_item_id": self.scope_item_id,
            "status": self.status,
            "percent_complete": self.percent_complete,
            "note": self.note,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
        }


class ScopeEvent(db.Model):
    """The item's journal — separate from `ScopeProgressEvent` on purpose. ScopeProgressEvent
    is the specific, required-note record of "how done is this" that drives `status`/
    `percent_complete`; this is the general log of everything else worth remembering about an
    item: auto-captured field edits (title, description, charge number, external link) and
    freestanding manual notes (a decision, a risk, context that isn't a progress judgment
    itself). Same shape and reasoning as The Fixer's IncidentEvent / Value Stream's MapEvent.
    Nothing here is ever updated; "change" rows are never deleted, only manual "note" rows can
    be removed (a typo, a wrong call)."""

    __tablename__ = "scope_event"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    scope_item_id = db.Column(db.String(36), db.ForeignKey("scope_item.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)
    author = db.Column(db.String(120), nullable=True)

    kind = db.Column(db.String(20), nullable=False, default="note")  # "note" | "change"

    # kind="change" only — the auto-captured diff, already formatted for display.
    field = db.Column(db.String(60), nullable=True)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)

    # kind="note" only.
    note = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scope_item_id": self.scope_item_id,
            "created_at": self.created_at.isoformat(),
            "author": self.author,
            "kind": self.kind,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "note": self.note,
        }


def ancestor_chain(item: ScopeItem) -> list[ScopeItem]:
    """Root-to-self chain for the breadcrumb — same cycle guard as Org Charts' version, so a
    corrupted parent_id can never hang the app in a loop."""
    chain: list[ScopeItem] = []
    seen: set[str] = set()
    node: ScopeItem | None = item
    while node is not None and node.id not in seen:
        chain.append(node)
        seen.add(node.id)
        node = node.parent
    chain.reverse()
    return chain
