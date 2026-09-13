import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { ScopeItem, ScopeItemDetail, ScopeStatus } from './types'

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
      data: Partial<Pick<ScopeItem, 'title' | 'description' | 'portfolio' | 'charge_number' | 'external_ref'>>,
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
