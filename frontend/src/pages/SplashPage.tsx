import { Link } from 'react-router-dom'
import Nav from '../components/Nav'
import StatusPill from '../components/StatusPill'
import './SplashPage.css'

const MOCK_TREE = [
  { title: 'Design Definition', status: 'done', percent: 100, charge: 'CN-4471-10', depth: 0 },
  { title: 'Long-Lead Procurement', status: 'in_progress', percent: 65, charge: 'CN-4471-20', depth: 0 },
  { title: 'Build & Integration', status: 'not_started', percent: 0, charge: 'CN-4471-30', depth: 0 },
  { title: 'Fixture Fabrication', status: 'not_started', percent: 0, charge: 'CN-4471-31', depth: 1 },
  { title: 'Final Assembly', status: 'not_started', percent: 0, charge: 'CN-4471-32', depth: 1 },
] as const

const FEATURES = [
  {
    title: 'Judgment, not automation',
    body: 'Percent complete is always a person’s call, recorded with a required note — never a closed-issue count. Even with a GitHub or Azure Boards link attached, that’s a reference, not a source of truth.',
  },
  {
    title: 'As deep as it needs to be',
    body: 'One self-referential item, nested as far as a project’s real scope calls for — no hardcoded epic/feature/story taxonomy forcing software vocabulary onto a manufacturing WBS.',
  },
  {
    title: 'Built to feed Reckon',
    body: 'Each item can carry a charge number — the join key the project-execution dashboard will use to line earned value up against real S4 actuals, once it exists.',
  },
]

export default function SplashPage() {
  return (
    <div className="splash-page">
      <Nav />
      <div className="splash-page__scroll">
        <div className="splash-page__content">
          <header className="splash-hero">
            <h1 className="splash-hero__title">Scope Manager</h1>
            <p className="splash-hero__sub">
              A minimal work breakdown structure — and an honest place to record how done it
              really is.
            </p>
            <div className="splash-hero__actions">
              <Link className="sm-btn sm-btn--primary" to="/">Open the scope tree</Link>
            </div>
          </header>

          <figure className="splash-figure">
            <div className="splash-mock">
              {MOCK_TREE.map((row) => (
                <div
                  key={row.title}
                  className="splash-mock__row"
                  style={{ marginLeft: row.depth * 22 }}
                >
                  <span className="splash-mock__title">{row.title}</span>
                  <StatusPill status={row.status} />
                  <span className="splash-mock__percent">{row.percent}%</span>
                  <span className="splash-mock__charge">{row.charge}</span>
                </div>
              ))}
            </div>
          </figure>

          <div className="splash-grid">
            {FEATURES.map((f) => (
              <div key={f.title} className="splash-card">
                <div className="splash-card__heading">{f.title}</div>
                <p className="splash-card__body">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
