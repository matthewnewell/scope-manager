import { STATUS_LABEL } from '../api/types'
import type { ScopeStatus } from '../api/types'
import './StatusPill.css'

export default function StatusPill({ status }: { status: ScopeStatus }) {
  return <span className={`status-pill status-pill--${status}`}>{STATUS_LABEL[status]}</span>
}
