import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCreateScopeItem, useProjects, useScopeItems } from '../api/hooks'
import type { ScopeItem } from '../api/types'
import { getAuthor, setAuthor } from '../lib/author'
import StatusPill from '../components/StatusPill'
import './ScopeTreePage.css'

/** Groups a flat list by parent_id — the whole tree for one project is small enough to fetch
 * in one call and assemble client-side, unlike Org Charts' lazy per-node fetch. */
function groupByParent(items: ScopeItem[]): Map<string | null, ScopeItem[]> {
  const map = new Map<string | null, ScopeItem[]>()
  for (const item of items) {
    const key = item.parent_id
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(item)
  }
  return map
}

export default function ScopeTreePage() {
  const { data: projects } = useProjects()
  const [project, setProject] = useState<string | undefined>(undefined)

  useEffect(() => {
    if (!project && projects && projects.length > 0) setProject(projects[0])
  }, [projects, project])

  const { data: items, isLoading } = useScopeItems(project)
  const byParent = items ? groupByParent(items) : new Map<string | null, ScopeItem[]>()
  const roots = byParent.get(null) ?? []

  return (
    <div className="scope-tree-page">
      <header className="scope-tree-page__header">
        <h1 className="scope-tree-page__title">Scope</h1>
        {projects && projects.length > 1 && (
          <select
            className="scope-tree-page__project"
            value={project}
            onChange={(e) => setProject(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        )}
      </header>

      {isLoading && <p className="scope-tree-page__loading">Loading…</p>}

      {!isLoading && items && items.length === 0 && (
        <p className="scope-tree-page__loading">No scope items yet for this project.</p>
      )}

      {!isLoading && project && (
        <>
          <ul className="scope-tree scope-tree--root">
            {roots.map((item) => (
              <ScopeNode key={item.id} item={item} byParent={byParent} />
            ))}
          </ul>
          <AddItemForm project={project} />
        </>
      )}
    </div>
  )
}

function ScopeNode({ item, byParent }: { item: ScopeItem; byParent: Map<string | null, ScopeItem[]> }) {
  const [expanded, setExpanded] = useState(true)
  const kids = byParent.get(item.id) ?? []

  return (
    <li className="scope-node">
      <div className="scope-row">
        {kids.length > 0 ? (
          <button
            className="scope-row__toggle"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? '▾' : '▸'}
          </button>
        ) : (
          <span className="scope-row__toggle-spacer" />
        )}
        <Link to={`/items/${item.id}`} className="scope-row__link">
          <span className="scope-row__title">{item.title}</span>
          <StatusPill status={item.status} />
          <span className="scope-row__percent">{item.percent_complete}%</span>
          {item.charge_number && <span className="scope-row__charge">{item.charge_number}</span>}
          {kids.length > 0 && <span className="scope-row__count">{kids.length}</span>}
        </Link>
      </div>
      {expanded && kids.length > 0 && (
        <ul className="scope-tree">
          {kids.map((k) => (
            <ScopeNode key={k.id} item={k} byParent={byParent} />
          ))}
        </ul>
      )}
    </li>
  )
}

function AddItemForm({ project }: { project: string }) {
  const createItem = useCreateScopeItem()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [chargeNumber, setChargeNumber] = useState('')
  const [author, setAuthorField] = useState(() => getAuthor())

  function submit() {
    if (!title.trim()) return
    setAuthor(author)
    createItem.mutate(
      { project, title: title.trim(), charge_number: chargeNumber.trim() || undefined, created_by: author.trim() || undefined },
      { onSuccess: () => { setTitle(''); setChargeNumber(''); setOpen(false) } },
    )
  }

  if (!open) {
    return (
      <button className="sm-btn sm-btn--ghost scope-tree-page__add-btn" onClick={() => setOpen(true)}>
        + Add top-level scope item
      </button>
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
      <input
        placeholder="Your name (optional)"
        value={author}
        onChange={(e) => setAuthorField(e.target.value)}
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
