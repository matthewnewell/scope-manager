import { useState } from 'react'
import { useAddScopeEvent, useDeleteScopeEvent, useScopeItemEvents } from '../api/hooks'
import type { ScopeEvent } from '../api/types'
import { getAuthor, relativeTime, setAuthor } from '../lib/author'
import './Journal.css'

interface Group {
  key: string
  ts: string
  author: string | null
  changes: ScopeEvent[]
  note: ScopeEvent | null
}

/** Groups the flat event list back into "one save" clusters — events from a single edit share
 * created_at exactly, changes before the note. Ported from The Fixer's Journal, simplified:
 * every event here already belongs to one scope item, so there's no cross-target grouping or
 * jump-to-tab logic to carry along. */
function groupEvents(events: ScopeEvent[]): Group[] {
  const groups: Group[] = []
  const byKey = new Map<string, Group>()
  for (const e of events) {
    let g = byKey.get(e.created_at)
    if (!g) {
      g = { key: e.created_at, ts: e.created_at, author: e.author, changes: [], note: null }
      byKey.set(e.created_at, g)
      groups.push(g)
    }
    if (e.kind === 'change') g.changes.push(e)
    else g.note = e
  }
  return groups
}

export default function Journal({ itemId }: { itemId: string }) {
  const { data: events, isLoading } = useScopeItemEvents(itemId)
  const addEvent = useAddScopeEvent(itemId)
  const deleteEvent = useDeleteScopeEvent(itemId)

  const [text, setText] = useState('')
  const [name, setName] = useState(getAuthor())
  const author = getAuthor()

  function submit() {
    const note = text.trim()
    if (!note) return
    if (name.trim() && name.trim() !== author) setAuthor(name)
    addEvent.mutate(
      { note, author: name.trim() || author || undefined },
      { onSuccess: () => setText('') },
    )
  }

  const groups = groupEvents(events ?? [])

  return (
    <div className="journal">
      <div className="journal__composer">
        <textarea
          className="journal__input"
          rows={2}
          placeholder="What happened? A decision, a risk, context worth remembering…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
        />
        <div className="journal__composer-row">
          {!author && (
            <input
              className="journal__name"
              placeholder="your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          )}
          {author && <span className="journal__as">as {author}</span>}
          <button className="journal__add" onClick={submit} disabled={!text.trim() || addEvent.isPending}>
            {addEvent.isPending ? 'Adding…' : 'Add note'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <p className="journal__empty">Loading…</p>
      ) : groups.length === 0 ? (
        <p className="journal__empty">
          Nothing logged yet. Edits are recorded automatically; add a note for context that
          isn't a progress judgment itself.
        </p>
      ) : (
        <ol className="journal__feed">
          {groups.map((g) => (
            <li key={g.key} className="journal__entry">
              <div className="journal__meta">
                <span className="journal__author">{g.author || 'Someone'}</span>
                <span className="journal__time">{relativeTime(g.ts)}</span>
              </div>

              {g.changes.length > 0 && (
                <ul className="journal__changes">
                  {g.changes.map((c) => (
                    <li key={c.id}>
                      {c.field}: <span className="journal__old">{c.old_value}</span>
                      {' → '}
                      <span className="journal__new">{c.new_value}</span>
                    </li>
                  ))}
                </ul>
              )}

              {g.note && (
                <div className="journal__note">
                  <span>{g.note.note}</span>
                  <button className="journal__del" title="Delete this note" onClick={() => deleteEvent.mutate(g.note!.id)}>
                    ✕
                  </button>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
