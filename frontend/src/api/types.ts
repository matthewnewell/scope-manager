export const STATUSES = ['not_started', 'in_progress', 'at_risk', 'done'] as const
export type ScopeStatus = (typeof STATUSES)[number]

export const STATUS_LABEL: Record<ScopeStatus, string> = {
  not_started: 'Not started',
  in_progress: 'In progress',
  at_risk: 'At risk',
  done: 'Done',
}

export interface ScopeItem {
  id: string
  project: string
  portfolio: string | null
  title: string
  description: string | null
  parent_id: string | null
  charge_number: string | null
  external_ref: string | null
  created_by: string | null
  status: ScopeStatus
  percent_complete: number
  last_update_note: string | null
  last_updated_by: string | null
  last_updated_at: string | null
  child_count?: number
}

export interface ScopeProgressEvent {
  id: string
  scope_item_id: string
  status: ScopeStatus
  percent_complete: number
  note: string
  author: string | null
  created_at: string
}

export type EventKind = 'note' | 'change'

export interface ScopeEvent {
  id: string
  scope_item_id: string
  created_at: string
  author: string | null
  kind: EventKind
  field: string | null
  old_value: string | null
  new_value: string | null
  note: string | null
}

export interface ScopeItemDetail extends ScopeItem {
  ancestors: ScopeItem[]
  children: ScopeItem[]
  progress_events: ScopeProgressEvent[]
  events: ScopeEvent[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  reply: string
  error?: string
}
