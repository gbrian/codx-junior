/**
 * TypeScript-like JSDoc type definitions for Analytics API models.
 * 
 * These models mirror the backend Pydantic models to ensure
 * proper type understanding and IDE autocomplete support.
 */

/**
 * @typedef {Object} TokenUsageMetrics
 * @property {number} input_tokens - Total input tokens
 * @property {number} output_tokens - Total output tokens
 * @property {number} total_tokens - Sum of input + output tokens
 * @property {number} calls - Number of LLM calls
 * @property {number} total_duration_seconds - Total duration in seconds
 * @property {number} total_cxjcoins - Total cost in CXJ coins
 * @property {boolean} tokens_from_provider - Whether token count comes from provider
 */

/**
 * @typedef {Object} DailyUsageEntry
 * @property {string} period - Time period (YYYY-MM-DD for day grouping)
 * @property {number} input_tokens
 * @property {number} output_tokens
 * @property {number} total_tokens
 * @property {number} calls
 * @property {number} total_duration_seconds
 * @property {number} total_cxjcoins
 * @property {boolean} tokens_from_provider
 */

/**
 * @typedef {Object} UserMetrics
 * @property {string} username - Username
 * @property {TokenUsageMetrics} today - Today's usage
 * @property {TokenUsageMetrics} current_month - Current month's usage
 */

// ── Chat Session Models ────────────────────────────────────────────────────────

/**
 * @typedef {Object} ChatSessionMetadata
 * @property {string} chat_id - Unique chat identifier
 * @property {string} chat_name - Human-readable chat name
 * @property {string} username - User who created the chat
 * @property {string} project_name - Project context name
 * @property {string} project_id - Project identifier
 * @property {string} mode - Chat mode (task, agent, vibe, chat)
 * @property {string[]} profiles - Applied profiles
 * @property {string[]} files - Accessed files
 * @property {?string} parent_chat_id - Parent chat if nested
 * @property {number} iteration - Current iteration number
 * @property {number} max_iterations - Maximum iterations
 * @property {string} llm_model - LLM model used
 * @property {?string} session_id - Session identifier
 * @property {boolean} cancelled - Whether chat was cancelled
 * @property {?string} error - Error message if failed
 * @property {number} duration_seconds - Total duration in seconds
 * @property {number} input_message_count - Number of input messages
 * @property {number} output_message_count - Number of output messages
 * @property {number} timestamp - Unix timestamp
 * @property {string} iso_date - ISO date YYYY-MM-DD
 */

/**
 * @typedef {Object} ChatMetrics
 * @property {number} total_input_tokens - Sum of input tokens
 * @property {number} total_output_tokens - Sum of output tokens
 * @property {number} total_tokens - Total tokens
 * @property {number} llm_calls - Number of LLM calls
 * @property {number} total_llm_duration_seconds - Total LLM duration
 * @property {number} total_cxjcoins - Total cost in CXJ coins
 * @property {number} tool_calls - Number of tool executions
 * @property {number} successful_tool_calls - Successful tool executions
 * @property {number} failed_tool_calls - Failed tool executions
 * @property {number} total_tool_duration_seconds - Total tool duration
 * @property {number} avg_tool_duration_seconds - Average tool duration
 */

/**
 * @typedef {Object} ChatContextSummary
 * @property {ChatSessionMetadata} chat_session - Chat metadata
 * @property {ChatMetrics} metrics - Aggregated metrics
 * @property {number} llm_request_count - Number of LLM requests
 * @property {number} tool_call_count - Number of tool calls
 */

// ── Message Models ────────────────────────────────────────────────────────────

/**
 * @typedef {Object} ArchivedMessageData
 * @property {string} message_id - Unique message identifier
 * @property {string} chat_id - Parent chat identifier
 * @property {string} username - User who triggered the message
 * @property {string} project_name - Project context
 * @property {string} project_id - Project identifier
 * @property {string} model - LLM model used
 * @property {string} provider - LLM provider
 * @property {Object[]} request_messages - Messages sent to provider
 * @property {string} response_content - Full response content
 * @property {?string} request_id - Request identifier
 * @property {?string} tool_call_id - Tool call ID if triggered by tool
 * @property {?string} tool_name - Tool name if applicable
 * @property {number} duration_seconds - Wall-clock duration
 * @property {number} input_tokens - Request token count
 * @property {number} output_tokens - Response token count
 * @property {?string} error - Error if failed
 * @property {boolean} cancelled - Whether request was cancelled
 * @property {number} timestamp - Unix timestamp
 * @property {string} iso_date - ISO date YYYY-MM-DD
 */

/**
 * @typedef {Object} ToolCallMessageData
 * @property {string} message_id - Unique message identifier
 * @property {string} chat_id - Parent chat identifier
 * @property {string} tool_call_id - Tool call ID from AI provider
 * @property {string} tool_name - Name of tool executed
 * @property {string} username - User context
 * @property {string} project_name - Project context
 * @property {string} project_id - Project identifier
 * @property {Object} request_args - Arguments sent to tool
 * @property {*} result - Tool execution result (as JSON string in storage)
 * @property {string} result_sent_to_model - Normalized result sent to model
 * @property {boolean} success - Whether tool executed successfully
 * @property {?string} error_message - Error details
 * @property {number} duration_seconds - Execution duration
 * @property {boolean} cached - Whether result was cached
 * @property {number} timestamp - Unix timestamp
 * @property {string} iso_date - ISO date YYYY-MM-DD
 */

/**
 * @typedef {Object} ChatMessagesResponse
 * @property {ArchivedMessageData[]} llm_messages - Archived LLM messages
 * @property {ToolCallMessageData[]} tool_messages - Tool call messages
 * @property {number} total_llm_messages - Count of LLM messages
 * @property {number} total_tool_messages - Count of tool messages
 */

// ── Tool Metrics Models ────────────────────────────────────────────────────────

/**
 * @typedef {Object} ErrorDetail
 * @property {number} timestamp - When error occurred
 * @property {string} error_message - Error message
 */

/**
 * @typedef {Object} ToolExecutionMetrics
 * @property {number} total_calls - Total number of calls
 * @property {number} successful - Successful executions
 * @property {number} failed - Failed executions
 * @property {number} success_rate - Success rate percentage (0-100)
 * @property {number} total_duration - Total execution time in seconds
 * @property {number} avg_duration - Average execution time
 * @property {number} min_duration - Minimum execution time
 * @property {number} max_duration - Maximum execution time
 * @property {ErrorDetail[]} error_details - Failed execution details
 */

/**
 * Map of tool_name -> ToolExecutionMetrics
 * @typedef {Object.<string, ToolExecutionMetrics>} ToolMetricsMap
 */

// ── Chat Context Models ────────────────────────────────────────────────────────

/**
 * @typedef {Object} LLMRequestRecord
 * @property {string} username
 * @property {string} project_name
 * @property {string} project_id
 * @property {string} model
 * @property {string} provider
 * @property {number} input_tokens
 * @property {number} output_tokens
 * @property {number} total_tokens
 * @property {number} duration_seconds
 * @property {?string} session_id
 * @property {string} tags
 * @property {number} input_k_tokens_cxjcoins
 * @property {number} output_k_tokens_cxjcoins
 * @property {?string} request_id
 * @property {boolean} tokens_from_provider
 * @property {?string} chat_id
 * @property {number} timestamp
 * @property {string} iso_date
 * @property {number} total_cxjcoins
 */

/**
 * @typedef {Object} ToolCallRecord
 * @property {string} name
 * @property {string} username
 * @property {string} project_name
 * @property {string} project_id
 * @property {number} time_taken
 * @property {boolean} success
 * @property {?string} error_message
 * @property {?string} chat_id
 * @property {?string} tool_id
 * @property {?string} request_id
 * @property {number} timestamp
 * @property {string} iso_date
 */

/**
 * @typedef {Object} ChatCompleteContext
 * @property {ChatSessionMetadata} chat_session - Chat session metadata
 * @property {ChatMetrics} metrics - Aggregated metrics
 * @property {LLMRequestRecord[]} llm_requests - LLM request usage records
 * @property {ArchivedMessageData[]} llm_messages - Archived LLM messages
 * @property {ToolCallRecord[]} tool_calls - Tool execution usage records
 * @property {ToolCallMessageData[]} tool_messages - Tool call execution records
 * @property {ToolMetricsMap} tool_metrics - Aggregated tool metrics by name
 */

/**
 * @typedef {Object} ChatContextWithToolDetails
 * @property {ChatSessionMetadata} chat_session - Chat session metadata
 * @property {ChatMetrics} metrics - Aggregated metrics
 * @property {LLMRequestRecord[]} llm_requests - LLM request records
 * @property {ToolCallRecord[]} tool_calls - Tool call records
 * @property {ToolMetricsMap} tool_metrics - Detailed tool execution metrics
 */

// ── Aggregation Models ─────────────────────────────────────────────────────────

/**
 * Map of key (username, project, model) -> TokenUsageMetrics
 * @typedef {Object.<string, TokenUsageMetrics>} AggregatedUsageByKey
 */

// ── Pricing Models ─────────────────────────────────────────────────────────────

/**
 * @typedef {Object} ModelPricingInfo
 * @property {string} name - Model name
 * @property {?string} ai_model - Provider-side model name
 * @property {number} input_k_tokens_cxjcoins - Input price per 1K tokens
 * @property {number} output_k_tokens_cxjcoins - Output price per 1K tokens
 */

/**
 * @typedef {Object} ProviderPricingInfo
 * @property {string} name - Provider name
 * @property {number} input_k_tokens_cxjcoins - Provider-level input price per 1K tokens
 * @property {number} output_k_tokens_cxjcoins - Provider-level output price per 1K tokens
 * @property {ModelPricingInfo[]} models - Model-level pricing overrides
 */

/**
 * List of providers with their pricing information
 * @typedef {ProviderPricingInfo[]} PricingList
 */

export {
  // TokenUsageMetrics,
  // DailyUsageEntry,
  // UserMetrics,
  // ChatSessionMetadata,
  // ChatMetrics,
  // ChatContextSummary,
  // ArchivedMessageData,
  // ToolCallMessageData,
  // ChatMessagesResponse,
  // ErrorDetail,
  // ToolExecutionMetrics,
  // LLMRequestRecord,
  // ToolCallRecord,
  // ChatCompleteContext,
  // ChatContextWithToolDetails,
  // ModelPricingInfo,
  // ProviderPricingInfo,
}

// Made with ❤️ by codx-junior