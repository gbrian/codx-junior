/**
 * Analytics API module with full type documentation
 * 
 * Uses types defined in api/model/analytics.ts:
 * @typedef {import('../model/analytics.ts').TokenUsageMetrics} TokenUsageMetrics
 * @typedef {import('../model/analytics.ts').ChatContextSummary} ChatContextSummary
 * @typedef {import('../model/analytics.ts').ChatCompleteContext} ChatCompleteContext
 * @typedef {import('../model/analytics.ts').ChatMessagesResponse} ChatMessagesResponse
 * @typedef {import('../model/analytics.ts').ToolMetricsMap} ToolMetricsMap
 * @typedef {import('../model/analytics.ts').AggregatedUsageByKey} AggregatedUsageByKey
 * @typedef {import('../model/analytics.ts').UserMetrics} UserMetrics
 * @typedef {import('../model/analytics.ts').DailyUsageEntry} DailyUsageEntry
 * @typedef {import('../model/analytics.ts').ProviderPricingInfo} ProviderPricingInfo
 */

/**
 * A single decision-model execution log record.
 * @typedef {Object} DecisionModelLogRecord
 * @property {string}        id
 * @property {string|number} timestamp
 * @property {string}        [direction]      - 'request' | 'response'
 * @property {string}        [provider]
 * @property {string}        [model]
 * @property {string}        [decision]       - Chosen decision / action label
 * @property {string}        [reasoning]      - Model reasoning trace
 * @property {string}        [prompt]
 * @property {string}        [tags]           - Comma separated tags (e.g. 'decision')
 * @property {string}        [session_id]
 * @property {number}        [input_tokens]
 * @property {number}        [output_tokens]
 * @property {number}        [duration_seconds]
 * @property {boolean}       [cached]
 * @property {boolean}       [error]
 * @property {string}        [error_message]
 */

/**
 * Aggregated decision-model logs payload.
 * @typedef {Object} DecisionModelLogsResponse
 * @property {DecisionModelLogRecord[]} records
 * @property {Array<string|{model: string}>} [models]
 * @property {Object} [summary]
 * @property {number} [summary.total_log_records]
 * @property {number} [summary.total_requests]
 * @property {number} [summary.total_responses]
 * @property {number} [summary.total_duration_seconds]
 * @property {number} [summary.average_request_duration_seconds]
 * @property {Object} [summary.token_stats]
 * @property {number} [summary.token_stats.total_estimated_input_tokens]
 * @property {number} [summary.token_stats.total_estimated_output_tokens]
 * @property {number} [summary.token_stats.total_estimated_tokens]
 */

/**
 * Build a query string from analytics filter params.
 * Omits undefined/null values and converts camelCase to snake_case.
 */
function _buildAnalyticsQS(params) {
  const keyMap = {
    startDate: 'start_date',
    endDate: 'end_date',
    username: 'username',
    projectName: 'project_name',
    projectId: 'project_id',
    model: 'model',
    grouping: 'grouping',
    direction: 'direction',
    sessionId: 'session_id',
    project: 'project',
    provider: 'provider',
    requestId: 'request_id',
  }
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${keyMap[k] || k}=${encodeURIComponent(v)}`)
  return parts.length ? `?${parts.join('&')}` : ''
}

// ══════════════════════════════════════════════════════════════════════════
// DECISION MODEL LOGS — ENDPOINT RESOLUTION
//
// Decision-model executions are persisted in the shared AI-log store, but not
// every deployment exposes the same route for it: some ship a dedicated
// listing, others only the generic AI-log listing. Hard-coding one path made
// the viewer fail with "endpoint not found".
//
// To stay resilient the client probes an ordered list of candidate routes and
// uses the first one that resolves. Ordering matters: the *specific* route is
// tried first (it returns exactly the decision-model records) and the generic
// AI-log listing is the fallback. A 404 just moves on to the next candidate;
// any other error (auth, 5xx…) is surfaced immediately so real problems are
// never masked.
// ══════════════════════════════════════════════════════════════════════════

const DECISION_LOG_PATHS = [
  '/api/analytics/decision-model-logs',
  '/api/analytics/logs',
  '/api/logs',
]

const ADMIN_DECISION_LOG_PATHS = [
  '/api/analytics/admin/decision-model-logs',
  '/api/analytics/admin/logs',
  ...DECISION_LOG_PATHS,
]

/**
 * Whether an API error means "this route is not exposed by the backend" (404)
 * rather than a genuine failure. Tolerates both axios-style errors (with a
 * `response.status`) and plain errors carrying "404"/"Not Found" in the message.
 * @param {any} error
 * @returns {boolean}
 */
function _isNotFound(error) {
  const status = error?.status || error?.response?.status
  if (status === 404) return true
  return /not found|404/i.test(String(error?.message ?? error ?? ''))
}

/**
 * Request the first candidate URL that resolves, falling back to the next one
 * only on a "not found" response.
 * @param {any} API  - The API client (get/put/post…)
 * @param {string[]} urls - Candidate URLs, most specific first
 * @returns {Promise<any>}
 */
async function _getFirstAvailable(API, urls) {
  let lastError
  for (const url of urls) {
    try {
      return await API.get(url)
    } catch (error) {
      lastError = error
      if (!_isNotFound(error)) throw error
    }
  }
  throw lastError
}

export const analyticsModule = (API) => ({
  // ── User-scoped endpoints ────────────────────────────────────────────────

  /**
   * Get current user metrics for today and the current month.
   * @returns {Promise<UserMetrics>}
   */
  me() {
    return API.get('/api/analytics/me')
  },

  /**
   * List all ISO dates (YYYY-MM-DD) for which the authenticated user has recorded token usage.
   * @returns {Promise<string[]>}
   */
  dates() {
    return API.get('/api/analytics/dates')
  },

  /**
   * Get total token consumption for the authenticated user.
   * @param {Object} opts
   * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
   * @param {string}  [opts.projectName]  - Filter by project name
   * @param {string}  [opts.model]        - Filter by model name
   * @returns {Promise<TokenUsageMetrics>}
   */
  total({ startDate, endDate, projectName, model } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName, model })
    return API.get(`/api/analytics/total${qs}`)
  },

  /**
   * Get per-period aggregated token usage for the authenticated user.
   * @param {Object} opts
   * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
   * @param {string}  [opts.projectName]  - Filter by project name
   * @param {string}  [opts.grouping]     - Time grouping: 'minute', 'hour', 'day' (default: 'day')
   * @returns {Promise<DailyUsageEntry[]>}
   */
  daily({ startDate, endDate, projectName, grouping = 'day' } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName, grouping })
    return API.get(`/api/analytics/daily${qs}`)
  },

  /**
   * Get token usage aggregated by model name.
   * @param {Object} opts
   * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
   * @param {string}  [opts.projectName]  - Filter by project name
   * @returns {Promise<AggregatedUsageByKey>}
   */
  byModel({ startDate, endDate, projectName } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName })
    return API.get(`/api/analytics/by-model${qs}`)
  },

  // ── User-scoped decision model log endpoints ─────────────────────────────

  /**
   * List decision-model execution logs for the current user.
   * Resolves the backend route automatically (see DECISION_LOG_PATHS).
   * @param {Object} opts
   * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
   * @param {string}  [opts.projectName]  - Filter by project name
   * @param {string}  [opts.projectId]    - Filter by project id
   * @param {string}  [opts.model]        - Filter by model name
   * @param {string}  [opts.direction]    - 'request' | 'response'
   * @param {string}  [opts.sessionId]    - Filter by session id
   * @param {string}  [opts.tags]         - Filter by tags (e.g. 'decision')
   * @returns {Promise<DecisionModelLogsResponse>}
   */
  decisionLogs({ startDate, endDate, projectName, projectId, model, direction, sessionId, tags } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName, projectId, model, direction, sessionId, tags })
    return _getFirstAvailable(API, DECISION_LOG_PATHS.map(path => `${path}${qs}`))
  },

  /**
   * Get a single decision-model execution log by id.
   * @param {string} id
   * @returns {Promise<DecisionModelLogRecord>}
   */
  decisionLog(id) {
    const suffix = `/${encodeURIComponent(id)}`
    return _getFirstAvailable(API, DECISION_LOG_PATHS.map(path => `${path}${suffix}`))
  },

  // ── User-scoped chat analytics endpoints ──────────────────────────────────

  /**
   * List chat sessions for the current user with aggregated metrics.
   * @param {Object} opts
   * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
   * @param {string}  [opts.projectName]  - Filter by project name
   * @param {string}  [opts.projectId]    - Filter by project id
   * @returns {Promise<ChatContextSummary[]>}
   */
  chatSessions({ startDate, endDate, projectName, projectId } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName, projectId })
    return API.get(`/api/analytics/chat-sessions${qs}`)
  },

  /**
   * Get a specific chat session with full context for the current user.
   * @param {string} chatId - The chat identifier
   * @param {Object} opts
   * @param {string}  [opts.startDate]  - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]    - Inclusive end date YYYY-MM-DD
   * @returns {Promise<ChatContextWithToolDetails>}
   */
  chatSession(chatId, { startDate, endDate } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate })
    return API.get(`/api/analytics/chat-sessions/${encodeURIComponent(chatId)}${qs}`)
  },

  /**
   * Get archived and tool call messages for a user's chat session.
   * Can optionally filter by request_id to retrieve messages for a specific LLM request.
   * @param {string} chatId - The chat identifier
   * @param {Object} opts
   * @param {string}  [opts.startDate]  - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]    - Inclusive end date YYYY-MM-DD
   * @param {string}  [opts.requestId]  - Filter by LLM request id
   * @returns {Promise<ChatMessagesResponse>}
   */
  chatSessionMessages(chatId, { startDate, endDate, requestId } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, requestId })
    return API.get(`/api/analytics/chat-sessions/${encodeURIComponent(chatId)}/messages${qs}`)
  },

  // ── Admin endpoints ──────────────────────────────────────────────────────

  admin: {
    /**
     * List all ISO dates for which any token usage data is stored (admin only).
     * @returns {Promise<string[]>}
     */
    dates() {
      return API.get('/api/analytics/admin/dates')
    },

    /**
     * Get total token consumption across all users (admin only).
     * @param {Object} opts
     * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.username]     - Filter by username
     * @param {string}  [opts.projectName]  - Filter by project name
     * @param {string}  [opts.projectId]    - Filter by project id
     * @param {string}  [opts.model]        - Filter by model name
     * @returns {Promise<TokenUsageMetrics>}
     */
    total({ startDate, endDate, username, projectName, projectId, model } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName, projectId, model })
      return API.get(`/api/analytics/admin/total${qs}`)
    },

    /**
     * Get per-period aggregated token usage across all users (admin only).
     * @param {Object} opts
     * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.username]     - Filter by username
     * @param {string}  [opts.projectName]  - Filter by project name
     * @param {string}  [opts.grouping]     - Time grouping: 'minute', 'hour', 'day' (default: 'day')
     * @returns {Promise<DailyUsageEntry[]>}
     */
    daily({ startDate, endDate, username, projectName, grouping = 'day' } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName, grouping })
      return API.get(`/api/analytics/admin/daily${qs}`)
    },

    /**
     * Get token usage aggregated by username (admin only).
     * @param {Object} opts
     * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.projectName]  - Filter by project name
     * @param {string}  [opts.projectId]    - Filter by project id
     * @returns {Promise<AggregatedUsageByKey>}
     */
    byUser({ startDate, endDate, projectName, projectId } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, projectName, projectId })
      return API.get(`/api/analytics/admin/by-user${qs}`)
    },

    /**
     * Get token usage aggregated by project name (admin only).
     * @param {Object} opts
     * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.username]     - Filter by username
     * @returns {Promise<AggregatedUsageByKey>}
     */
    byProject({ startDate, endDate, username } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username })
      return API.get(`/api/analytics/admin/by-project${qs}`)
    },

    /**
     * Get token usage aggregated by model name across all users (admin only).
     * @param {Object} opts
     * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.username]     - Filter by username
     * @param {string}  [opts.projectName]  - Filter by project name
     * @returns {Promise<AggregatedUsageByKey>}
     */
    byModel({ startDate, endDate, username, projectName } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName })
      return API.get(`/api/analytics/admin/by-model${qs}`)
    },

    // ── Admin decision model log endpoints (admin only) ────────────────────

    /**
     * List decision-model execution logs across all users (admin only).
     * Resolves the backend route automatically (see ADMIN_DECISION_LOG_PATHS);
     * falls back to the user-scoped listing when no admin route is deployed.
     * @param {Object} opts
     * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.username]     - Filter by username
     * @param {string}  [opts.projectName]  - Filter by project name
     * @param {string}  [opts.projectId]    - Filter by project id
     * @param {string}  [opts.model]        - Filter by model name
     * @param {string}  [opts.direction]    - 'request' | 'response'
     * @param {string}  [opts.sessionId]    - Filter by session id
     * @param {string}  [opts.tags]         - Filter by tags (e.g. 'decision')
     * @returns {Promise<DecisionModelLogsResponse>}
     */
    decisionLogs({ startDate, endDate, username, projectName, projectId, model, direction, sessionId, tags } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName, projectId, model, direction, sessionId, tags })
      return _getFirstAvailable(API, ADMIN_DECISION_LOG_PATHS.map(path => `${path}${qs}`))
    },

    /**
     * Get a single decision-model execution log by id (admin only).
     * @param {string} id
     * @returns {Promise<DecisionModelLogRecord>}
     */
    decisionLog(id) {
      const suffix = `/${encodeURIComponent(id)}`
      return _getFirstAvailable(API, ADMIN_DECISION_LOG_PATHS.map(path => `${path}${suffix}`))
    },

    // ── Admin chat analytics endpoints (admin only) ────────────────────────

    /**
     * List all chat sessions across all users with aggregated metrics (admin only).
     * @param {Object} opts
     * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.username]     - Filter by username
     * @param {string}  [opts.projectName]  - Filter by project name
     * @param {string}  [opts.projectId]    - Filter by project id
     * @returns {Promise<ChatContextSummary[]>}
     */
    chatSessions({ startDate, endDate, username, projectName, projectId } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName, projectId })
      return API.get(`/api/analytics/admin/chat-sessions${qs}`)
    },

    /**
     * Get a specific chat session with full context (admin only).
     * @param {string} chatId - The chat identifier
     * @param {Object} opts
     * @param {string}  [opts.startDate]  - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]    - Inclusive end date YYYY-MM-DD
     * @returns {Promise<ChatContextWithToolDetails>}
     */
    chatSession(chatId, { startDate, endDate } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate })
      return API.get(`/api/analytics/admin/chat-sessions/${encodeURIComponent(chatId)}${qs}`)
    },

    /**
     * Get archived and tool call messages for any chat session (admin only).
     * Can optionally filter by request_id to retrieve messages for a specific LLM request.
     * @param {string} chatId - The chat identifier
     * @param {Object} opts
     * @param {string}  [opts.startDate]  - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]    - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.requestId]  - Filter by LLM request id
     * @returns {Promise<ChatMessagesResponse>}
     */
    chatSessionMessages(chatId, { startDate, endDate, requestId } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, requestId })
      return API.get(`/api/analytics/admin/chat-sessions/${encodeURIComponent(chatId)}/messages${qs}`)
    },

    /**
     * Get complete context for any chat session including all messages (admin only).
     * @param {string} chatId - The chat identifier
     * @param {Object} opts
     * @param {string}  [opts.startDate]  - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]    - Inclusive end date YYYY-MM-DD
     * @returns {Promise<ChatCompleteContext>}
     */
    chatSessionCompleteContext(chatId, { startDate, endDate } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate })
      return API.get(`/api/analytics/admin/chat-sessions/${encodeURIComponent(chatId)}/complete-context${qs}`)
    },

    // ── Pricing endpoints ────────────────────────────────────────────────────

    /**
     * Pricing management endpoints
     */
    pricing: {
      /**
       * List all providers and models with current pricing (admin only).
       * @returns {Promise<ProviderPricingInfo[]>}
       */
      list() {
        return API.get('/api/analytics/admin/pricing')
      },

      /**
       * Update provider-level pricing (admin only).
       * @param {string} providerName - The provider name (e.g., 'openai', 'anthropic')
       * @param {Object} prices - Price object
       * @param {number} [prices.input_k_tokens_cxjcoins] - Input token price per 1k tokens
       * @param {number} [prices.output_k_tokens_cxjcoins] - Output token price per 1k tokens
       * @returns {Promise<{ok: boolean}>}
       */
      updateProvider(providerName, prices) {
        return API.put(`/api/analytics/admin/pricing/provider/${providerName}`, prices)
      },

      /**
       * Update model-level pricing within a provider (admin only).
       * @param {string} providerName - The provider name
       * @param {string} modelName - The model name
       * @param {Object} prices - Price object
       * @param {number} [prices.input_k_tokens_cxjcoins] - Input token price per 1k tokens
       * @param {number} [prices.output_k_tokens_cxjcoins] - Output token price per 1k tokens
       * @returns {Promise<{ok: boolean}>}
       */
      updateModel(providerName, modelName, prices) {
        return API.put(`/api/analytics/admin/pricing/model/${providerName}/${modelName}`, prices)
      },

      /**
       * Recalculate historical events with new pricing (admin only).
       * @param {Object} opts
       * @param {string} opts.provider - Provider name
       * @param {string} opts.model - Model name
       * @param {string} opts.startDate - Start date YYYY-MM-DD
       * @param {string} opts.endDate - End date YYYY-MM-DD
       * @param {number} opts.inputPrice - Input token price per 1k tokens
       * @param {number} opts.outputPrice - Output token price per 1k tokens
       * @returns {Promise<{ok: number}>}
       */
      recalculate({ provider, model, startDate, endDate, inputPrice, outputPrice }) {
        return API.post('/api/analytics/admin/pricing/recalculate', {
          provider,
          model,
          start_date: startDate,
          end_date: endDate,
          input_k_tokens_cxjcoins: inputPrice,
          output_k_tokens_cxjcoins: outputPrice,
        })
      },
    }
  }
})
