"""
Demo seed: the WBS for each awarded demo project, keyed by its Conway's Depot id. The codes are
the same ones Good Plan's demo plans budget against (1.x program and engineering, 2.x production,
3.x mission assurance and test), and each work package's charge number follows the same
project-plus-WBS pattern Labor Supply & Demand's mocked S4 actuals use (CN-4471 + "1.2" ->
CN-4471-12), so a line budgeted in Good Plan, the scope it belongs to here, and what people
charge in S4 all meet on one element.

Pursuits have no WBS here: their draft WBS lives in Good Plan until the work is awarded.
Progress is a mix on purpose: some work packages have a history, some are at risk, most of
production is honestly not started.
"""

from datetime import datetime, timedelta, timezone

from db import db
from models import ScopeItem, ScopeProgressEvent

TITLES = {
    "1": "Program & Engineering",
    "1.1": "Program Management",
    "1.2": "Systems Engineering",
    "1.3": "Design Engineering",
    "1.4": "Manufacturing Engineering & Tooling",
    "1.5": "Supply Chain & Procurement",
    "2": "Production",
    "2.1": "Fabrication & Assembly",
    "2.2": "Inspection",
    "2.3": "Special Processes (Heat Treat & NDT)",
    "2.4": "Finishing",
    "3": "Mission Assurance & Test",
    "3.1": "Mission Assurance",
    "3.2": "Test",
}

# (depot id, name, portfolio, charge-number base, work packages,
#  {code: [(status, pct, note, author, days ago)]}) -- dated, so earned value has a history
PROJECTS = [
    # Bracket: on schedule, but running over cost (see Reckon's mocked actuals: tooling overruns).
    (
        "ff5bfe0b-7b18-4337-a464-6517c6f6c13b", "Bracket Assembly Project", "Industrial Programs", "CN-4471",
        ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "3.1"],
        {
            "1.1": [("in_progress", 3, "Kickoff held; IMS baselined.", "Sam Ortiz (PM)", 20),
                    ("in_progress", 7, "Monthly review cadence set with Acme.", "Sam Ortiz (PM)", 4)],
            "1.2": [("in_progress", 15, "Architecture defined, working system requirements.", "Sam Ortiz (PM)", 17),
                    ("in_progress", 37, "Requirements baselined at SRR; PDR package in work.", "Sam Ortiz (PM)", 4)],
            "1.3": [("in_progress", 15, "Bracket body model through first stress pass.", "Sam Ortiz (PM)", 6)],
            "1.4": [("at_risk", 0, "Long-lead casting drives the fixture design; supplier date not yet committed.", "Sam Ortiz (PM)", 3)],
        },
    ),
    # Nacelle: healthy, a little ahead.
    (
        "35fe3413-20e9-4762-8828-029ecade70c2", "Nacelle Fairing Retrofit", "Industrial Programs", "CN-5820",
        ["1.1", "1.3", "2.1", "2.2", "3.1"],
        {
            "1.1": [("in_progress", 10, "Kickoff and fleet survey plan agreed with the customer.", "Dana Kim (PM)", 6)],
            "1.3": [("in_progress", 15, "Damage survey of the first fairings complete.", "Dana Kim (PM)", 12),
                    ("in_progress", 32, "Repair scheme drafted; customer engineering review next week.", "Dana Kim (PM)", 5)],
            # The Fixer's NDT-hold case, told from the scope side: inspection hasn't started, but the
            # backup inspector it depends on isn't certified yet.
            "2.2": [("at_risk", 0, "Backup NDT inspector certification not yet scheduled; panels will queue when inspection starts.", "Dana Kim (PM)", 2)],
        },
    ),
    # Radar: behind schedule, waiting on the titanium forging.
    (
        "2a9c5e71-84d3-4f0b-b6a2-c13e7d9f5a08", "Radar Housing Production", "Defense Systems", "CN-6103",
        ["1.1", "1.2", "1.3", "1.4", "1.5", "2.1", "2.2", "2.4", "3.1", "3.2"],
        {
            "1.1": [("in_progress", 9, "Monthly customer reviews under way.", "Dana Kim (PM)", 9)],
            "1.2": [("in_progress", 30, "Interface requirements baselined.", "Dana Kim (PM)", 20),
                    ("at_risk", 50, "Harness interface still open with the customer; holding SRR close-out.", "Dana Kim (PM)", 5)],
            "1.3": [("in_progress", 30, "Housing drawings released; harness routing in work.", "Dana Kim (PM)", 8)],
            "1.4": [("at_risk", 3, "Machining fixtures waiting on forging dimensions.", "Dana Kim (PM)", 6)],
            "1.5": [("at_risk", 15, "Titanium forging expedite requested; supplier holding a 3-week slip.", "Dana Kim (PM)", 6)],
        },
    ),
]


def _charge(base: str, code: str) -> str:
    return f"{base}-{code.replace('.', '')}"


def seed_if_empty():
    if ScopeItem.query.count() > 0:
        return

    for project_id, name, portfolio, base, leaves, progress in PROJECTS:
        codes = sorted({c.split(".")[0] for c in leaves}) + leaves
        by_code: dict[str, ScopeItem] = {}
        for code in codes:
            parent = by_code.get(code.split(".")[0]) if "." in code else None
            item = ScopeItem(
                depot_project_id=project_id, project=name, portfolio=portfolio,
                code=code, title=TITLES[code], parent_id=parent.id if parent else None,
                # Only work packages are charged against; the grouping elements aren't.
                charge_number=_charge(base, code) if "." in code else None,
                created_by="Sam Ortiz (PM)",
            )
            db.session.add(item)
            db.session.flush()
            by_code[code] = item
        for code, events in progress.items():
            for status, pct, note, author, ago in events:
                db.session.add(ScopeProgressEvent(
                    scope_item_id=by_code[code].id, status=status, percent_complete=pct, note=note, author=author,
                    created_at=datetime.now(timezone.utc) - timedelta(days=ago),
                ))
    db.session.commit()
