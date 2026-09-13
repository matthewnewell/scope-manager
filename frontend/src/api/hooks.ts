import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { ChatMessage, ChatResponse, ScopeEvent, ScopeItem, ScopeItemDetail, ScopeStatus } from './types'

export function useScopeItems(project: string | undefined) {
  return useQuery({
    queryKey: ['scope-items', project],
    queryFn: () => api.get<ScopeItem[]>(`/scope-items?project=${encodeURIComponent(project!)}`),
    enabled: !!project,
  })
}

export function useScopeItem(itemId: string | undefined) {
  return useQuery({
    queryKey: ['scope-items', 'detail', itemId],
    queryFn: () => api.get<ScopeItemDetail>(`/scope-items/${itemId}`),
    enabled: !!itemId,
  })
}

export function useProjects() {
  return useQuery({
    queryKey: ['scope-items', 'projects'],
    queryFn: () => api.get<string[]>('/scope-items/projects'),
  })
}

function useInvalidateScopeItems() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: ['scope-items'] })
}

export function useCreateScopeItem() {
  const invalidate = useInvalidateScopeItems()
  return useMutation({
    mutationFn: (data: {
      project: string
      title: string
      portfolio?: string
      description?: string
      parent_id?: string
      charge_number?: string
      external_ref?: string
      created_by?: string
    }) => api.post<ScopeItem>('/scope-items', data),
    onSuccess: invalidate,
  })
}

export function useUpdateScopeItem(itemId: string) {
  const invalidate = useInvalidateScopeItems()
  return useMutation({
    mutationFn: (
      data: Partial<Pick<ScopeItem, 'title' | 'description' | 'portfolio' | 'charge_number' | 'external_ref'>> & {
        author?: string
        journal_note?: string
      },
    ) => api.put<ScopeItem>(`/scope-items/${itemId}`, data),
    onSuccess: invalidate,
  })
}

export function useDeleteScopeItem() {
  const invalidate = useInvalidateScopeItems()
  return useMutation({
    mutationFn: (itemId: string) => api.del(`/scope-items/${itemId}`),
    onSuccess: invalidate,
  })
}

export function useAddProgress(itemId: string) {
  const invalidate = useInvalidateScopeItems()
  return useMutation({
    mutationFn: (data: { status: ScopeStatus; percent_complete: number; note: string; author?: string }) =>
      api.post<ScopeItem>(`/scope-items/${itemId}/progress`, data),
    onSuccess: invalidate,
  })
}

// ── Journal ──────────────────────────────────────────────────────────────────────────────────

export function useScopeItemEvents(itemId: string | undefined) {
  return useQuery({
    queryKey: ['scope-items', itemId, 'events'],
    queryFn: () => api.get<ScopeEvent[]>(`/scope-items/${itemId}/events`),
    enabled: !!itemId,
  })
}

function useInvalidateEvents(itemId?: string) {
  const qc = useQueryClient()
  return () => {
    if (itemId) qc.invalidateQueries({ queryKey: ['scope-items', itemId, 'events'] })
    qc.invalidateQueries({ queryKey: ['scope-items', 'detail', itemId] })
  }
}

export function useAddScopeEvent(itemId: string) {
  const invalidate = useInvalidateEvents(itemId)
  return useMutation({
    mutationFn: (data: { note: string; author?: string }) =>
      api.post<ScopeEvent>(`/scope-items/${itemId}/events`, data),
    onSuccess: invalidate,
  })
}

export function useDeleteScopeEvent(itemId: string) {
  const invalidate = useInvalidateEvents(itemId)
  return useMutation({
    mutationFn: (eventId: string) => api.del(`/scope-items/events/${eventId}`),
    onSuccess: invalidate,
  })
}

// ── AI chat ──────────────────────────────────────────────────────────────────────────────────

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<{ status: string; ai_configured: boolean }>('/health'),
  })
}

export function useChat() {
  return useMutation({
    mutationFn: (data: { messages: ChatMessage[]; itemId: string }) =>
      api.post<ChatResponse>('/chat', { messages: data.messages, item_id: data.itemId }),
  })
}
