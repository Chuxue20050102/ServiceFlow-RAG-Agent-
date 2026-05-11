export interface KnowledgeDocument {
  id: number
  document_name: string
  document_type: string
  file_name: string
  chunk_count: number
  status: string
  created_at: string
}

export interface TicketBatch {
  batch_id: number
  batch_name: string
  file_name: string
  total_count: number
  status: string
}

export interface AnalyzeResponse {
  batch_id: number
  status: string
  analyzed_count: number
  failed_count: number
  total_count: number
  progress_percent: number
}

export interface KnowledgeSearchResponse {
  query: string
  matches: string[]
}

export interface TicketSummary {
  total_count: number
  high_severity_count: number
  top_ticket_type: string
  top_responsible_team: string
  type_stats: Record<string, number>
  severity_stats: Record<string, number>
  team_stats: Record<string, number>
}

export interface TicketItem {
  id: number
  ticket_id: string
  user_id: string
  content: string
  source: string | null
  ticket_type: string | null
  severity: string | null
  responsible_team: string | null
  summary: string | null
  suggestion: string | null
  reply_template: string | null
  matched_rules: string[]
  raw_ai_result: string | null
  parse_success: boolean | null
  parse_error: string | null
}

export interface TicketReport {
  report_id: number
  title: string
  content: string
}
