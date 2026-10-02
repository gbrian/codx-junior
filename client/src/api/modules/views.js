/**
 * Views API module
 * Handles view operations: list, save, delete, rename
 */

export const viewsModule = (API) => ({
  list() {
    return API.get('/api/views')
  },

  save(view) {
    return API.post('/api/views', view)
  },

  delete(name) {
    return API.delete(`/api/views/${encodeURIComponent(name)}`)
  },

  rename(oldName, newName) {
    return API.put(`/api/views/${encodeURIComponent(oldName)}`, { name: newName })
  }
})