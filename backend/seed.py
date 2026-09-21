"""
Demo seed — one project's scope worked in real detail (a 3-item WBS, one item nested two
levels deep, a mix of statuses including one item with no progress recorded yet), one other
project with a single item so the project switcher isn't a dead end. Reuses the same demo
project/portfolio names Value Stream, Conway's Depot, DWMP, and The Fixer already share.
"""

from db import db
from models import ScopeItem, ScopeProgressEvent

_BKT = "Bracket Assembly Program"
_NAC = "Nacelle Fairing Retrofit"
_PORTFOLIO = "Industrial Programs"


def seed_if_empty():
    if ScopeItem.query.count() > 0:
        return

    # ── Bracket Assembly Program: three top-level scope items, one with two children ──
    design = ScopeItem(
        project=_BKT, portfolio=_PORTFOLIO,
        title="Design Definition", charge_number="CN-4471-10",
        description="Architecture through released drawing for the bracket assembly.",
        created_by="Sam Ortiz (PM)",
    )
    procurement = ScopeItem(
        project=_BKT, portfolio=_PORTFOLIO,
        title="Long-Lead Procurement", charge_number="CN-4471-20",
        description="Casting and long-lead hardware acquisition.",
        created_by="Sam Ortiz (PM)",
    )
    build = ScopeItem(
        project=_BKT, portfolio=_PORTFOLIO,
        title="Build & Integration", charge_number="CN-4471-30",
        description="Fixture fabrication through final assembly.",
        created_by="Sam Ortiz (PM)",
    )
    db.session.add_all([design, procurement, build])
    db.session.flush()

    fixture = ScopeItem(
        project=_BKT, portfolio=_PORTFOLIO, parent_id=build.id,
        title="Fixture Fabrication", charge_number="CN-4471-31",
        created_by="Sam Ortiz (PM)",
    )
    final_assembly = ScopeItem(
        project=_BKT, portfolio=_PORTFOLIO, parent_id=build.id,
        title="Final Assembly", charge_number="CN-4471-32",
        created_by="Sam Ortiz (PM)",
    )
    db.session.add_all([fixture, final_assembly])
    db.session.flush()

    # Design: a real history — in progress, then done, showing the judgment actually moved.
    db.session.add_all([
        ScopeProgressEvent(
            scope_item_id=design.id, status="in_progress", percent_complete=40,
            note="Architecture Definition complete, working System Requirements.",
            author="Sam Ortiz (PM)",
        ),
        ScopeProgressEvent(
            scope_item_id=design.id, status="done", percent_complete=100,
            note="Drawing released after CDR.",
            author="Sam Ortiz (PM)",
        ),
    ])

    # Procurement: one entry, in progress — the long-lead casting is the known dominant delay.
    db.session.add(ScopeProgressEvent(
        scope_item_id=procurement.id, status="in_progress", percent_complete=65,
        note="Casting on order, tracking the supplier's committed ship date.",
        author="Sam Ortiz (PM)",
    ))

    # Build, Fixture Fabrication, Final Assembly: intentionally no progress events yet — the
    # honest "not started, 0%" state, and what the empty-history UI looks like on first load.

    # ── Nacelle Fairing Retrofit: a single item so the project switcher isn't a dead end,
    # deliberately echoing The Fixer's NDT-hold demo incident (no shared data, just the same
    # story told from the scope side). ──
    ndt_fix = ScopeItem(
        project=_NAC, portfolio=_PORTFOLIO,
        title="NDT Process Improvement", charge_number="CN-5820-40",
        description="Cross-train a backup NDT inspector and add a long-lead procurement check.",
        created_by="Dana Kim (PM)",
    )
    db.session.add(ndt_fix)
    db.session.flush()
    db.session.add(ScopeProgressEvent(
        scope_item_id=ndt_fix.id, status="at_risk", percent_complete=30,
        note="Backup inspector certification scheduled but not complete — panels still queuing.",
        author="Dana Kim (PM)",
    ))

    db.session.commit()
