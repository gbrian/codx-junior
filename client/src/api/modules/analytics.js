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
