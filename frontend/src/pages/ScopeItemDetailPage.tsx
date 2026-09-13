import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  useAddProgress,
  useCreateScopeItem,
  useDeleteScopeItem,
  useHealth,
  useScopeItem,
  useUpdateScopeItem,
} from '../api/hooks'
import { STATUSES, STATUS_LABEL } from '../api/types'
import type { ScopeStatus } from '../api/types'
import { getAuthor, relativeTime, setAuthor } from '../lib/author'
import Nav from '../components/Nav'
import StatusPill from '../components/StatusPill'
import Journal from '../components/Journal'
import ChatPanel from '../components/ChatPanel'
import './ScopeItemDetailPage.css'

export default function ScopeItemDetailPage() {
  const { itemId } = useParams<{ itemId: string }>()
  const { data: item, isLoading } = useScopeItem(itemId)
  const { data: health } = useHealth()
  const updateItem = useUpdateScopeItem(itemId ?? '')
  const deleteItem = useDeleteScopeItem()
  const navigate = useNavigate()
  const [chatOpen, setChatOpen] = useState(false)

  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [chargeNumber, setChargeNumber] = useState('')
  const [externalRef, setExternalRef] = useState('')
  const [author, setAuthorField] = useState(() => getAuthor())

  if (isLoading || !item) return <div className="scope-detail__loading">Loading…</div>

  function startEditing() {
    setTitle(item!.title)
    setDescription(item!.description ?? '')
    setChargeNumber(item!.charge_number ?? '')
    setExternalRef(item!.external_ref ?? '')
    setEditing(true)
  }

  function saveEdits() {
    setAuthor(author)
    updateItem.mutate(
      {
        title: title.trim(),
        description: description.trim() || undefined,
        charge_number: chargeNumber.trim() || undefined,
        external_ref: externalRef.trim() || undefined,
        author: author.trim() || undefined,
      },
      { onSuccess: () => setEditing(false) },
    )
  }

  function handleDelete() {
    if (!itemId) return
    if (!window.confirm(`Delete "${item!.title}"? This can't be undone.`)) return
    deleteItem.mutate(itemId, { onSuccess: () => navigate('/') })
  }

  return (
    <div className="scope-layout">
      <Nav />
      <div className="scope-layout__row">
        <div className="scope-detail">
          <div className="scope-detail__inner">
            <nav className="scope-detail__breadcrumb">
              <Link to="/">{item.project}</Link>
              {item.ancestors.map((a) => (
                <span key={a.id}>
                  {' '}/ <Link to={`/items/${a.id}`}>{a.title}</Link>
                </span>
              ))}
              {' '}/ <span className="scope-detail__breadcrumb-current">{item.title}</span>
            </nav>

            <header className="scope-detail__header">
              {!editing ? (
                <>
                  <div className="scope-detail__title-row">
                    <h1 className="scope-detail__title">{item.title}</h1>
                    <button className="sm-btn sm-btn--ghost" onClick={startEditing}>✎ Edit</button>
                  </div>
                  {item.description && <p className="scope-detail__desc">{item.description}</p>}
                  <div className="scope-detail__facts">
                    {item.charge_number && (
                      <span className="scope-detail__fact">
                        <span className="scope-detail__fact-label">Charge number</span>
                        <span className="scope-detail__fact-value scope-detail__fact-value--mono">{item.charge_number}</span>
                      </span>
                    )}
                    {item.external_ref && (
                      <span className="scope-detail__fact">
                        <span className="scope-detail__fact-label">External link</span>
                        <a className="scope-detail__fact-value" href={item.external_ref} target="_blank" rel="noopener noreferrer">
                          {item.external_ref}
                        </a>
                      </span>
                    )}
                  </div>
                </>
              ) : (
                <div className="scope-detail__edit-form">
                  <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" />
                  <textarea
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Description (optional)"
                  />
                  <div className="scope-detail__edit-row">
                    <input
                      value={chargeNumber}
                      onChange={(e) => setChargeNumber(e.target.value)}
                      placeholder="Charge number (optional)"
                    />
                    <input
                      value={externalRef}
                      onChange={(e) => setExternalRef(e.target.value)}
                      placeholder="External link — GitHub issue, Azure Boards item (optional)"
                    />
                  </div>
                  <div className="scope-detail__edit-row">
                    <input
                      value={author}
                      onChange={(e) => setAuthorField(e.target.value)}
                      placeholder="Your name (optional — attributed on the change in the journal below)"
                    />
                  </div>
                  <div className="scope-detail__edit-actions">
                    <button className="sm-btn sm-btn--primary" onClick={saveEdits} disabled={!title.trim() || updateItem.isPending}>
                      {updateItem.isPending ? 'Saving…' : 'Save'}
                    </button>
                    <button className="sm-btn sm-btn--ghost" onClick={() => setEditing(false)}>Cancel</button>
                  </div>
                </div>
              )}
            </header>

            <section className="scope-detail__section">
              <h2 className="scope-detail__section-title">Current status</h2>
              <div className="scope-status-card">
                <div className="scope-status-card__top">
                  <StatusPill status={item.status} />
                  <span className="scope-status-card__percent">{item.percent_complete}%</span>
                </div>
                {item.last_update_note ? (
                  <p className="scope-status-card__note">
                    “{item.last_update_note}”
                    <span className="scope-status-card__meta">
                      {' '}— {item.last_updated_by ?? 'someone'}
                      {item.last_updated_at && `, ${relativeTime(item.last_updated_at)}`}
                    </span>
                  </p>
                ) : (
                  <p className="scope-status-card__note scope-status-card__note--empty">
                    No progress recorded yet — this is an honest 0%, not a guess.
                  </p>
                )}
              </div>
              <ProgressForm itemId={item.id} />
              {item.progress_events.length > 0 && (
                <ul className="scope-history">
                  {[...item.progress_events].reverse().map((e) => (
                    <li key={e.id} className="scope-history__row">
                      <StatusPill status={e.status} />
                      <span className="scope-history__percent">{e.percent_complete}%</span>
                      <span className="scope-history__note">{e.note}</span>
                      <span className="scope-history__meta">{e.author ?? 'someone'} · {relativeTime(e.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="scope-detail__section">
              <h2 className="scope-detail__section-title">Children ({item.children.length})</h2>
              {item.children.length > 0 && (
                <ul className="scope-children-list">
                  {item.children.map((c) => (
                    <li key={c.id}>
                      <Link to={`/items/${c.id}`} className="scope-children-list__row">
                        <span className="scope-children-list__title">{c.title}</span>
                        <StatusPill status={c.status} />
                        <span className="scope-children-list__percent">{c.percent_complete}%</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              <AddChildForm project={item.project} parentId={item.id} />
            </section>

            <section className="scope-detail__section">
              <h2 className="scope-detail__section-title">Journal</h2>
              <Journal itemId={item.id} />
            </section>

            <footer className="scope-detail__footer">
              {item.children.length === 0 ? (
                <button className="sm-btn sm-btn--ghost scope-detail__delete" onClick={handleDelete} disabled={deleteItem.isPending}>
                  Delete this item
                </button>
              ) : (
                <p className="scope-detail__delete-hint">
                  Has {item.children.length} child item(s) — move or remove them first to delete this one.
                </p>
              )}
            </footer>
          </div>
        </div>

        {chatOpen ? (
          <ChatPanel
            itemId={item.id}
            aiConfigured={health?.ai_configured ?? false}
            onCollapse={() => setChatOpen(false)}
          />
        ) : (
          <button className="scope-layout__chat-tab" onClick={() => setChatOpen(true)} title="Open chat">
            ✨ Chat
          </button>
        )}
      </div>
    </div>
  )
}

function ProgressForm({ itemId }: { itemId: string }) {
  const addProgress = useAddProgress(itemId)
  const [status, setStatus] = useState<ScopeStatus>('in_progress')
  const [percent, setPercent] = useState(0)
  const [note, setNote] = useState('')
  const [author, setAuthorField] = useState(() => getAuthor())

  function submit() {
    if (!note.trim()) return
    setAuthor(author)
    addProgress.mutate(
      { status, percent_complete: percent, note: note.trim(), author: author.trim() || undefined },
      { onSuccess: () => setNote('') },
    )
  }

  return (
    <div className="progress-form">
      <div className="progress-form__row">
        <select value={status} onChange={(e) => setStatus(e.target.value as ScopeStatus)}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{STATUS_LABEL[s]}</option>
          ))}
        </select>
        <input
          type="number"
          min={0}
          max={100}
          value={percent}
          onChange={(e) => setPercent(Math.max(0, Math.min(100, Number(e.target.value))))}
        />
        <span className="progress-form__percent-sign">%</span>
      </div>
      <textarea
        rows={2}
        placeholder="What changed, and why? (required)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className="progress-form__row">
        <input
          placeholder="Your name (optional)"
          value={author}
          onChange={(e) => setAuthorField(e.target.value)}
        />
        <button className="sm-btn sm-btn--primary" onClick={submit} disabled={!note.trim() || addProgress.isPending}>
          {addProgress.isPending ? 'Recording…' : 'Record update'}
        </button>
      </div>
    </div>
  )
}

function AddChildForm({ project, parentId }: { project: string; parentId: string }) {
  const createItem = useCreateScopeItem()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [chargeNumber, setChargeNumber] = useState('')

  function submit() {
    if (!title.trim()) return
    createItem.mutate(
      { project, parent_id: parentId, title: title.trim(), charge_number: chargeNumber.trim() || undefined },
      { onSuccess: () => { setTitle(''); setChargeNumber(''); setOpen(false) } },
    )
  }

  if (!open) {
    return (
      <button className="sm-btn sm-btn--ghost" onClick={() => setOpen(true)}>+ Add child item</button>
    )
  }

  return (
    <div className="add-item-form">
      <input
        placeholder="Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && submit()}
        autoFocus
      />
      <input
        placeholder="Charge number (optional)"
        value={chargeNumber}
        onChange={(e) => setChargeNumber(e.target.value)}
      />
      <div className="add-item-form__actions">
        <button className="sm-btn sm-btn--primary" onClick={submit} disabled={!title.trim() || createItem.isPending}>
          {createItem.isPending ? 'Adding…' : 'Add'}
        </button>
        <button className="sm-btn sm-btn--ghost" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </div>
  )
}
