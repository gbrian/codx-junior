/**
 * Browsers API module.
 *
 * Thin wrapper around the co-browsing REST API.  Every page action is sent to
 * the same backend `action` endpoint used by the AI tools, so the live VNC view
 * and the AI always operate on the exact same browser page.
 */

export const browsersModule = (API) => ({
  // ── List & Retrieval ───────────────────────────────────────────────────

  async list(filters) {
    let qs = ''
    if (filters) {
      const params = Object.entries(filters)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&')
      qs = `?${params}`
    }
    return API.get(`/api/browsers${qs}`)
  },

  async get(sessionId) {
    return API.get(`/api/browsers/${sessionId}`)
  },

  // ── CRUD & lifecycle ────────────────────────────────────────────────────

  /**
   * Create a browser session.
   * @param {Object} payload - { name, chat_id?, initial_url? }
   */
  async create(payload) {
    return API.post('/api/browsers', payload)
  },

  async update(sessionId, payload) {
    return API.put(`/api/browsers/${sessionId}`, payload)
  },

  async delete(sessionId) {
    return API.delete(`/api/browsers/${sessionId}`)
  },

  async restart(sessionId) {
    return API.post(`/api/browsers/${sessionId}/restart`, {})
  },

  /**
   * Return (or create) the chat linked to a browser session. The returned chat
   * has the browser profile active so the agent can drive the same page.
   */
  async createChat(sessionId, chatId = null, createNew = false) {
    const payload = {}
    if (chatId) payload.chat_id = chatId
    if (createNew) payload.create_new = true
    return API.post(`/api/browsers/${sessionId}/chat`, payload)
  },

  async stop(sessionId) {
    return API.post(`/api/browsers/${sessionId}/stop`, {})
  },

  // ── Page actions ────────────────────────────────────────────────────────

  /**
   * Execute a page action.  See the backend `BrowserSessionActionRequest`.
   */
  async action(sessionId, payload) {
    return API.post(`/api/browsers/${sessionId}/action`, payload)
  },

  navigate(sessionId, url) {
    return this.action(sessionId, { action: 'navigate', url })
  },

  back(sessionId) {
    return this.action(sessionId, { action: 'back' })
  },

  forward(sessionId) {
    return this.action(sessionId, { action: 'forward' })
  },

  refresh(sessionId) {
    return this.action(sessionId, { action: 'refresh' })
  },

  click(sessionId, selector) {
    return this.action(sessionId, { action: 'click', selector })
  },

  fill(sessionId, selector, value) {
    return this.action(sessionId, { action: 'fill', selector, value })
  },

  execute(sessionId, script) {
    return this.action(sessionId, { action: 'execute', script })
  },

  text(sessionId) {
    return this.action(sessionId, { action: 'text' })
  },

  links(sessionId) {
    return this.action(sessionId, { action: 'links' })
  },

  async screenshot(sessionId, fullPage = true) {
    return API.post(`/api/browsers/${sessionId}/screenshot`, { full_page: fullPage })
  },

  async source(sessionId) {
    return API.get(`/api/browsers/${sessionId}/source`)
  },

  // ── Co-browsing audit + cost ────────────────────────────────────────────

  async activity(sessionId, limit = 100) {
    return API.get(`/api/browsers/${sessionId}/activity?limit=${encodeURIComponent(limit)}`)
  },

  async cost(sessionId) {
    return API.get(`/api/browsers/${sessionId}/cost`)
  }
})
