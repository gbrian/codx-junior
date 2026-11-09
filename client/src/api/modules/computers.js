/**
 * Computers API module.
 *
 * Computer sessions generalize browser sessions: a session is a shared machine
 * (Chromium page, Linux desktop, Windows/macOS VM or a remote host).  The
 * backend exposes the canonical routes under `/api/computers`; the legacy
 * `/api/browsers` routes remain available.
 */

export const computersModule = (API) => ({
  // ── List & Retrieval ───────────────────────────────────────────────────

  async list(filters) {
    let qs = ''
    if (filters) {
      const params = Object.entries(filters)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&')
      qs = `?${params}`
    }
    return API.get(`/api/computers${qs}`)
  },

  async get(sessionId) {
    return API.get(`/api/computers/${sessionId}`)
  },

  // ── Image library ──────────────────────────────────────────────────────

  /**
   * Browse the desktop image catalog.
   *
   * @param {Object} [filters] - provider, q, category, kind, refresh.
   */
  async images(filters = {}) {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value))
      }
    })
    const qs = params.toString()
    return API.get(`/api/computers/images${qs ? `?${qs}` : ''}`)
  },

  /** List selectable tags for a repository. */
  async imageTags(provider, repository, refresh = false) {
    const params = new URLSearchParams({ provider, repository })
    if (refresh) params.set('refresh', 'true')
    return API.get(`/api/computers/images/tags?${params.toString()}`)
  },

  /** Credentials for the embedded KasmVNC live view. */
  async viewerCredentials(sessionId) {
    return API.post(`/api/computers/${sessionId}/viewer-credentials`, {})
  },

  // ── Saved computers ────────────────────────────────────────────────────

  /** Commit a running Linux/Kasmweb desktop into the project library. */
  async saveComputer(sessionId, payload) {
    return API.post(`/api/computers/${sessionId}/save`, payload)
  },

  /** List the project's reusable computers. */
  async savedComputers() {
    return API.get('/api/computers/library')
  },

  /** Delete a saved computer and its local Docker image. */
  async deleteSavedComputer(itemId) {
    return API.delete(`/api/computers/library/${itemId}`)
  },

  /** Authenticated preview blob for a saved computer. */
  async savedComputerPreview(itemId) {
    return API.connection.getBlob(`/api/computers/library/${itemId}/preview`)
  },

  // ── CRUD & lifecycle ────────────────────────────────────────────────────

  async create(payload) {
    return API.post('/api/computers', payload)
  },

  async update(sessionId, payload) {
    return API.put(`/api/computers/${sessionId}`, payload)
  },

  async delete(sessionId) {
    return API.delete(`/api/computers/${sessionId}`)
  },

  async restart(sessionId) {
    return API.post(`/api/computers/${sessionId}/restart`, {})
  },

  async createChat(sessionId, chatId = null, createNew = false) {
    const payload = {}
    if (chatId) payload.chat_id = chatId
    if (createNew) payload.create_new = true
    return API.post(`/api/computers/${sessionId}/chat`, payload)
  },

  async stop(sessionId) {
    return API.post(`/api/computers/${sessionId}/stop`, {})
  },

  async control(sessionId, action, { chatId = null, reason = null } = {}) {
    const payload = { action }
    if (chatId) payload.chat_id = chatId
    if (reason) payload.reason = reason
    return API.post(`/api/computers/${sessionId}/control`, payload)
  },

  // ── Actions (browser page or desktop) ──────────────────────────────────

  async action(sessionId, payload) {
    return API.post(`/api/computers/${sessionId}/action`, payload)
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

  /** Desktop helpers. */
  desktop(sessionId, action, payload = {}) {
    return this.action(sessionId, { action, ...payload })
  },

  clickAt(sessionId, x, y, button = 'left', clicks = 1) {
    return this.action(sessionId, { action: 'click', x, y, button, clicks })
  },

  clickText(sessionId, text, options = {}) {
    return this.action(sessionId, { action: 'click_text', text, ...options })
  },

  typeText(sessionId, text) {
    return this.action(sessionId, { action: 'type', text })
  },

  key(sessionId, key) {
    return this.action(sessionId, { action: 'key', key })
  },

  runCommand(sessionId, command, timeout = 60) {
    return this.action(sessionId, { action: 'run_command', command, timeout })
  },

  async screenshot(sessionId, options = {}) {
    const payload = typeof options === 'boolean'
      ? { full_page: options }
      : { include_text: true, max_width: 1600, ...options }
    return API.post(`/api/computers/${sessionId}/screenshot`, payload)
  },

  /** One-time WebSocket path for the built-in noVNC viewer. */
  async vncTicket(sessionId) {
    return API.post(`/api/computers/${sessionId}/vnc-ticket`, {})
  },

  async source(sessionId) {
    return API.get(`/api/computers/${sessionId}/source`)
  },

  // ── Co-driving audit + cost ────────────────────────────────────────────

  async activity(sessionId, limit = 100, { since = null, actor = null } = {}) {
    const params = new URLSearchParams({ limit: String(limit) })
    if (since) params.set('since', since)
    if (actor) params.set('actor', actor)
    return API.get(`/api/computers/${sessionId}/activity?${params.toString()}`)
  },

  async cost(sessionId) {
    return API.get(`/api/computers/${sessionId}/cost`)
  }
})
