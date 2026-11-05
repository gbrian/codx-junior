/**
 * DSH (DeepSeek Harness) task bridge API.
 *
 * The DSH plugin owns the conversation; codx-junior only mirrors task identity,
 * hierarchy and board placement. These calls configure that bridge and trigger
 * work in DSH.
 */
export const dshModule = (API) => ({
  /** Connection config + live bridge health + mirrored task count. */
  status() {
    return API.get('/api/dsh/status')
  },

  /** Persist the dashboard-managed Global Settings `dsh` section. */
  saveSettings(settings) {
    return API.put('/api/dsh/settings', settings)
  },

  /** Generate or rotate the token the DSH plugin presents. */
  generateToken() {
    return API.post('/api/dsh/token', {})
  },

  /** Pull every DSH task from one connected instance into the mirror board. */
  sync(instanceId) {
    const qs = instanceId ? `?instance_id=${encodeURIComponent(instanceId)}` : ''
    return API.post(`/api/dsh/sync${qs}`, {})
  },

  /** Create a DSH Session (and optionally prompt it) on one instance. */
  createTask(payload) {
    return API.post('/api/dsh/tasks', payload)
  },

  /** Read the live message surface of one DSH task (not persisted). */
  messages(sessionId, instanceId) {
    const qs = instanceId ? `?instance_id=${encodeURIComponent(instanceId)}` : ''
    return API.get(`/api/dsh/tasks/${encodeURIComponent(sessionId)}/messages${qs}`)
  },

  /** Send a follow-up prompt to a DSH Session. */
  prompt(sessionId, text, instanceId) {
    return API.post(`/api/dsh/tasks/${encodeURIComponent(sessionId)}/prompt`, {
      text,
      instance_id: instanceId,
    })
  },

  /** Cancel the active DSH turn. */
  cancel(sessionId, instanceId) {
    const qs = instanceId ? `?instance_id=${encodeURIComponent(instanceId)}` : ''
    return API.post(`/api/dsh/tasks/${encodeURIComponent(sessionId)}/cancel${qs}`, {})
  },
})
