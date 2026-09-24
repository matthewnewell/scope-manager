import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useCreateScopeItem, useProjects, useScopeItems } from '../api/hooks'
import type { ProjectOption, ScopeItem } from '../api/types'
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

const PROJECT_KEY = 'sm:project'
const GOOD_PLAN_URL = 'http://localhost:5178'

/** The project whose WBS is on screen: a Depot link's `?project=` (its Depot id) wins, then the
 * last one looked at, then the first project with scope. */
function useProjectChoice(options: ProjectOption[] | undefined) {
  const [params, setParams] = useSearchParams()
  const fromUrl = params.get('project')
  let remembered: string | null = null
  try {
    remembered = window.localStorage.getItem(PROJECT_KEY)
  } catch {
    /* not remembered */
  }
  const known = (id: string | null) => !!id && !!options?.some((o) => o.id === id)
  const projectId = known(fromUrl) ? fromUrl! : known(remembered) ? remembered! : options?.[0]?.id

  useEffect(() => {
    if (!projectId) return
    try {
      window.localStorage.setItem(PROJECT_KEY, projectId)
    } catch {
      /* not remembered */
    }
  }, [projectId])

  const choose = (id: string) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('project', id)
        return next
      },
      { replace: true },
    )
  return [projectId, choose] as const
}

export default function ScopeTreePage() {
  const { data } = useProjects()
  const options = data?.projects
  const [projectId, setProjectId] = useProjectChoice(options)
  const project = options?.find((o) => o.id === projectId)

  const { data: items, isLoading } = useScopeItems(projectId)
  const byParent = items ? groupByParent(items) : new Map<string | null, ScopeItem[]>()
  const roots = byParent.get(null) ?? []
  const withScope = options?.filter((o) => o.item_count > 0) ?? []
  const without = options?.filter((o) => o.item_count === 0) ?? []

  return (
    <div className="scope-tree-page">
      <header className="scope-tree-page__header">
        <h1 className="scope-tree-page__title">Work breakdown</h1>
        {options && options.length > 0 && (
          <select
            className="scope-tree-page__project"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            <optgroup label="With a WBS">
              {withScope.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </optgroup>
            <optgroup label="No WBS yet">
              {without.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.phase === 'pursuit' ? ' (pursuit)' : ''}
                </option>
              ))}
            </optgroup>
          </select>
        )}
      </header>
      <p className="scope-tree-page__lede">
        The project's WBS. Good Plan budgets labor, materials and ODCs against its work packages (the
        leaves), and progress recorded here is what earns that budget.
      </p>
      {data && !data.depot_reachable && (
        <p className="scope-tree-page__loading">Conway's Depot isn't reachable, so only projects that already have scope are listed.</p>
      )}

      {isLoading && <p className="scope-tree-page__loading">Loading…</p>}

      {!isLoading && items && items.length === 0 && project && (
        <div className="scope-tree-page__empty">
          {project.phase === 'pursuit' ? (
            <>
              <strong>{project.name} is still a pursuit, so it has no WBS here yet.</strong> Its draft WBS
              lives in Good Plan, where the estimate is built on it. Once the work is awarded, send the
              draft over from Good Plan, or start one below.{' '}
              <a href={GOOD_PLAN_URL} target="_blank" rel="noreferrer">Open Good Plan</a>
            </>
          ) : (
            <>No WBS yet for {project.name}. Start with its top-level elements.</>
          )}
        </div>
      )}

      {!isLoading && project && (
        <>
          <ul className="scope-tree scope-tree--root">
            {roots.map((item) => (
              <ScopeNode key={item.id} item={item} byParent={byParent} />
            ))}
          </ul>
          <AddItemForm projectId={project.id} project={project.name} portfolio={project.portfolio} />
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
          {item.code && <span className="scope-row__code">{item.code}</span>}
          <span className="scope-row__title">{item.title}</span>
          {kids.length === 0 && <span className="scope-row__wp" title="A work package: budget in Good Plan sits here">WP</span>}
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

function AddItemForm({ projectId, project, portfolio }: { projectId: string; project: string; portfolio: string | null }) {
  const createItem = useCreateScopeItem()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [chargeNumber, setChargeNumber] = useState('')
  const [author, setAuthorField] = useState(() => getAuthor())

  function submit() {
    if (!title.trim()) return
    setAuthor(author)
    createItem.mutate(
      {
        project_id: projectId, project, portfolio: portfolio ?? undefined, title: title.trim(),
        charge_number: chargeNumber.trim() || undefined, created_by: author.trim() || undefined,
      },
      { onSuccess: () => { setTitle(''); setChargeNumber(''); setOpen(false) } },
    )
  }

  if (!open) {
    return (
      <button className="sm-btn sm-btn--ghost scope-tree-page__add-btn" onClick={() => setOpen(true)}>
        + Add top-level element
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
