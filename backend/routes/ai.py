"""
Chat assist — same shape as Value Stream's / Conway's Depot's / The Fixer's: stateless (the
frontend owns history, resending it each call), context rebuilt fresh from the database every
time so an edit or a new progress update mid-conversation shows up in the next reply without
restarting the chat.

One persistent pane scoped to a single scope item, not a per-field "AI Suggest" button — that
pattern was tried and pulled back out of Value Stream in favor of exactly this shape.
"""

from flask import Blueprint, jsonify, request

import ai_client
from models import ScopeItem, ancestor_chain

bp = Blueprint("ai", __name__, url_prefix="/api")

SYSTEM_PROMPT = """You are the assistant embedded in Scope Manager, a minimal work-breakdown
and progress-tracking tool. It is deliberately not Azure Boards or Jira — no sprints, no
kanban — just a scope item, optionally nested under a parent, with a percent-complete history
that's always a recorded human judgment, never computed from a linked GitHub/Azure Boards
issue.

Your job:
- Help write a clear, specific scope item title and description — specific enough that someone
  unfamiliar with the project could tell what "done" looks like for it.
- When someone is about to record a progress update, help them write a note that actually says
  what changed and why, not a placeholder like "in progress" or "working on it." Push back
  gently on a percent-complete number that doesn't seem to match its own note (e.g. "65%,
  haven't started yet").
- If asked, help decide whether an item's charge number setup makes sense — a leaf item doing
  real charged work usually has one; a container/grouping item usually doesn't need one of its
  own.
- Never invent a percent-complete or status yourself, and never suggest treating an external
  link (GitHub issue, Azure Boards item) as a source of truth for how done something is — that
  is a deliberate rule of this app, not an oversight.

Never invent facts about this item that aren't in the context below."""


def _build_context(item: ScopeItem) -> str:
    ancestors = ancestor_chain(item)[:-1]
    lines = [f'Scope item: "{item.title}" (status: {item.status}, {item.percent_complete}%)']
    lines.append(f"Project: {item.project}")
    if ancestors:
        lines.append("Under: " + " > ".join(a.title for a in ancestors))
    if item.description:
        lines.append(f"Description: {item.description}")
    if item.charge_number:
        lines.append(f"Charge number: {item.charge_number}")
    if item.external_ref:
        lines.append(f"External link: {item.external_ref}")

    lines.append("\nProgress history so far:")
    if item.progress_events:
        for e in item.progress_events:
            lines.append(f"  [{e.status}, {e.percent_complete}%] {e.note} ({e.author or 'unattributed'})")
    else:
        lines.append("  (none yet — an honest 0%, not started)")

    children = sorted(item.children, key=lambda c: c.created_at)
    lines.append(f"\nChildren ({len(children)}):")
    if children:
        for c in children:
            lines.append(f"  - {c.title} [{c.status}, {c.percent_complete}%]")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


@bp.post("/chat")
def chat():
    if not ai_client.is_configured():
        return jsonify({"reply": "", "error": ai_client.NOT_CONFIGURED_MESSAGE})

    body = request.get_json(force=True) or {}
    messages = body.get("messages") or []
    if not messages:
        return jsonify({"error": "messages is required"}), 400

    item_id = body.get("item_id")
    if not item_id:
        return jsonify({"error": "item_id is required"}), 400
    item = ScopeItem.query.get_or_404(item_id)

    system = SYSTEM_PROMPT + "\n\n" + _build_context(item)
    reply = ai_client.chat(messages, system=system, max_tokens=1024)
    return jsonify({"reply": reply})
