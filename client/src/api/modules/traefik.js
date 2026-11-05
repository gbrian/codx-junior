/**
 * Traefik maintenance API module.
 *
 * Backend router:
 *   codx/junior/api/traefik.py
 *
 * Rules are stored in two places:
 *   - global rules  -> GlobalSettings.traefik_rules
 *   - project rules -> CODXJuniorSettings.traefik_rules (.codx/project.json)
 *
 * The same UI component uses `global.*` or `projects.*` depending on its scope.
 *
 * @typedef {import('../model/traefik.js').TraefikRule} TraefikRule
 * @typedef {import('../model/traefik.js').TraefikRoute} TraefikRoute
 * @typedef {import('../model/traefik.js').TraefikTargets} TraefikTargets
 */

function query({ projectId, refresh } = {}) {
  const params = new URLSearchParams()
  if (projectId) params.set('project_id', projectId)
  if (refresh) params.set('refresh', 'true')
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export const traefikModule = (API) => ({
  // ── Read model ───────────────────────────────────────────────────────────

  /**
   * Merged workspace + custom route list.
   * Without projectId it returns the global view (all project rules read-only).
   * With projectId it returns that project's view (its rules editable, global
   * rules inherited read-only, workspace routes filtered by project).
   *
   * @param {{projectId?: string, refresh?: boolean}} [options]
   * @returns {Promise<{routes: TraefikRoute[], stats: object, issues: string[], defaults: object}>}
   */
  routes(options = {}) {
    return API.get(`/api/traefik/routes${query(options)}`)
  },

  /**
   * Targets available to the rule editor: workspace apps, running containers
   * and defaults (domain, auth middleware, entrypoints).
   *
   * @returns {Promise<TraefikTargets>}
   */
  targets() {
    return API.get('/api/traefik/targets')
  },

  /**
   * Generated Traefik dynamic configuration plus route rows and issues.
   *
   * @param {{projectId?: string, refresh?: boolean}} [options]
   */
  preview(options = {}) {
    return API.get(`/api/traefik/preview${query(options)}`)
  },

  // ── Storages ─────────────────────────────────────────────────────────────

  global: {
    /** @returns {Promise<{rules: TraefikRule[]}>} */
    rules() {
      return API.get('/api/traefik/global/rules')
    },

    /**
     * Replace the whole global rule list.
     * @param {TraefikRule[]} rules
     * @returns {Promise<{rules: TraefikRule[]}>}
     */
    saveRules(rules) {
      return API.put('/api/traefik/global/rules', { rules })
    },
  },

  projects: {
    /** @param {string} projectId @returns {Promise<{rules: TraefikRule[]}>} */
    rules(projectId) {
      return API.get(`/api/traefik/projects/${encodeURIComponent(projectId)}/rules`)
    },

    /**
     * Replace the whole rule list of one project (stored in its project.json).
     * @param {string} projectId
     * @param {TraefikRule[]} rules
     * @returns {Promise<{rules: TraefikRule[]}>}
     */
    saveRules(projectId, rules) {
      return API.put(
        `/api/traefik/projects/${encodeURIComponent(projectId)}/rules`,
        { rules }
      )
    },
  },
})
