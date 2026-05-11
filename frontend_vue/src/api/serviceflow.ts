import type {
  AnalyzeResponse,
  KnowledgeSearchResponse,
  KnowledgeDocument,
  TicketBatch,
  TicketItem,
  TicketReport,
  TicketSummary,
} from '@/types/serviceflow'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8010/api/serviceflow'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail ?? 'Request failed')
  }
  return response.json() as Promise<T>
}

export function uploadKnowledgeDocument(
  documentName: string,
  documentType: string,
  file: File,
) {
  const formData = new FormData()
  formData.append('document_name', documentName)
  formData.append('document_type', documentType)
  formData.append('file', file)
  return request<KnowledgeDocument>('/knowledge/upload', {
    method: 'POST',
    body: formData,
  })
}

export function listKnowledgeDocuments() {
  return request<KnowledgeDocument[]>('/knowledge')
}

export function searchKnowledge(query: string) {
  return request<KnowledgeSearchResponse>(`/knowledge/search?query=${encodeURIComponent(query)}`)
}

export function uploadTicketBatch(batchName: string, file: File) {
  const formData = new FormData()
  formData.append('batch_name', batchName)
  formData.append('file', file)
  return request<TicketBatch>('/tickets/upload', {
    method: 'POST',
    body: formData,
  })
}

export function analyzeTicketBatch(batchId: number) {
  return request<AnalyzeResponse>(`/tickets/${batchId}/analyze`, {
    method: 'POST',
  })
}

export function getAnalyzeStatus(batchId: number) {
  return request<AnalyzeResponse>(`/tickets/${batchId}/analyze/status`)
}

export function getTicketSummary(batchId: number) {
  return request<TicketSummary>(`/tickets/${batchId}/summary`)
}

export function getTicketItems(batchId: number) {
  return request<TicketItem[]>(`/tickets/${batchId}/items`)
}

export function generateTicketReport(batchId: number) {
  return request<TicketReport>(`/tickets/${batchId}/report`, {
    method: 'POST',
  })
}

export function getTicketReport(batchId: number) {
  return request<TicketReport>(`/tickets/${batchId}/report`)
}
