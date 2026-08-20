/**
 * Analytics API module
 * Handles token usage analytics and chat session enrichment
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
  }
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${keyMap[k] || k}=${encodeURIComponent(v)}`)
  return parts.length ? `?${parts.join('&')}` : ''
}

export const analyticsModule = (API) => ({
  // ── User-scoped endpoints ────────────────────────────────────────────────

  me() {
    return API.get('/api/analytics/me')
  },

  dates() {
    return API.get('/api/analytics/dates')
  },

  total({ startDate, endDate, projectName, model } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName, model })
    return API.get(`/api/analytics/total${qs}`)
  },

  daily({ startDate, endDate, projectName, grouping = 'day' } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName, grouping })
    return API.get(`/api/analytics/daily${qs}`)
  },

  byModel({ startDate, endDate, projectName } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName })
    return API.get(`/api/analytics/by-model${qs}`)
  },

  // ── User-scoped enriched endpoints (chat sessions) ───────────────────────

  /**
   * List user's chat sessions with aggregated metrics.
   * @param {object} opts
   * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
   * @param {string}  [opts.projectName]  - Filter by project name
   * @returns {Promise<Array>} List of ChatContextSummary objects
   */
  chatSessions({ startDate, endDate, projectName } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate, projectName })
    return API.get(`/api/analytics/chat-sessions${qs}`)
  },

  /**
   * Get a specific chat session with full context and enriched requests/tools.
   * @param {string} chatId - The chat identifier
   * @param {object} opts
   * @param {string}  [opts.startDate]  - Inclusive start date YYYY-MM-DD
   * @param {string}  [opts.endDate]    - Inclusive end date YYYY-MM-DD
   * @returns {Promise<object>} ChatContextSummary with detailed requests and tools
   */
  chatSession(chatId, { startDate, endDate } = {}) {
    const qs = _buildAnalyticsQS({ startDate, endDate })
    return API.get(`/api/analytics/chat-sessions/${encodeURIComponent(chatId)}${qs}`)
  },

  // ── Admin endpoints ──────────────────────────────────────────────────────

  admin: {
    dates() {
      return API.get('/api/analytics/admin/dates')
    },

    total({ startDate, endDate, username, projectName, projectId, model } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName, projectId, model })
      return API.get(`/api/analytics/admin/total${qs}`)
    },

    daily({ startDate, endDate, username, projectName, grouping = 'day' } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName, grouping })
      return API.get(`/api/analytics/admin/daily${qs}`)
    },

    byUser({ startDate, endDate, projectName, projectId } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, projectName, projectId })
      return API.get(`/api/analytics/admin/by-user${qs}`)
    },

    byProject({ startDate, endDate, username } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username })
      return API.get(`/api/analytics/admin/by-project${qs}`)
    },

    byModel({ startDate, endDate, username, projectName } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName })
      return API.get(`/api/analytics/admin/by-model${qs}`)
    },

    // ── Admin enriched endpoints (chat sessions) ─────────────────────────────

    /**
     * List all chat sessions across all users with aggregated metrics (admin only).
     * @param {object} opts
     * @param {string}  [opts.startDate]    - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]      - Inclusive end date YYYY-MM-DD
     * @param {string}  [opts.username]     - Filter by username
     * @param {string}  [opts.projectName]  - Filter by project name
     * @param {string}  [opts.projectId]    - Filter by project id
     * @returns {Promise<Array>} List of ChatContextSummary objects
     */
    chatSessions({ startDate, endDate, username, projectName, projectId } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate, username, projectName, projectId })
      return API.get(`/api/analytics/admin/chat-sessions${qs}`)
    },

    /**
     * Get a specific chat session with full context (admin only).
     * @param {string} chatId - The chat identifier
     * @param {object} opts
     * @param {string}  [opts.startDate]  - Inclusive start date YYYY-MM-DD
     * @param {string}  [opts.endDate]    - Inclusive end date YYYY-MM-DD
     * @returns {Promise<object>} ChatContextSummary with detailed requests and tools
     */
    chatSession(chatId, { startDate, endDate } = {}) {
      const qs = _buildAnalyticsQS({ startDate, endDate })
      return API.get(`/api/analytics/admin/chat-sessions/${encodeURIComponent(chatId)}${qs}`)
    },

    // ── Pricing endpoints ────────────────────────────────────────────────────

    pricing: {
      list() {
        return API.get('/api/analytics/admin/pricing')
      },

      updateProvider(providerName, prices) {
        return API.put(`/api/analytics/admin/pricing/provider/${providerName}`, prices)
      },

      updateModel(providerName, modelName, prices) {
        return API.put(`/api/analytics/admin/pricing/model/${providerName}/${modelName}`, prices)
      },

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