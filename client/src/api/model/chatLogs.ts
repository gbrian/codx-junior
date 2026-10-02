/**
 * Chat Logs Models
 * TypeScript interfaces for chat log summary and forensic audit trail records.
 * Mirrors backend Pydantic models from codx.junior.model.logs
 */

/**
 * Status distribution of log records
 */
export interface ChatLogStatusDistribution {
  success: number
  error: number
  cancelled: number
}

/**
 * Estimated token usage statistics
 */
export interface ChatLogTokenStats {
  total_estimated_input_tokens: number
  total_estimated_output_tokens: number
  total_estimated_tokens: number
}

/**
 * Model and provider usage statistics
 */
export interface ChatLogModelUsage {
  model: string
  provider: string
  request_count: number
  total_duration_seconds: number
}

/**
 * Forensic record of a complete LLM request-response cycle
 * Captures all data needed to audit or replay an AI interaction
 */
export interface ForensicArchivedMessageRecord {
  message_id: string
  request_id: string
  timestamp: number
  iso_date: string
  request_messages: Array<Record<string, any>>
  system_prompt?: string | null
  temperature?: number | null
  max_tokens?: number | null
  tools?: Array<Record<string, any>> | null
  response_content: string
  input_tokens: number
  output_tokens: number
  duration_seconds: number
  error?: string | null
  cancelled: boolean
  model: string
  provider: string
  chat_id: string
  username: string
  project_name: string
  project_id: string
}

/**
 * Forensic record of a complete tool call execution
 * Captures all data needed to audit or replay a tool interaction
 */
export interface ForensicToolCallRecord {
  message_id: string
  tool_call_id: string
  timestamp: number
  iso_date: string
  tool_name: string
  tool_definition?: Record<string, any> | null
  request_args: Record<string, any>
  result: any
  result_sent_to_model: string
  duration_seconds: number
  success: boolean
  error_message?: string | null
  cached: boolean
  chat_id: string
  username: string
  project_name: string
  project_id: string
}

/**
 * Union type for forensic records
 */
export type ForensicLogRecord = ForensicArchivedMessageRecord | ForensicToolCallRecord

/**
 * Complete summary of all AI logs associated with a single chat
 * Aggregates request/response pairs, token estimates, status distribution,
 * and model usage statistics with optional forensic audit trail
 */
export interface ChatLogSummary {
  chat_id: string
  session_id?: string | null
  total_log_records: number
  total_requests: number
  total_responses: number
  status_distribution: ChatLogStatusDistribution
  token_stats: ChatLogTokenStats
  total_duration_seconds: number
  average_request_duration_seconds?: number | null
  model_usage: ChatLogModelUsage[]
  first_timestamp?: string | null
  last_timestamp?: string | null
  has_errors: boolean
  error_details: string[]
  fallback_used: boolean
  fallback_reason?: string | null
  raw_log_records: Array<Record<string, any>>
}

// Type guards for forensic records
export function isArchivedMessageRecord(record: any): record is ForensicArchivedMessageRecord {
  return record && 'request_messages' in record && 'response_content' in record
}

export function isToolCallRecord(record: any): record is ForensicToolCallRecord {
  return record && 'tool_name' in record && 'request_args' in record
}