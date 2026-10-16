/**
 * Browsers API module
 * Handles all browser-related API operations: list, CRUD, navigate, screenshot, etc.
 */

export const browsersModule = (API) => ({
  // ── List & Retrieval ───────────────────────────────────────────────────

  /**
   * List all browsers with optional filters
   */
  async list(filters) {
    let qs = ""
    if (filters) {
      const params = Object.entries(filters)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join("&")
      qs = `?${params}`
    }
    return API.get(`/api/browsers${qs}`)
  },

  /**
   * Get a specific browser by ID
   */
  async get(browserId) {
    return API.get(`/api/browsers/${browserId}`)
  },

  /**
   * Get browser status by ID
   */
  async getStatus(browserId) {
    return API.get(`/api/browsers/${browserId}/status`)
  },

  // ── CRUD Operations ────────────────────────────────────────────────────

  /**
   * Create a new browser instance
   * @param {Object} browserConfig - Browser configuration (profile, headless, etc.)
   */
  async create(browserConfig) {
    return API.post('/api/browsers', browserConfig)
  },

  /**
   * Update browser configuration
   */
  async update(browserId, browserConfig) {
    return API.put(`/api/browsers/${browserId}`, browserConfig)
  },

  /**
   * Delete a browser instance
   */
  async delete(browserId) {
    return API.delete(`/api/browsers/${browserId}`)
  },

  // ── Browser Navigation & Actions ───────────────────────────────────────

  /**
   * Navigate to a URL
   */
  async navigate(browserId, url) {
    return API.post(`/api/browsers/${browserId}/navigate`, { url })
  },

  /**
   * Get current page URL
   */
  async getCurrentUrl(browserId) {
    return API.get(`/api/browsers/${browserId}/current-url`)
  },

  /**
   * Get page title
   */
  async getPageTitle(browserId) {
    return API.get(`/api/browsers/${browserId}/page-title`)
  },

  /**
   * Go back (previous page)
   */
  async goBack(browserId) {
    return API.post(`/api/browsers/${browserId}/back`, {})
  },

  /**
   * Go forward (next page)
   */
  async goForward(browserId) {
    return API.post(`/api/browsers/${browserId}/forward`, {})
  },

  /**
   * Refresh the page
   */
  async refresh(browserId) {
    return API.post(`/api/browsers/${browserId}/refresh`, {})
  },

  // ── Screenshot & Snapshots ─────────────────────────────────────────────

  /**
   * Take a screenshot of the current page
   * @param {string} browserId - Browser ID
   * @param {Object} options - Screenshot options (format, fullPage, etc.)
   */
  async screenshot(browserId, options = {}) {
    return API.post(`/api/browsers/${browserId}/screenshot`, options)
  },

  /**
   * Get screenshot URL
   */
  async getScreenshotUrl(browserId) {
    return API.connection.prepareUrl(`/api/browsers/${browserId}/screenshot`)
  },

  // ── Page Interaction ────────────────────────────────────────────────────

  /**
   * Execute JavaScript in the page context
   */
  async execute(browserId, script) {
    return API.post(`/api/browsers/${browserId}/execute`, { script })
  },

  /**
   * Click an element
   */
  async click(browserId, selector) {
    return API.post(`/api/browsers/${browserId}/click`, { selector })
  },

  /**
   * Type text in an element
   */
  async type(browserId, selector, text) {
    return API.post(`/api/browsers/${browserId}/type`, { selector, text })
  },

  /**
   * Fill form field
   */
  async fill(browserId, selector, value) {
    return API.post(`/api/browsers/${browserId}/fill`, { selector, value })
  },

  /**
   * Get element text
   */
  async getElementText(browserId, selector) {
    return API.get(`/api/browsers/${browserId}/element-text?selector=${encodeURIComponent(selector)}`)
  },

  /**
   * Get element HTML
   */
  async getElementHtml(browserId, selector) {
    return API.get(`/api/browsers/${browserId}/element-html?selector=${encodeURIComponent(selector)}`)
  },

  /**
   * Check if element exists
   */
  async elementExists(browserId, selector) {
    return API.get(`/api/browsers/${browserId}/element-exists?selector=${encodeURIComponent(selector)}`)
  },

  /**
   * Wait for element to appear
   */
  async waitForElement(browserId, selector, timeout = 30000) {
    return API.post(`/api/browsers/${browserId}/wait-for-element`, { selector, timeout })
  },

  // ── Cookie & Storage Management ────────────────────────────────────────

  /**
   * Get all cookies
   */
  async getCookies(browserId) {
    return API.get(`/api/browsers/${browserId}/cookies`)
  },

  /**
   * Set a cookie
   */
  async setCookie(browserId, cookie) {
    return API.post(`/api/browsers/${browserId}/cookies`, cookie)
  },

  /**
   * Delete a cookie
   */
  async deleteCookie(browserId, name) {
    return API.delete(`/api/browsers/${browserId}/cookies?name=${encodeURIComponent(name)}`)
  },

  /**
   * Clear all cookies
   */
  async clearCookies(browserId) {
    return API.post(`/api/browsers/${browserId}/cookies/clear`, {})
  },

  /**
   * Get local storage
   */
  async getLocalStorage(browserId) {
    return API.get(`/api/browsers/${browserId}/storage/local`)
  },

  /**
   * Set local storage value
   */
  async setLocalStorage(browserId, key, value) {
    return API.post(`/api/browsers/${browserId}/storage/local`, { key, value })
  },

  /**
   * Delete local storage value
   */
  async deleteLocalStorage(browserId, key) {
    return API.delete(`/api/browsers/${browserId}/storage/local?key=${encodeURIComponent(key)}`)
  },

  /**
   * Clear local storage
   */
  async clearLocalStorage(browserId) {
    return API.post(`/api/browsers/${browserId}/storage/local/clear`, {})
  },

  // ── Page Analysis ──────────────────────────────────────────────────────

  /**
   * Get page HTML content
   */
  async getPageContent(browserId) {
    return API.get(`/api/browsers/${browserId}/page-content`)
  },

  /**
   * Get all links on the page
   */
  async getLinks(browserId) {
    return API.get(`/api/browsers/${browserId}/links`)
  },

  /**
   * Get all images on the page
   */
  async getImages(browserId) {
    return API.get(`/api/browsers/${browserId}/images`)
  },

  /**
   * Get page metadata
   */
  async getMetadata(browserId) {
    return API.get(`/api/browsers/${browserId}/metadata`)
  },

  /**
   * Search for text on page
   */
  async findText(browserId, text) {
    return API.get(`/api/browsers/${browserId}/find-text?text=${encodeURIComponent(text)}`)
  },

  // ── Message Handling (Chat Integration) ─────────────────────────────────

  /**
   * Send a message to the browser (for chat integration)
   */
  async message(chat) {
    return API.post('/api/browser', chat)
  }
})