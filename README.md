# Scope Manager

A minimal work breakdown structure, and an honest place to record how done it really is.

## The idea

**Deliberately not Azure Boards or Jira.** No sprints, no kanban, no backlog grooming, no
GitHub/Azure Boards sync. Those are real products other teams have spent years building — this
ecosystem's own failure mode (BurnedValue) was trying to build one app that does everything.
For software work that already lives in GitHub Issues or Azure Boards, the plan is for Scope
Manager (or Reckon, the future project-execution dashboard, directly) to *read* that system's
status via its own API rather than re-implement it — not built here yet, `external_ref` is a
plain link-out for now. For everything else — hardware, manufacturing, anything with no
existing backlog tool — the model below is the whole native experience.

**One self-referential item, not a hardcoded Epic → Feature → Story taxonomy.** A `ScopeItem`
optionally has a `parent_id` pointing at another `ScopeItem` — nest as shallow or as deep as a
given project's scope actually calls for, in whatever vocabulary fits it. Same "plain
self-reference, no rigid schema" choice Org Charts made for reporting lines.

**Percent complete is always a person's judgment call — never computed.** Even where a
`ScopeItem` has a GitHub/Azure Boards link, a closed-issue count isn't the same thing as real
progress (the same "no fake precision" rule DWMP applies to dwell time and Good Plan applies to
FTE totals). So a `ScopeItem` carries no live status/percent columns of its own — its current
state is always the *latest* `ScopeProgressEvent`, the same way DWMP's current part status is
always computed from the latest snapshot rather than duplicated onto `Part`. Every update
requires a short note, so it's a deliberate act, not a slider dragged idly.

**Why this exists**: it's the narrowest thing that gives [Reckon](../reckon) (not built yet) the
one signal it actually needs — earned value (BCWP) per charge number, computed from a scope
item's percent complete. Sprints, kanban, and a real GitHub/Azure Boards sync are real future
ideas, worth keeping written down, but explicitly not this app's v1.

## Stack

Same as the rest of this ecosystem — Flask + SQLAlchemy + SQLite backend, React + TypeScript +
Vite frontend, no shared database, tied in only by Conway's Depot's registry entry and the
plain-text `project` label convention every sibling app uses.

## Running locally

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py            # :8097, seeds a small demo WBS on first run

# frontend (separate terminal)
cd frontend
npm install
npm run dev                        # :5183, proxies /api to :8097
```

## Data model

- **ScopeItem** — `project`/`portfolio` (plain-text labels, same convention as every sibling
  app), `title`, `description`, `parent_id` (self-referential, nullable), `charge_number`
  (nullable — the join key Reckon will use), `external_ref` (nullable link-out). No status or
  percent columns — see below.
- **ScopeProgressEvent** — one append-only row per judgment call: `status`, `percent_complete`,
  a required `note`, `author`, `created_at`. A `ScopeItem`'s current status/percent is always
  its latest event; an item with none yet is honestly "not started, 0%."
- **ScopeEvent** — the item's journal, separate from `ScopeProgressEvent` on purpose: this is
  the general log (auto-captured field edits — title, description, charge number, external
  link — plus freestanding manual notes), not the specific required-note "how done is this"
  record that drives status/percent. Same shape as The Fixer's `IncidentEvent`. "Change" rows
  are permanent; manual "note" rows can be deleted.
- An item can't be deleted while it still has children (move or remove them first).
  `parent_id` isn't editable after creation in v1 — reparenting would need the same cycle guard
  Org Charts' `manager_id` update has, worth adding once something actually needs to move a
  scope item.

## API surface Reckon will use

`GET /api/scope-items?project=X&charge_number=Y` — current status/percent (and everything else)
for whatever matches. That's the entire contract between the two apps; Reckon never writes here.

## AI chat

A persistent pane scoped to one scope item — ported ~verbatim from The Fixer's/Value Stream's
`ai_client.py` (Claude/Gemini/Ollama, off by default via `AI_PROVIDER=none`). Helps write a
clearer title/description and a progress note that actually says what changed, and will push
back if a recorded percent doesn't seem to match its own note. It never invents or suggests a
status/percent itself, and never treats a linked GitHub/Azure Boards issue as a progress source
— consistent with the "judgment, not automation" rule the whole app is built around.

## Status

v1 — tree view + item detail, add/edit/delete, recording progress updates with history, a
journal (auto-captured edits + manual notes), and an optional AI chat pane. Seeded with a small
demo WBS (3 top-level items on one project, one nested two levels deep, one item deliberately
left with no progress recorded to show the honest empty state) plus a single item on a second
project so the project switcher isn't a dead end.
