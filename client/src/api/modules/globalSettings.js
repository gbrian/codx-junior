/**
 * Global Settings API module
 * Handles sectioned read/write of GlobalSettings with version history and rollback
 */

export const globalSettingsModule = (API) => ({
  /**
   * Read full GlobalSettings object assembled from all section files
   */
  async read() {
    const data = await API.get('/api/global/settings')
    API.globalSettings = data
    return data
  },

  /**
   * Write full GlobalSettings object (overwrites all sections)
   */
  async write(settings) {
    await API.put('/api/global/settings', settings)
    return API.globalSettings.read()
  },

  /**
   * Read a specific section by name
   * @param {string} sectionName - Section name (e.g., 'ai_models', 'ai_providers', 'git')
   * @returns {Promise<any>} Section data
   */
  section(sectionName) {
    return API.get(`/api/global/settings/section/${sectionName}`)
  },

  /**
   * Write a specific section without affecting others
   * @param {string} sectionName - Section name
   * @param {any} data - Section data (dict, list, or model)
   * @returns {Promise<any>} Updated section data
   */
  async saveSection(sectionName, data) {
    await API.put(`/api/global/settings/section/${sectionName}`, data)
    return API.globalSettings.section(sectionName)
  },

  /**
   * List version history for a section
   * @param {string} sectionName - Section name
   * @returns {Promise<Array>} List of SectionVersion objects
   */
  history(sectionName) {
    return API.get(`/api/global/settings/history/${sectionName}`)
  },

  /**
   * Get content of a specific version snapshot
   * @param {string} sectionName - Section name
   * @param {string} timestamp - Version timestamp (from history)
   * @returns {Promise<any>} Version data
   */
  getVersion(sectionName, timestamp) {
    return API.get(`/api/global/settings/history/${sectionName}/${timestamp}`)
  },

  /**
   * Rollback section to a specific historical version
   * @param {string} sectionName - Section name
   * @param {string} timestamp - Version timestamp
   * @returns {Promise<object>} Rollback status
   */
  rollback(sectionName, timestamp) {
    return API.post(`/api/global/settings/history/${sectionName}/${timestamp}/rollback`)
  },

  /**
   * Plugin management (legacy endpoints)
   */
  plugins: {
    async list() {
      return await API.get('/api/global/settings/section/plugins')
    },
    async add(plugin) {
      return await API.post('/api/plugins', plugin)
    },
    async remove(pluginName) {
      return await API.delete(`/api/plugins/${pluginName}`)
    },
    async loadFromFile(fileName) {
      return await API.get(`/api/plugins/load_from_file?file_path=${encodeURIComponent(fileName)}`)
    }
  }
})